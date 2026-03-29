"""
30.3 — Chat endpoint test suite.

Run from the backend directory with the dev server running:
    python test_chat.py

Ground truths sourced from docs/sanity-check.md and backend/tests/test_data_quality.py.
Sign-off criteria: 8/10 questions answered correctly.
"""

import json
import requests

BASE = "http://localhost:8000/api/v1/chat"

QUESTIONS = [
    # (label, question, hint of what correct answer contains)
    ("Khabib record",
     "What is Khabib Nurmagomedov's UFC record?",
     "expected: 13 wins, 0 losses"),

    ("Conor record",
     "What is Conor McGregor's UFC record?",
     "expected: 10 wins, 4 losses"),

    ("Jon Jones record",
     "What is Jon Jones's UFC record?",
     "expected: 22 wins, 1 loss (DQ), 1 NC"),

    ("Petr Yan record",
     "What is Petr Yan's UFC record?",
     "expected: 12 wins, 4 losses"),

    ("GSP record",
     "What is Georges St-Pierre's UFC record?",
     "expected: 20 wins, 2 losses"),

    ("McGregor vs Khabib",
     "Who won the fight between Conor McGregor and Khabib Nurmagomedov and how?",
     "expected: Khabib wins by submission in round 4"),

    ("Nunes vs Rousey",
     "Who won the fight between Amanda Nunes and Ronda Rousey and how?",
     "expected: Nunes wins by KO/TKO in round 1"),

    ("Most sig strikes Khabib",
     "What is the most significant strikes Khabib Nurmagomedov landed in a single fight? Which fight was it?",
     "expected: a specific number and opponent name"),

    ("Most KO wins lightweight",
     "Who has the most KO/TKO wins in the Lightweight division?",
     "expected: a fighter name with a count"),

    ("Best takedown accuracy",
     "Which fighter has the best takedown accuracy among fighters with at least 10 fights?",
     "expected: a fighter name with a percentage"),
]


def ask(question: str) -> dict:
    try:
        r = requests.post(BASE, json={"question": question, "history": []}, timeout=30)
        return r.json()
    except Exception as e:
        return {"answer": f"REQUEST FAILED: {e}", "sql": None, "status": "error"}


def main():
    print("=" * 70)
    print("UFC Chat — Test Suite (30.3)")
    print("=" * 70)

    results = []
    for i, (label, question, hint) in enumerate(QUESTIONS, 1):
        print(f"\n[{i:02d}] {label}")
        print(f"     Q: {question}")
        print(f"     Hint: {hint}")

        resp = ask(question)
        status = resp.get("status", "?")
        answer = resp.get("answer", "")
        sql = resp.get("sql", "")

        print(f"     Status: {status}")
        print(f"     A: {answer}")
        if sql:
            # Show just first line of SQL for brevity
            print(f"     SQL: {sql.splitlines()[0]}...")

        results.append((label, status, answer))
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    ok = sum(1 for _, s, _ in results if s == "ok")
    print(f"  Returned OK:     {ok}/{len(results)}")
    print(f"  Errors/no result: {len(results) - ok}/{len(results)}")
    print()
    print("Manually grade each answer above against the hints.")
    print("Target: 8/10 correct before moving to frontend (30.4).")


if __name__ == "__main__":
    main()
