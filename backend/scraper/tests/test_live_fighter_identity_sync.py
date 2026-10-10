"""
Tests that the weekly scraper keeps an existing fighter's name in step with
UFCStats.

UFCStats renamed Valesca Machado (nickname "Tina Black") to Tina Black. The
scraper found her row by URL and returned it untouched, so her new bout read
"Tina Black" while fighter_details did not, and validate_etl.py's "name
matches none of the fighter's own bouts" check failed the Post-Scrape ETL on
2026-09-27 and 2026-10-04. Feature engineering and retraining were skipped
both weeks. The URL is the identity, so a different name on a URL match is a
rename and the row should follow it.

The database is in-memory SQLite behind the scraper's own engine reference, so
the real lookup and write SQL runs unchanged.

Run from backend/:
    pytest scraper/tests/test_live_fighter_identity_sync.py -v
"""

import os
import sys

import pytest
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# live_scraper imports its sibling database_integration as a top-level module,
# as it resolves when run as a script from scraper/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper import live_scraper  # noqa: E402
from scraper.live_scraper import LiveUFCScraper  # noqa: E402

URL = "http://ufcstats.com/fighter-details/"
TINA_URL = URL + "a1a91dbf41a029c4"


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE fighter_details (
                id TEXT PRIMARY KEY, "FIRST" TEXT, "LAST" TEXT,
                "NICKNAME" TEXT, "URL" TEXT)
        """))
        conn.execute(text("""
            CREATE TABLE fighter_tott (
                id TEXT PRIMARY KEY, "FIGHTER" TEXT, "HEIGHT" TEXT, "WEIGHT" TEXT,
                "REACH" TEXT, "STANCE" TEXT, "DOB" TEXT, "URL" TEXT,
                fighter_id TEXT, career_wins INT, career_losses INT,
                career_draws INT)
        """))
        conn.execute(text("""
            INSERT INTO fighter_details VALUES
              ('a1a91dbf', 'Valesca', 'Machado', 'Tina Black', :tina),
              ('9b3d1c2e', 'Da Un',   'Jung',    NULL,         :jung),
              ('5e8a7f10', NULL,      'Aoriqileng', NULL,      :mono),
              ('f4c49976', 'Conor',   'McGregor', 'The Notorious', :conor)
        """), {"tina": TINA_URL, "jung": URL + "9b3d1c2e00000000",
               "mono": URL + "5e8a7f1000000000", "conor": URL + "f4c49976c75c5ab2"})
    monkeypatch.setattr(live_scraper, "engine", engine)
    return engine


@pytest.fixture
def scraper():
    s = LiveUFCScraper.__new__(LiveUFCScraper)   # no browser
    s.existing_ids = set()
    return s


def _row(db, fighter_id):
    with db.connect() as conn:
        return conn.execute(text("""
            SELECT "FIRST", "LAST", "NICKNAME" FROM fighter_details WHERE id = :id
        """), {"id": fighter_id}).one()


def _fighter_count(db):
    with db.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM fighter_details")).scalar()


def _fight_page_person(name, url, nickname_html):
    html = f"""
    <div class="b-fight-details__person">
      <h3 class="b-fight-details__person-name"><a href="{url}">{name}</a></h3>
      {nickname_html}
      <ul class="b-list__box-list">
        <li class="b-list__box-list-item"><i>Height:</i> 5' 4"</li>
      </ul>
    </div>"""
    return BeautifulSoup(html, "html.parser").div


class TestNameSync:
    def test_renamed_fighter_takes_the_name_ufcstats_now_lists(self, db, scraper):
        # The bout that failed the gate: store_new_fights resolves her by URL.
        fighter_id = scraper.get_or_create_fighter("Tina Black", TINA_URL)

        assert fighter_id == "a1a91dbf"
        assert _row(db, "a1a91dbf")[:2] == ("Tina", "Black")
        assert _fighter_count(db) == 4

    def test_same_name_split_differently_is_left_alone(self, db, scraper):
        # "Da Un Jung" splits to Da / Un Jung, but it is the same name.
        scraper.get_or_create_fighter("Da Un Jung", URL + "9b3d1c2e00000000")

        assert _row(db, "9b3d1c2e")[:2] == ("Da Un", "Jung")

    def test_mononym_is_left_alone(self, db, scraper):
        scraper.get_or_create_fighter("Aoriqileng", URL + "5e8a7f1000000000")

        assert _row(db, "5e8a7f10")[:2] == (None, "Aoriqileng")

    def test_missing_name_never_blanks_a_fighter(self, db, scraper):
        scraper.get_or_create_fighter("", TINA_URL)

        assert _row(db, "a1a91dbf")[:2] == ("Valesca", "Machado")

    def test_no_nickname_information_leaves_nickname_alone(self, db, scraper):
        scraper.get_or_create_fighter("Conor McGregor", URL + "f4c49976c75c5ab2")

        assert _row(db, "f4c49976") == ("Conor", "McGregor", "The Notorious")


class TestNicknameSync:
    def test_fight_page_with_empty_nickname_clears_the_stale_one(self, db, scraper):
        # Her fight page: name "Tina Black", an empty nickname line.
        tott = scraper._parse_fighter_tott(_fight_page_person(
            "Tina Black", TINA_URL,
            '<p class="b-fight-details__person-title">\n</p>'))
        scraper.store_fighter_tott("Tina Black", tott)

        assert _row(db, "a1a91dbf") == ("Tina", "Black", None)

    def test_fight_page_nickname_is_stored_without_quotes(self, db, scraper):
        tott = scraper._parse_fighter_tott(_fight_page_person(
            "Conor McGregor", URL + "f4c49976c75c5ab2",
            '<p class="b-fight-details__person-title">\n  "Mystic Mac"\n</p>'))
        scraper.store_fighter_tott("Conor McGregor", tott)

        assert _row(db, "f4c49976")[2] == "Mystic Mac"

    def test_fight_page_without_a_nickname_line_changes_nothing(self, db, scraper):
        # A layout change must read as "unknown", not as "no nickname".
        tott = scraper._parse_fighter_tott(_fight_page_person(
            "Conor McGregor", URL + "f4c49976c75c5ab2", ""))
        scraper.store_fighter_tott("Conor McGregor", tott)

        assert _row(db, "f4c49976")[2] == "The Notorious"

    def test_profile_page_nickname_is_read(self, scraper, monkeypatch):
        html = """
          <span class="b-content__title-highlight">Tina Black</span>
          <p class="b-content__Nickname">
          </p>"""
        monkeypatch.setattr(scraper, "_get_soup",
                            lambda url, delay=None: BeautifulSoup(html, "html.parser"))

        assert scraper.scrape_fighter_physical_stats(TINA_URL)["nickname"] == ""
