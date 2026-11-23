"""scraper/ufc_live_feed.py - Read UFC.com's per-event live feed.

UFC.com's event pages poll one JSON document per event. It lists every bout
with its card section, the section's scheduled start, a status, and the result
once the bout is over. It is plain JSON on CloudFront, so unlike UFCStats it
needs no headless browser, and one request covers the whole card.

The feed is undocumented. Every caller must treat a failure here as "unknown"
and fall back to something safe, never as "nothing happened".

Finding an event's feed id takes two hops: the /events listing gives each
event page's slug, and each event page carries the feed id ("event_fmid").
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

import requests

# A plain, honest User-Agent. ESPN's CDN rejects any User-Agent containing a
# URL, so this one deliberately carries none, to stay usable for both sources.
USER_AGENT = "KabesMaybes/0.1"

FEED_URL = "https://d29dxerjsp82wz.cloudfront.net/api/v3/event/live/{fmid}.json"
EVENTS_URL = "https://www.ufc.com/events"
EVENT_PAGE_URL = "https://www.ufc.com/event/{slug}"

REQUEST_GAP_S = 1.5   # pause between requests to ufc.com in one run
TIMEOUT_S = 20


class FeedError(RuntimeError):
    """The feed or a UFC.com page could not be read or did not look as expected."""


@dataclass(frozen=True)
class FeedBout:
    fight_id: int              # UFC.com's id for the bout
    order: int                 # 1 = main event
    segment: str               # "Main", "Prelims1", "Prelims2", ...
    segment_start: datetime | None  # scheduled start of the bout's card section (UTC), if announced
    status: str                # "Final" for finished bouts; other values seen live
    fighter_names: tuple[str, str]
    fighter_last_names: tuple[str, str]


def _get(session: requests.Session, url: str) -> requests.Response:
    try:
        resp = session.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
    except requests.RequestException as e:
        raise FeedError(f"{url}: {e}") from e
    if resp.status_code != 200:
        raise FeedError(f"{url}: HTTP {resp.status_code}")
    return resp


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_event(fmid: int, session: requests.Session | None = None) -> dict:
    """Return the LiveEventDetail document for one event."""
    session = session or requests.Session()
    resp = _get(session, FEED_URL.format(fmid=fmid))
    try:
        event = resp.json()["LiveEventDetail"]
        event["FightCard"]
    except (ValueError, KeyError, TypeError) as e:
        raise FeedError(f"feed {fmid}: unexpected document ({e})") from e
    return event


def bouts(event: dict) -> list[FeedBout]:
    """The event's bouts, in card order. Raises FeedError on a malformed bout."""
    out = []
    for f in event["FightCard"]:
        try:
            fighters = f["Fighters"]
            out.append(FeedBout(
                fight_id=int(f["FightId"]),
                order=int(f["FightOrder"]),
                segment=f["CardSegment"],
                segment_start=_parse_ts(f["CardSegmentStartTime"]) if f.get("CardSegmentStartTime") else None,
                status=f.get("Status") or "",
                fighter_names=tuple(
                    f"{x['Name'].get('FirstName') or ''} {x['Name'].get('LastName') or ''}".strip()
                    for x in fighters),
                fighter_last_names=tuple(x["Name"].get("LastName") or "" for x in fighters),
            ))
        except (KeyError, TypeError, ValueError) as e:
            raise FeedError(f"bout {f.get('FightId')}: unexpected shape ({e})") from e
    return sorted(out, key=lambda b: b.order)


def name_tokens(name: str) -> frozenset[str]:
    """Accent-folded, lower-case word set. "Jiří Procházka" -> {"jiri", "prochazka"}."""
    ascii_name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    return frozenset(re.sub(r"[^a-z ]", " ", ascii_name.lower()).split())


def _same_fighter(our_name: str, feed_last_name: str) -> bool:
    # The feed's last name must appear whole in our name. Matching on any shared
    # word would pair "Da Silva" with every other Silva on the card.
    last = name_tokens(feed_last_name)
    return bool(last) and last <= name_tokens(our_name)


def match_bout(name_a: str, name_b: str, feed_bouts: list[FeedBout]) -> FeedBout | None:
    """The single feed bout between these two fighters, or None if zero or several match."""
    hits = [
        b for b in feed_bouts
        if len(b.fighter_last_names) == 2 and (
            (_same_fighter(name_a, b.fighter_last_names[0]) and _same_fighter(name_b, b.fighter_last_names[1]))
            or (_same_fighter(name_a, b.fighter_last_names[1]) and _same_fighter(name_b, b.fighter_last_names[0])))
    ]
    return hits[0] if len(hits) == 1 else None


def _event_key(name: str) -> frozenset[str]:
    return name_tokens(name) - {"vs", "ufc", "fight", "night"}


def list_event_slugs(session: requests.Session) -> list[str]:
    html = _get(session, EVENTS_URL).text
    slugs = sorted(set(re.findall(r'href="/event/([a-z0-9-]+)"', html)))
    if not slugs:
        raise FeedError("ufc.com/events listed no event pages")
    return slugs


def event_fmid_from_page(slug: str, session: requests.Session) -> int | None:
    m = re.search(r'"event_fmid"\s*:\s*"(\d+)"', _get(session, EVENT_PAGE_URL.format(slug=slug)).text)
    return int(m.group(1)) if m else None


_NUMBERED_SLUG = re.compile(r"^ufc-(\d+)$")
_DATED_SLUG = re.compile(r"-([a-z]+)-(\d{2})-(\d{4})$")
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


def _slug_date(slug: str) -> date | None:
    m = _DATED_SLUG.search(slug)
    if not m or m.group(1) not in _MONTHS:
        return None
    return date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))


def candidate_slugs(event_name: str, event_date: date, slugs: list[str]) -> list[str]:
    """Event pages worth opening for this event, so a lookup costs a few requests, not dozens.

    "UFC 335: ..." can only be /event/ufc-335. Anything else is a dated page
    within a day of the event, or one of the rare pages with neither a number
    nor a date in its slug.
    """
    numbered = re.match(r"UFC (\d+)\b", event_name)
    if numbered:
        return [s for s in slugs if s == f"ufc-{numbered.group(1)}"]
    out = []
    for s in slugs:
        if _NUMBERED_SLUG.match(s):
            continue
        d = _slug_date(s)
        if d is None or abs((d - event_date).days) <= 1:
            out.append(s)
    return out


def find_event_fmid(
    event_name: str,
    event_date: date,
    session: requests.Session,
    slugs: list[str],
    exclude: set[int] = frozenset(),
) -> int | None:
    """Find the feed id for one of our events among UFC.com's listed event pages.

    A feed matches when its start is within a day of our event date (UFC.com
    stores the start in UTC, our date is the local one) and its name has the
    same words as ours, headliners included. Returns None unless exactly one
    event page matches.
    """
    want = _event_key(event_name)
    found = set()
    for slug in candidate_slugs(event_name, event_date, slugs):
        time.sleep(REQUEST_GAP_S)
        fmid = event_fmid_from_page(slug, session)
        if fmid is None or fmid in exclude:
            continue
        time.sleep(REQUEST_GAP_S)
        feed = fetch_event(fmid, session)
        start = _parse_ts(feed["StartTime"]).date()
        if abs((start - event_date).days) <= 1 and _event_key(feed.get("Name") or "") == want:
            found.add(fmid)
    return found.pop() if len(found) == 1 else None
