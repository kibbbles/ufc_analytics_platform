"""scraper/record_live_feeds.py - record UFC.com's and ESPN's live feeds through one event.

Phase 0 of the live-results work: before building a poller on these feeds,
record one real fight night end to end. A completed event cannot show which
status values the feeds use while a bout is in progress, how many seconds pass
between a fight ending and its result appearing, or how a correction or a late
cancellation looks. This records exactly that, and nothing on the site reads it.

Once a minute it fetches both sources and writes one live_feed_snapshots row
per source (migration 012): status, latency, a hash of the body, the body
itself only when it changed, and a parsed count of bout statuses. Failures are
rows too, so gaps in the record are visible rather than silent.

It stops once both sources show every bout final and have stayed that way for
the grace period (to catch late corrections), or at --max-hours.

Exit status is 1 when the recording is incomplete: a source never answered,
any row failed to save, or the time cap hit before the card finished.

Politeness: one request per source per minute, conditional requests when the
source sends an ETag or Last-Modified, and the plain User-Agent from
ufc_live_feed.

Run from backend/:
    python scraper/record_live_feeds.py --ufc-fmid 1352 --espn-date 20261205 \\
        --start 2026-12-05T14:30:00Z
    python scraper/record_live_feeds.py --ufc-fmid 1348 --espn-date 20261121 --once --dry-run
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scraper.ufc_live_feed import FEED_URL, USER_AGENT

logger = logging.getLogger(__name__)

ESPN_URL = 'https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={date}'
TIMEOUT_S = 20


# --- parsing ---------------------------------------------------------------

def summarize(source: str, doc: dict) -> dict:
    """Bout status counts, plus whether the source shows the whole card as final."""
    if source == 'ufc_feed':
        event = doc['LiveEventDetail']
        statuses = Counter(f.get('Status') or '' for f in event['FightCard'])
        return {
            'event_status': event.get('Status'),
            'live_fight_id': event.get('LiveFightId'),
            'live_round': event.get('LiveRoundNumber'),
            'bouts': dict(statuses),
            'results': sum(1 for f in event['FightCard'] if (f.get('Result') or {}).get('Method')),
            'complete': bool(event['FightCard']) and (
                event.get('Status') == 'Final' or set(statuses) == {'Final'}),
        }
    comps = [c for e in doc.get('events', []) for c in e.get('competitions', [])]
    states = Counter(c['status']['type']['state'] for c in comps)
    return {
        'bouts': dict(Counter(c['status']['type']['name'] for c in comps)),
        'winners': sum(1 for c in comps for x in c.get('competitors', []) if x.get('winner')),
        'complete': bool(comps) and set(states) == {'post'},
    }


# --- fetching --------------------------------------------------------------

@dataclass
class Fetch:
    source: str
    fetched_at: datetime
    http_status: int | None = None
    latency_ms: int | None = None
    body: bytes | None = None
    error: str | None = None


class HttpFetcher:
    """GET with the honest User-Agent and conditional headers per source."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.validators: dict[str, dict[str, str]] = {}

    def __call__(self, source: str, url: str) -> Fetch:
        headers = {'User-Agent': USER_AGENT, **self.validators.get(source, {})}
        started = time.monotonic()
        f = Fetch(source, datetime.now(timezone.utc))
        try:
            resp = self.session.get(url, headers=headers, timeout=TIMEOUT_S)
        except requests.RequestException as e:
            f.error = f'{type(e).__name__}: {e}'
            return f
        f.latency_ms = int((time.monotonic() - started) * 1000)
        f.http_status = resp.status_code
        if resp.status_code == 200:
            f.body = resp.content
            v = {}
            if resp.headers.get('ETag'):
                v['If-None-Match'] = resp.headers['ETag']
            if resp.headers.get('Last-Modified'):
                v['If-Modified-Since'] = resp.headers['Last-Modified']
            self.validators[source] = v
        elif resp.status_code != 304:
            f.error = f'HTTP {resp.status_code}'
        return f


# --- storage ---------------------------------------------------------------

def db_store(row: dict) -> None:
    from sqlalchemy import text
    from db.database import engine
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO live_feed_snapshots
                (recording, source, fetched_at, http_status, latency_ms, sha256,
                 changed, body_gz, summary, error)
            VALUES (:recording, :source, :fetched_at, :http_status, :latency_ms, :sha256,
                    :changed, :body_gz, CAST(:summary AS JSONB), :error)
        """), row)


def print_store(row: dict) -> None:
    pass   # --dry-run: the log line already shows everything


# --- the loop --------------------------------------------------------------

@dataclass
class Recorder:
    recording: str
    urls: dict[str, str]
    fetch: Callable[[str, str], Fetch]
    store: Callable[[dict], None]
    interval_s: int = 60
    grace: timedelta = timedelta(minutes=20)
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    sleep: Callable[[float], None] = time.sleep
    last_sha: dict[str, str] = field(default_factory=dict)
    last_summary: dict[str, dict] = field(default_factory=dict)
    ok_polls: Counter = field(default_factory=Counter)
    failed_polls: Counter = field(default_factory=Counter)
    changes: Counter = field(default_factory=Counter)
    store_failures: int = 0

    def poll(self) -> dict[str, dict | None]:
        """Fetch and record every source once. Returns each source's summary, or None."""
        summaries: dict[str, dict | None] = {}
        for source, url in self.urls.items():
            f = self.fetch(source, url)
            sha = summary = None
            changed = False
            error = f.error
            if f.body is not None:
                sha = hashlib.sha256(f.body).hexdigest()
                changed = sha != self.last_sha.get(source)
                self.last_sha[source] = sha
                try:
                    summary = summarize(source, json.loads(f.body))
                    self.last_summary[source] = summary
                except (ValueError, KeyError, TypeError) as e:
                    error = f'unparseable body: {type(e).__name__}: {e}'
            elif f.http_status == 304:
                # Not modified: the source still says what it said last time.
                sha = self.last_sha.get(source)
                summary = self.last_summary.get(source)
            if error:
                self.failed_polls[source] += 1
            else:
                self.ok_polls[source] += 1
            self.changes[source] += changed
            row = {
                'recording': self.recording, 'source': source, 'fetched_at': f.fetched_at,
                'http_status': f.http_status, 'latency_ms': f.latency_ms, 'sha256': sha,
                'changed': changed, 'body_gz': gzip.compress(f.body) if changed else None,
                'summary': json.dumps(summary) if summary and changed else None, 'error': error,
            }
            try:
                self.store(row)
            except Exception as e:   # keep recording; the exit status reports it
                self.store_failures += 1
                logger.error(f'{source}: could not save snapshot: {e}')
            state = f'error={error}' if error else (
                f"{'changed' if changed else 'same'} {json.dumps(summary, separators=(',', ':')) if summary else ''}")
            print(f'{f.fetched_at:%H:%M:%S} {source:16} {f.http_status or "---"} '
                  f'{f.latency_ms if f.latency_ms is not None else "-":>5}ms {state}', flush=True)
            summaries[source] = None if error else summary
        return summaries

    def run(self, start: datetime, deadline: datetime, once: bool = False) -> bool:
        wait = (start - self.now()).total_seconds()
        if wait > 0:
            print(f'Waiting {wait / 60:.0f} min until {start:%Y-%m-%d %H:%M}Z', flush=True)
            self.sleep(wait)
        complete_since: datetime | None = None
        finished = False
        while self.now() < deadline:
            tick = self.now()
            summaries = self.poll()
            if once:
                break
            if all(s is not None and s['complete'] for s in summaries.values()):
                complete_since = complete_since or tick
                if self.now() - complete_since >= self.grace:
                    finished = True
                    break
            elif any(s is not None and not s['complete'] for s in summaries.values()):
                complete_since = None   # a source reopened a bout: keep watching
            next_tick = tick + timedelta(seconds=self.interval_s)
            self.sleep(max(0.0, (next_tick - self.now()).total_seconds()))

        problems = []
        for source in self.urls:
            if self.ok_polls[source] == 0:
                problems.append(f'{source} never answered')
        if self.store_failures:
            problems.append(f'{self.store_failures} snapshot(s) could not be saved')
        if not finished and not once:
            problems.append(f'stopped at the time cap ({deadline:%H:%M}Z) before every bout was final')
        print('\nRecording summary', flush=True)
        for source in self.urls:
            print(f'  {source:16} {self.ok_polls[source]} ok, {self.failed_polls[source]} failed, '
                  f'{self.changes[source]} changed bodies')
        for p in problems:
            print(f'::error::{p}', flush=True)
        if once:
            print('  single poll (--once): completeness not checked')
        elif not problems:
            print('  complete: every bout final in both sources through the grace period')
        return not problems


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ufc-fmid', type=int, required=True, help="UFC.com feed id (upcoming_events.ufc_event_fmid)")
    ap.add_argument('--espn-date', required=True, help='ESPN scoreboard date, YYYYMMDD')
    ap.add_argument('--recording', help='label for this recording (default ufc-<fmid>)')
    ap.add_argument('--start', type=_utc, help='UTC time to start polling (default now)')
    ap.add_argument('--interval', type=int, default=60, help='seconds between polls (default 60)')
    ap.add_argument('--max-hours', type=float, default=10, help='hard stop after start (default 10)')
    ap.add_argument('--grace-minutes', type=int, default=20,
                    help='keep polling this long after the card is final, for corrections (default 20)')
    ap.add_argument('--once', action='store_true', help='poll each source once and stop')
    ap.add_argument('--dry-run', action='store_true', help='print only; do not write snapshots')
    args = ap.parse_args()

    start = args.start or datetime.now(timezone.utc)
    rec = Recorder(
        recording=args.recording or f'ufc-{args.ufc_fmid}',
        urls={'ufc_feed': FEED_URL.format(fmid=args.ufc_fmid),
              'espn_scoreboard': ESPN_URL.format(date=args.espn_date)},
        fetch=HttpFetcher(),
        store=print_store if args.dry_run else db_store,
        interval_s=args.interval,
        grace=timedelta(minutes=args.grace_minutes),
    )
    print(f'Recording {rec.recording}: start {start:%Y-%m-%d %H:%M}Z, every {args.interval}s, '
          f'cap {args.max_hours}h{" [DRY RUN]" if args.dry_run else ""}', flush=True)
    ok = rec.run(start, start + timedelta(hours=args.max_hours), once=args.once)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
