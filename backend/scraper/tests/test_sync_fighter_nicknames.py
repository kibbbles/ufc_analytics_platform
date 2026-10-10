"""
Unit tests for sync_fighter_nicknames.py: reading the UFCStats A-Z listing and
deciding which nicknames to write.

Run from backend/:
    pytest scraper/tests/test_sync_fighter_nicknames.py -v
"""

import os
import sys

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.sync_fighter_nicknames import parse_listing, plan_changes  # noqa: E402

URL = "http://ufcstats.com/fighter-details/"


def _listing_row(first, last, nickname, slug):
    cell = f'<td class="b-statistics__table-col"><a href="{URL}{slug}">{{}}</a></td>'
    return "<tr>" + "".join(cell.format(v) for v in (first, last, nickname)) + "</tr>"


LISTING_HTML = f"""
<table class="b-statistics__table"><tbody>
  <tr class="b-statistics__table-row"><td class="b-statistics__table-col_type_clear"></td></tr>
  {_listing_row("Melissa", "Amaya", "Mamba", "amaya")}
  {_listing_row("Patricio", "Pitbull", "", "pitbull")}
  {_listing_row("Magomed", "Bibulatov", "", "bibulatov")}
</tbody></table>"""


@pytest.fixture
def listing():
    return parse_listing(BeautifulSoup(LISTING_HTML, "html.parser"))


def test_listing_reads_name_and_nickname_and_skips_the_spacer_row(listing):
    assert listing == {
        URL + "amaya":     {"name": "Melissa Amaya",     "nickname": "Mamba"},
        URL + "pitbull":   {"name": "Patricio Pitbull",  "nickname": ""},
        URL + "bibulatov": {"name": "Magomed Bibulatov", "nickname": ""},
    }


def test_changed_layout_is_an_error_not_an_empty_listing():
    with pytest.raises(ValueError):
        parse_listing(BeautifulSoup("<div>Checking your browser</div>", "html.parser"))


def test_nicknames_follow_ufcstats_and_names_are_only_reported(listing):
    rows = [
        ("a1", "Melissa",   "Amaya",     None,      URL + "amaya"),
        ("b2", "Patricio",  "Pitbull",   "Pitbull", URL + "pitbull"),
        ("c3", "Bibulatov", "Magomed",   None,      URL + "bibulatov"),
        ("d4", "Not",       "Listed",    "Ghost",   URL + "unlisted"),
    ]

    changes, renamed = plan_changes(listing, rows)

    assert changes == [
        {"id": "a1", "url": URL + "amaya",   "old": None,      "new": "Mamba"},
        {"id": "b2", "url": URL + "pitbull", "old": "Pitbull", "new": None},
    ]
    assert renamed == [
        {"id": "c3", "stored": "Bibulatov Magomed", "ufcstats": "Magomed Bibulatov"},
    ]
