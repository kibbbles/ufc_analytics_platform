"""bench_endpoints.py — Measure cold-start response times for key analytics endpoints.

Usage (from repo root):
    python backend/scripts/bench_endpoints.py [--base-url URL] [--runs N]

Defaults to hitting the local dev server at http://localhost:8000.
Pass --base-url https://kabes-maybes-api-... to hit Cloud Run.

Prints per-endpoint median/min/max across N runs (default 5).
"""

import argparse
import statistics
import time
import urllib.request
import urllib.error

ENDPOINTS = [
    ("/api/v1/analytics/style-evolution",               "style-evolution (all)"),
    ("/api/v1/analytics/style-evolution?weight_class=Heavyweight", "style-evolution (Heavyweight)"),
    ("/api/v1/past-predictions",                        "past-predictions summary"),
    ("/api/v1/past-predictions/events",                 "past-predictions events"),
    ("/api/v1/past-predictions/stats",                  "past-predictions stats"),
]


def fetch_ms(url: str) -> float:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            raise
        # 404 etc are fine for timing purposes
    return (time.perf_counter() - start) * 1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    runs = args.runs

    print(f"\nBenchmark: {base}  ({runs} runs each)\n")
    print(f"{'Endpoint':<50}  {'median':>8}  {'min':>8}  {'max':>8}")
    print("-" * 80)

    for path, label in ENDPOINTS:
        url = base + path
        times = []
        for _ in range(runs):
            try:
                times.append(fetch_ms(url))
            except Exception as exc:
                print(f"  ERROR on {label}: {exc}")
                break
        if times:
            med = statistics.median(times)
            print(f"{label:<50}  {med:>7.0f}ms  {min(times):>7.0f}ms  {max(times):>7.0f}ms")

    print()


if __name__ == "__main__":
    main()
