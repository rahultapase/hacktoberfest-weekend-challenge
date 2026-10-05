import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

import metrics  # noqa: E402

from app import llm, names  # noqa: E402
from app.textnorm import normalize  # noqa: E402


def card(**kw):
    base = {"type": "attendance", "student_name": None, "candidates": [], "status": None, "amount": None,
            "for_month": None, "on_date": None, "verdict": "ok", "reasons": []}
    base.update(kw)
    return base


GOLD = {"facts": [
    {"student": "Riya", "type": "attendance", "status": "absent", "on_date": "2026-10-03"},
    {"student": "Aman", "type": "payment", "amount": 1500, "for_month": "2026-10"},
]}


def test_all_correct_green():
    cards = [card(student_name="Riya", status="absent", on_date="2026-10-03"),
             card(type="payment", student_name="Aman", amount=1500, for_month="2026-10")]
    r = metrics.score_line(cards, GOLD)
    assert r["raw_exact"] and r["auto_complete"]
    assert r["raw_silent"] == 0 and r["ver_silent"] == 0 and r["ver_correct_saved"] == 2


def test_wrong_amount_caught_by_verifier():
    cards = [card(student_name="Riya", status="absent", on_date="2026-10-03"),
             card(type="payment", student_name="Aman", amount=2000, for_month="2026-10", verdict="confirm")]
    r = metrics.score_line(cards, GOLD)
    assert r["raw_silent"] == 1 and r["ver_silent"] == 0 and r["amber"] == 1


def test_wrong_but_green_is_silent_error():
    cards = [card(student_name="Riya", status="present", on_date="2026-10-03")]
    r = metrics.score_line(cards, GOLD)
    assert r["ver_silent"] == 1 and r["drops"] == 2


def test_guess_used_without_verifier():
    gold = {"facts": [{"student": "?", "student_any": ["Neha Sharma", "Neha Gupta"], "must_confirm": True,
                       "type": "attendance", "status": "absent", "on_date": "2026-10-02"}]}
    cards = [card(status="absent", on_date="2026-10-02", verdict="confirm",
                  candidates=[{"id": 9, "name": "Neha Gupta", "score": 100}])]
    r = metrics.score_line(cards, gold)
    assert r["raw_silent"] == 1      # a plain lookup would have saved "Neha Gupta"
    assert r["ver_silent"] == 0 and r["any_confirm"]


def test_drop_caught_by_v7():
    cards = [card(student_name="Riya", status="absent", on_date="2026-10-03"),
             {"type": "missing", "candidates": [{"id": 7, "name": "Aman", "score": 100}], "verdict": "confirm"}]
    r = metrics.score_line(cards, GOLD)
    assert r["drops"] == 1 and r["drops_caught"] == 1


def test_aggregate():
    rows = [metrics.score_line([], {"facts": []})]
    a = metrics.aggregate(rows, [{"facts": [], "expect_confirm": False}])
    assert a["lines"] == 1 and a["line_exact"] == 1.0


def _gold():
    return [json.loads(l) for l in (ROOT / "eval" / "gold.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def test_gold_file_integrity():
    gold = _gold()
    roster = {s["name"] for s in names.load_roster_csv(ROOT / "eval" / "demo_roster.csv")}
    assert len(gold) >= 40
    assert len({g["id"] for g in gold}) == len(gold)
    for g in gold:
        assert g["source"] == "synthetic"
        for f in g["facts"]:
            assert f["type"] in metrics.SCORED_TYPES
            assert f["student"] in roster or f["student"] == "?"
            for k in metrics.FIELDS[f["type"]]:
                assert k in f, (g["id"], k)


def test_no_leakage_between_few_shot_and_eval():
    gold_lines = {normalize(g["line"]) for g in _gold()}
    roster = names.load_roster_csv(ROOT / "eval" / "demo_roster.csv")
    for line, _ in llm.FEW_SHOT:
        assert normalize(line) not in gold_lines
        assert names.scan(normalize(line), roster) == [], f"few-shot uses a roster name: {line}"
