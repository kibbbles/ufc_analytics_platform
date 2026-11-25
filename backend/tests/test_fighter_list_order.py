"""Order of the Fighter Lookup list (GET /fighters), against the live database.

Fighters with no weight class and a 0-0 record have no fights on file. They
used to sort into the alphabet with everyone else, so 8 of the 20 fighters on
page 1 showed "---" and 0-0. They now come after every fighter with a record.
Within each group the order is last name, then first name, then id.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.v1.endpoints.fighters import list_fighters
from db.database import SessionLocal

PAGE_SIZE = 100


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def _page(db, page, search=None, page_size=PAGE_SIZE):
    return list_fighters(page=page, page_size=page_size, search=search, weight_class=None, db=db)


def _empty(f):
    return f.weight_class is None and f.wins + f.losses == 0


def _all(db, search=None):
    first = _page(db, 1, search)
    rows = list(first.data)
    for p in range(2, first.meta.total_pages + 1):
        rows += _page(db, p, search).data
    assert len(rows) == first.meta.total
    return rows


@pytest.fixture(scope="module")
def everyone(db):
    return _all(db)


def test_first_page_has_no_empty_fighters(db):
    page = _page(db, 1, page_size=20).data
    assert page, "the list is empty"
    assert not [f for f in page if _empty(f)]


def test_empty_fighters_all_come_last(everyone):
    flags = [_empty(f) for f in everyone]
    assert any(flags) and not all(flags), "both groups should exist in the live data"
    boundary = flags.index(True)
    assert all(flags[boundary:]), "a fighter with a record sorts after an empty one"


def test_each_group_stays_in_name_order(everyone, db):
    # Same sort the database uses (en_US collation), checked as adjacent pairs.
    from sqlalchemy import text

    for group in (False, True):
        names = [(f.last_name or "", f.first_name or "", f.id) for f in everyone if _empty(f) is group]
        pairs = list(zip(names, names[1:]))
        out_of_order = db.execute(
            text("""
                SELECT COUNT(*) FROM unnest(
                    CAST(:al AS text[]), CAST(:af AS text[]), CAST(:ai AS text[]),
                    CAST(:bl AS text[]), CAST(:bf AS text[]), CAST(:bi AS text[])
                ) AS t(al, af, ai, bl, bf, bi)
                WHERE (al, af, ai) > (bl, bf, bi)
            """),
            {
                "al": [a[0] for a, _ in pairs], "af": [a[1] for a, _ in pairs], "ai": [a[2] for a, _ in pairs],
                "bl": [b[0] for _, b in pairs], "bf": [b[1] for _, b in pairs], "bi": [b[2] for _, b in pairs],
            },
        ).scalar()
        assert out_of_order == 0


def test_paging_never_repeats_or_skips_a_fighter(everyone, db):
    ids = [f.id for f in everyone]
    assert len(ids) == len(set(ids))


def test_search_results_put_empty_fighters_last(db):
    rows = _all(db, search="silva")
    flags = [_empty(f) for f in rows]
    if True in flags:
        assert all(flags[flags.index(True):])


def test_draw_only_fighters_keep_their_place(everyone):
    """0-0 with a weight class means draws or no contests, not an empty profile."""
    draw_only = [i for i, f in enumerate(everyone) if f.wins + f.losses == 0 and f.weight_class]
    first_empty = next(i for i, f in enumerate(everyone) if _empty(f))
    assert draw_only and all(i < first_empty for i in draw_only)
