from datetime import date

from app import ledger

STUDENT = {"id": 1, "name": "Aman", "monthly_fee": 1200, "start_month": "2026-08", "end_month": None}
CUR = "2026-10"


def pay(i, amount, for_month=None, d="2026-10-01", line=None):
    return {"id": i, "type": "payment", "amount": amount, "for_month": for_month,
            "entry_date": d, "raw_line": line or f"line{i}"}


def months(res):
    return {r["month"]: r["balance"] for r in res["months"]}


def test_no_payments_all_due():
    res = ledger.allocate(STUDENT, [], CUR)
    assert months(res) == {"2026-08": 1200, "2026-09": 1200, "2026-10": 1200}
    assert res["outstanding"] == 3600


def test_full_payment_explicit_month():
    res = ledger.allocate(STUDENT, [pay(1, 1200, "2026-10")], CUR)
    assert months(res)["2026-10"] == 0
    assert months(res)["2026-08"] == 1200


def test_unassigned_goes_to_oldest_unpaid():
    res = ledger.allocate(STUDENT, [pay(1, 1200)], CUR)
    assert months(res) == {"2026-08": 0, "2026-09": 1200, "2026-10": 1200}


def test_partial_then_rest_later():
    res = ledger.allocate(STUDENT, [pay(1, 700, "2026-10"), pay(2, 500, "2026-10", d="2026-10-12")], CUR)
    assert months(res)["2026-10"] == 0
    res = ledger.allocate(STUDENT, [pay(1, 700, "2026-10")], CUR)
    assert months(res)["2026-10"] == 500


def test_one_payment_two_months():
    res = ledger.allocate(STUDENT, [pay(1, 2400, "2026-09,2026-10")], CUR)
    assert months(res) == {"2026-08": 1200, "2026-09": 0, "2026-10": 0}


def test_overflow_goes_fifo_then_advance():
    res = ledger.allocate(STUDENT, [pay(1, 5000, "2026-10")], CUR)
    assert res["outstanding"] == 0
    assert res["advance"] == 5000 - 3600


def test_explicit_future_month_is_advance():
    s = dict(STUDENT, start_month="2026-10")
    res = ledger.allocate(s, [pay(1, 1200, "2026-10"), pay(2, 1200, "2026-11")], CUR)
    assert res["outstanding"] == 0 and res["advance"] == 1200


def test_fee_change_midway():
    entries = [{"id": 1, "type": "fee_set", "amount": 1500, "for_month": "2026-10",
                "entry_date": "2026-09-28", "raw_line": "x"}]
    res = ledger.allocate(STUDENT, entries, CUR)
    assert [r["due"] for r in res["months"]] == [1200, 1200, 1500]


def test_student_starting_mid_year_and_left():
    s = dict(STUDENT, start_month="2026-09")
    assert ledger.due_months(s, CUR) == ["2026-09", "2026-10"]
    left = dict(STUDENT, start_month="2026-04", end_month="2026-08")
    assert ledger.due_months(left, CUR)[-1] == "2026-08"
    assert not ledger.is_active(left, "2026-10")


def test_month_range_crosses_year():
    assert ledger.month_range("2026-11", "2027-02") == ["2026-11", "2026-12", "2027-01", "2027-02"]


def test_promises_open_kept_overdue():
    today = date(2026, 10, 15)
    es = [
        pay(1, 700, "2026-10", d="2026-10-03", line="a"),
        {"id": 2, "type": "promise", "amount": 500, "on_date": "2026-10-10", "entry_date": "2026-10-03", "raw_line": "a"},
    ]
    assert ledger.promises(es, today)[0]["status"] == "overdue"
    assert ledger.promises(es, date(2026, 10, 8))[0]["status"] == "open"
    es.append(pay(3, 500, "2026-10", d="2026-10-09", line="b"))
    assert ledger.promises(es, today)[0]["status"] == "kept"


def test_attendance_counts():
    es = [{"id": i, "type": "attendance", "status": s, "on_date": d, "entry_date": d}
          for i, (s, d) in enumerate([("absent", "2026-10-01"), ("absent", "2026-10-02"),
                                      ("late", "2026-10-03"), ("absent", "2026-09-30")])]
    assert ledger.attendance(es, "2026-10") == {"present": 0, "absent": 2, "late": 1}


def test_dues_for_month_sorted_and_filters_inactive():
    students = [
        STUDENT,
        {"id": 2, "name": "Riya", "monthly_fee": 800, "start_month": "2026-04", "end_month": None},
        {"id": 3, "name": "Tanvi", "monthly_fee": 800, "start_month": "2026-04", "end_month": "2026-08"},
    ]
    by = {1: [pay(1, 3600)], 2: []}
    rows = ledger.dues_for_month(students, by, "2026-10", date(2026, 10, 5))
    assert [r["name"] for r in rows] == ["Riya", "Aman"]
    assert rows[0]["balance"] == 800 and rows[1]["balance"] == 0
    assert rows[0]["outstanding"] == 800 * 7
