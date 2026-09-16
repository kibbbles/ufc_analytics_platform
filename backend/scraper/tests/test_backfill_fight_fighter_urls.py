"""
Unit tests for backfill_fight_fighter_urls.py - event page parsing and the
guard that decides whether a page's fighter URLs can be attached to BOUT.

Run from the project root:
    cd backend
    pytest scraper/tests/test_backfill_fight_fighter_urls.py -v
"""

from bs4 import BeautifulSoup

from scraper.backfill_fight_fighter_urls import (
    EVENT_ROW_CLASS,
    orient_to_bout,
    parse_event_fighters,
)

URL_A = 'http://ufcstats.com/fighter-details/aaaaaaaaaaaaaaaa'
URL_B = 'http://ufcstats.com/fighter-details/bbbbbbbbbbbbbbbb'


def meta(name_a, url_a, name_b, url_b):
    return {'fighter_a_name': name_a, 'fighter_a_url': url_a,
            'fighter_b_name': name_b, 'fighter_b_url': url_b}


def event_row(fight_url, *fighters):
    links = ''.join(
        f'<p><a class="b-link b-link_style_black" href="{url}">\n  {name}\n</a></p>'
        for name, url in fighters
    )
    return (
        f'<tr class="{EVENT_ROW_CLASS}" data-link="{fight_url}">'
        f'<td class="b-fight-details__table-col"><a class="b-flag b-flag_style_green">win</a></td>'
        f'<td class="b-fight-details__table-col">{links}</td>'
        f'</tr>'
    )


class TestParseEventFighters:
    def test_maps_fight_url_to_both_fighters_in_page_order(self):
        html = '<table>' + event_row(
            'http://ufcstats.com/fight-details/f1 ', ('Jean Silva', URL_A), ('Jose Delgado', URL_B)
        ) + '</table>'
        fights = parse_event_fighters(BeautifulSoup(html, 'html.parser'))
        assert fights == {
            'http://ufcstats.com/fight-details/f1': meta('Jean Silva', URL_A, 'Jose Delgado', URL_B)
        }

    def test_row_without_two_fighter_links_is_omitted(self):
        html = '<table>' + event_row('http://ufcstats.com/fight-details/f1', ('Jean Silva', URL_A)) + '</table>'
        assert parse_event_fighters(BeautifulSoup(html, 'html.parser')) == {}


class TestOrientToBout:
    def test_page_in_bout_order_is_returned_unchanged(self):
        m = meta('Jean Silva', URL_A, 'Jose Delgado', URL_B)
        assert orient_to_bout('Jean Silva vs. Jose Delgado', m) == m

    def test_winner_first_page_is_swapped_so_each_url_stays_with_its_fighter(self):
        page = meta('Salahdine Parnasse', URL_A, 'Dan Hooker', URL_B)
        oriented = orient_to_bout('Dan Hooker vs. Salahdine Parnasse', page)
        assert oriented == meta('Dan Hooker', URL_B, 'Salahdine Parnasse', URL_A)

    def test_names_that_match_neither_order_are_refused(self):
        page = meta('Jean Silva', URL_A, 'Jose Delgado', URL_B)
        assert orient_to_bout('Jean Silva vs. Someone Else', page) is None

    def test_namesakes_in_one_bout_are_not_swapped(self):
        # When both fighters share a name, only the page order identifies them.
        page = meta('Jean Silva', URL_A, 'Jean Silva', URL_B)
        assert orient_to_bout('Jean Silva vs. Jean Silva', page) == page
        assert orient_to_bout('Jean Silva vs. Jean Silva', meta('Jean Silva', URL_A, 'Jean Silva', None)) is None

    def test_missing_url_is_refused(self):
        assert orient_to_bout('Jean Silva vs. Jose Delgado', meta('Jean Silva', URL_A, 'Jose Delgado', None)) is None
        assert orient_to_bout('Jean Silva vs. Jose Delgado', None) is None
