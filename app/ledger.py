"""Ledger maths (spec section 7). Pure functions: no DB, no model.

Entries are dicts with at least: id, type, entry_date, amount, for_month, on_date, status, raw_line.
for_month may hold two months comma-joined ("2026-09,2026-10") for one payment covering both.
"""

from datetime import date


def ym(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def month_range(start: str, end: str) -> list[str]:
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _order(e: dict):
    return (e.get("entry_date") or "", e.get("id") or 0)


def fee_for_month(student: dict, entries: list[dict], month: str) -> int:
    """Latest fee_set effective on or before `month`, else the roster fee."""
    fee = student["monthly_fee"]
    best = None
    for e in entries:
        if e["type"] != "fee_set" or not e.get("amount"):
            continue
        eff = (e.get("for_month") or e["entry_date"][:7]).split(",")[0]
        if eff <= month and (best is None or (eff, _order(e)) > best[0]):
            best = ((eff, _order(e)), e["amount"])
    return best[1] if best else fee


def due_months(student: dict, current_month: str) -> list[str]:
    end = student.get("end_month") or current_month
    end = min(end, current_month)
    if student["start_month"] > end:
        return []
    return month_range(student["start_month"], end)


def allocate(student: dict, entries: list[dict], current_month: str) -> dict:
    """Allocate payments to months. Explicit month first, otherwise oldest unpaid (FIFO).
    Overflow goes to the oldest unpaid month; anything left is advance."""
    months = due_months(student, current_month)
    due = {m: fee_for_month(student, entries, m) for m in months}
    paid = {m: 0 for m in months}
    advance = 0

    def fill(m: str, amount: int) -> int:
        take = min(amount, due[m] - paid[m])
        paid[m] += take
        return amount - take

    payments = sorted((e for e in entries if e["type"] == "payment" and e.get("amount")), key=_order)
    for p in payments:
        left = p["amount"]
        targets = [m for m in (p.get("for_month") or "").split(",") if m]
        for m in targets:
            if m in due and left > 0:
                left = fill(m, left)
        for m in months:  # FIFO overflow / unassigned
            if left <= 0:
                break
            left = fill(m, left)
        advance += left

    rows = [{"month": m, "due": due[m], "paid": paid[m], "balance": due[m] - paid[m]} for m in months]
    return {
        "months": rows,
        "outstanding": sum(r["balance"] for r in rows if r["balance"] > 0),
        "advance": advance,
        "total_paid": sum(p["amount"] for p in payments),
    }


def promises(entries: list[dict], today: date) -> list[dict]:
    """Promise status: 'kept' once later payments cover it, 'overdue' if its date passed, else 'open'.
    Promises never change balances."""
    out = []
    pays = [e for e in entries if e["type"] == "payment" and e.get("amount")]
    for pr in sorted((e for e in entries if e["type"] == "promise"), key=_order):
        later = sum(p["amount"] for p in pays
                    if _order(p) > _order(pr) and p.get("raw_line") != pr.get("raw_line"))
        if pr.get("amount") and later >= pr["amount"]:
            status = "kept"
        elif pr.get("on_date") and pr["on_date"] < today.isoformat():
            status = "overdue"
        else:
            status = "open"
        out.append({"id": pr.get("id"), "amount": pr.get("amount"), "on_date": pr.get("on_date"),
                    "entry_date": pr["entry_date"], "status": status})
    return out


def attendance(entries: list[dict], month: str) -> dict:
    counts = {"present": 0, "absent": 0, "late": 0}
    for e in entries:
        if e["type"] == "attendance" and e.get("status") in counts:
            d = e.get("on_date") or e["entry_date"]
            if d.startswith(month):
                counts[e["status"]] += 1
    return counts


def is_active(student: dict, month: str) -> bool:
    return student["start_month"] <= month and (not student.get("end_month") or month <= student["end_month"])


def dues_for_month(students: list[dict], entries_by_student: dict, month: str, today: date) -> list[dict]:
    """One row per student active in `month`: due, paid, balance for that month, total outstanding,
    latest open/overdue promise. Sorted by balance (highest first)."""
    current = max(month, ym(today))
    rows = []
    for s in students:
        if not is_active(s, month):
            continue
        es = entries_by_student.get(s["id"], [])
        alloc = allocate(s, es, current)
        mrow = next((r for r in alloc["months"] if r["month"] == month),
                    {"month": month, "due": 0, "paid": 0, "balance": 0})
        open_pr = [p for p in promises(es, today) if p["status"] != "kept"]
        rows.append({
            "student_id": s["id"], "name": s["name"], "batch": s.get("batch"),
            "due": mrow["due"], "paid": mrow["paid"], "balance": mrow["balance"],
            "outstanding": alloc["outstanding"], "advance": alloc["advance"],
            "promise": open_pr[-1] if open_pr else None,
        })
    rows.sort(key=lambda r: (-r["balance"], r["name"]))
    return rows
