"""Verifier tests on fixed raw events (no model call)."""

from datetime import date
from pathlib import Path

from app import names
from app.parser import clean_events
from app.verifier import verify

ROSTER = names.load_roster_csv(Path(__file__).parent.parent / "eval" / "demo_roster.csv")
D = date(2026, 10, 5)
SMOKE = "riya nahi aayi, aman ne 1500 diye oct ke, baaki 500 next week"


def ev(**kw):
    base = {"type": None, "student_text": None, "status": None, "amount_text": None,
            "month_text": None, "date_text": None, "note_text": None}
    base.update(kw)
    return base


def codes(v):
    return {r["code"] for r in v["reasons"]}


def test_smoke_line_all_green():
    events = [
        ev(type="attendance", student_text="riya", status="absent"),
        ev(type="payment", student_text="aman", amount_text="1500", month_text="oct"),
        ev(type="promise", student_text="aman", amount_text="500", date_text="next week"),
    ]
    out = verify(SMOKE, D, events, ROSTER)
    assert [v["verdict"] for v in out] == ["ok", "ok", "ok"]
    assert out[0]["student_name"] == "Riya" and out[0]["on_date"] == "2026-10-05"
    assert out[1]["amount"] == 1500 and out[1]["for_month"] == "2026-10"
    assert out[2]["amount"] == 500 and out[2]["on_date"] == "2026-10-12"


def test_v1_hallucinated_amount():
    out = verify(SMOKE, D, [ev(type="payment", student_text="aman", amount_text="2000")], ROSTER)
    assert "V1" in codes(out[0])


def test_v2_unreadable_amount():
    line = "aman ne kuch diye"
    out = verify(line, D, [ev(type="payment", student_text="aman", amount_text="kuch")], ROSTER)
    assert "V2" in codes(out[0])


def test_v3_unusual_amount():
    line = "aman ne 15000 diye"
    out = verify(line, D, [ev(type="payment", student_text="aman", amount_text="15000")], ROSTER)
    assert "V3" in codes(out[0])  # Aman's fee is 1200, cap 7200


def test_v4_ambiguous_neha():
    line = "neha absent"
    out = verify(line, D, [ev(type="attendance", student_text="neha", status="absent")], ROSTER)
    assert out[0]["verdict"] == "confirm" and "V4" in codes(out[0])
    assert {c["name"] for c in out[0]["candidates"][:2]} == {"Neha Sharma", "Neha Gupta"}
    assert len(out) == 1  # no extra V7 card: the mention is covered by the candidates


def test_v4_unknown_student():
    line = "rahul ne 1000 diye"
    out = verify(line, D, [ev(type="payment", student_text="rahul", amount_text="1000")], ROSTER)
    assert "V4" in codes(out[0])


def test_v4_whole_line_copied_as_name():
    out = verify(SMOKE, D, [ev(type="attendance", student_text=SMOKE, status="absent")], ROSTER)
    assert "V4" in codes(out[0])


def test_v5_bad_month():
    line = "aman ne 1500 diye kisi mahine ke"
    out = verify(line, D, [ev(type="payment", student_text="aman", amount_text="1500",
                              month_text="kisi mahine")], ROSTER)
    assert "V5" in codes(out[0])


def test_two_month_payment_ok():
    line = "shreya ne 3000 diye sep oct dono ke"
    out = verify(line, D, [ev(type="payment", student_text="shreya", amount_text="3000",
                              month_text="sep oct")], ROSTER)
    assert out[0]["verdict"] == "ok"
    assert out[0]["for_month"] == "2026-09,2026-10"


def test_v6_missing_amount_and_status():
    line = "aman ne diye, riya"
    out = verify(line, D, [ev(type="payment", student_text="aman"),
                           ev(type="attendance", student_text="riya")], ROSTER)
    assert "V6" in codes(out[0]) and "V6" in codes(out[1])


def test_v7_dropped_student():
    line = "riya aur karan nahi aaye"
    out = verify(line, D, [ev(type="attendance", student_text="riya", status="absent")], ROSTER)
    assert len(out) == 2
    assert out[1]["type"] == "missing" and out[1]["student_name"] == "Karan"
    assert "V7" in codes(out[1])


def test_v8_duplicate_today():
    line = "aman ne 1500 diye oct ke"
    existing = [{"student_id": 7, "type": "payment", "amount": 1500, "for_month": "2026-10",
                 "entry_date": "2026-10-05"}]
    out = verify(line, D, [ev(type="payment", student_text="aman", amount_text="1500",
                              month_text="oct")], ROSTER, existing)
    assert "V8" in codes(out[0])


def test_kal_promise_is_future_payment_is_past():
    line = "kal riya ki mummy 1000 degi"
    out = verify(line, D, [ev(type="promise", student_text="riya", amount_text="1000", date_text="kal")], ROSTER)
    assert out[0]["on_date"] == "2026-10-06"
    line = "aman ne kal 1000 diye"
    out = verify(line, D, [ev(type="payment", student_text="aman", amount_text="1000", date_text="kal")], ROSTER)
    assert out[0]["on_date"] == "2026-10-04"


def test_reasons_are_bilingual():
    out = verify("neha absent", D, [ev(type="attendance", student_text="neha", status="absent")], ROSTER)
    r = out[0]["reasons"][0]
    assert r["en"] and r["hi"] and r["code"] == "V4"


def test_clean_events_normalizes_and_merges():
    raw = {"events": [
        {"type": "payment", "student_text": "rohit", "amount_text": "2k", "month_text": "", "date_text": ""},
        {"type": "payment", "student_text": "rohit", "amount_text": "2k", "month_text": None},
        {"type": "promise", "student_text": "", "amount_text": "500"},
        {"type": "bogus", "student_text": "x"},
    ]}
    out = clean_events(raw)
    assert len(out) == 2
    assert out[0]["month_text"] is None
    assert out[1]["student_text"] == "rohit"
