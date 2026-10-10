"""
Unit tests for how upcoming_scraper.py resolves a card's fighters to
fighter_details rows.

The database is a small in-memory fighter table behind a fake engine, so the
real matching code - URL lookup, then rapidfuzz name fallback - runs unchanged.

Run from the project root:
    cd backend
    pytest scraper/tests/test_upcoming_fighter_resolution.py -v
"""

import pytest

from scraper import upcoming_scraper
from scraper.upcoming_scraper import UpcomingScraper

URL = "http://ufcstats.com/fighter-details/"

# Two different people who share a name, as UFCStats has them.
FIGHTERS = [
    ("6f813990", "Anthony", "Romero", URL + "6f81399074fcdbba"),
    ("c0ac37a4", "Marcus", "McGhee", URL + "c0ac37a4e2a1e0f1"),
]


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows


class _Conn:
    def __init__(self, fighters):
        self._fighters = fighters

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, clause, params=None):
        if params and "url" in params:
            return _Result([(f[0],) for f in self._fighters if f[3] == params["url"]])
        return _Result([(f[0], f[1], f[2]) for f in self._fighters])


class _Engine:
    def __init__(self, fighters):
        self._fighters = fighters

    def connect(self):
        return _Conn(self._fighters)


@pytest.fixture()
def scraper(monkeypatch):
    monkeypatch.setattr(upcoming_scraper, "engine", _Engine(FIGHTERS))
    return UpcomingScraper.__new__(UpcomingScraper)


def test_known_url_resolves_to_its_fighter(scraper):
    assert scraper.resolve_fighter(URL + "c0ac37a4e2a1e0f1", "Marcus McGhee") == "c0ac37a4"


def test_unknown_url_is_unmatched_even_when_the_name_exists(scraper):
    # UFC 332: the card's Anthony Romero was a debutant not yet in the database.
    # Matching him by name attached his prediction to the other Anthony Romero.
    assert scraper.resolve_fighter(URL + "4419acb81e6f0ea4", "Anthony Romero") is None


def test_name_decides_only_when_the_card_has_no_url(scraper):
    assert scraper.resolve_fighter(None, "Anthony Romero") == "6f813990"
    assert scraper.resolve_fighter("", "Marcus McGhee") == "c0ac37a4"
