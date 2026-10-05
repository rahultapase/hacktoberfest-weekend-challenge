"""Seed a running server with SYNTHETIC history for screenshots/demo.

Pays every student up to September, a few for October, plus one open promise.
Usage: python tools/seed_demo.py [base_url]
"""

import sys

import httpx

B = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OCT_PAID = {"Shreya": 1500, "Kavya": 1500, "Sneha": 1500, "Rohit": 1200, "Priyanka": 1200,
            "Ishaan": 800, "Priya": 400, "Mohit": 1000, "Karan": 800}

students = httpx.get(B + "/api/students").json()
for s in students:
    if not s["active"]:
        continue
    y, m = map(int, s["start_month"].split("-"))
    prev = (2026 - y) * 12 + (10 - m)  # months before October 2026
    ev = []
    if prev > 0:
        ev.append({"type": "payment", "student_id": s["id"], "amount": s["monthly_fee"] * prev})
    if s["name"] in OCT_PAID:
        ev.append({"type": "payment", "student_id": s["id"], "amount": OCT_PAID[s["name"]], "for_month": "2026-10"})
    if s["name"] == "Mohit":
        ev.append({"type": "promise", "student_id": s["id"], "amount": 500, "on_date": "2026-10-10"})
    if ev:
        httpx.post(B + "/api/entries", json={"raw_line": "synthetic history (seed)", "entry_date": "2026-10-02",
                                             "model": "seed", "events": ev}).raise_for_status()
print("seeded", len(students), "students")
