"""Scoring for the eval (spec section 12). Pure functions, unit-tested in tests/test_eval_metrics.py.

A "fact" is a dict: student (canonical roster name), type, and type-specific fields:
  attendance: status, on_date | payment: amount, for_month | promise: amount, on_date | fee_set: amount, for_month
Notes are not scored.

Gold facts may carry:
  student "?" + student_any [...]  -> the right student can't be known from the line
  must_confirm: true               -> saving it green is a silent error even if the fields match
"""

SCORED_TYPES = ("attendance", "payment", "promise", "fee_set")
FIELDS = {
    "attendance": ("status", "on_date"),
    "payment": ("amount", "for_month"),
    "promise": ("amount", "on_date"),
    "fee_set": ("amount", "for_month"),
}


def fact_matches(pred: dict, gold: dict) -> bool:
    if pred.get("type") != gold.get("type"):
        return False
    for f in FIELDS[gold["type"]]:
        if pred.get(f) != gold.get(f):
            return False
    if gold.get("student") == "?":
        return pred.get("student") in (gold.get("student_any") or [])
    return pred.get("student") == gold.get("student")


def match(preds: list[dict], golds: list[dict]) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Greedy one-to-one matching. Returns (pairs[(pred_i, gold_i)], unmatched_pred_idx, unmatched_gold_idx)."""
    used_g, pairs = set(), []
    for i, p in enumerate(preds):
        for j, g in enumerate(golds):
            if j not in used_g and fact_matches(p, g):
                pairs.append((i, j))
                used_g.add(j)
                break
    mp = {i for i, _ in pairs}
    return pairs, [i for i in range(len(preds)) if i not in mp], [j for j in range(len(golds)) if j not in used_g]


def card_to_fact(card: dict, guess: bool) -> dict | None:
    """Turn a verifier card into a fact. guess=True means 'no verifier': take code's best name
    candidate even when it isn't confident (what a plain model + lookup would save)."""
    if card.get("type") not in SCORED_TYPES:
        return None
    student = card.get("student_name")
    if student is None and guess and card.get("candidates"):
        student = card["candidates"][0]["name"]
    f = {"student": student, "type": card["type"]}
    for k in FIELDS[card["type"]]:
        f[k] = card.get(k)
    return f


def score_line(cards: list[dict], gold: dict) -> dict:
    """Score one line both ways: without the verifier (everything saved) and with it (only green saved)."""
    golds = [g for g in gold["facts"] if g["type"] in SCORED_TYPES]
    scored_cards = [c for c in cards if c.get("type") in SCORED_TYPES]
    missing_cards = [c for c in cards if c.get("type") == "missing"]

    # --- without verifier: every extracted fact is saved
    raw = [card_to_fact(c, guess=True) for c in scored_cards]
    pairs, un_p, un_g = match(raw, golds)
    mc_hits = [i for i, j in pairs if golds[j].get("must_confirm")]
    raw_silent = len(un_p) + len(mc_hits)
    raw_correct = len(pairs) - len(mc_hits)

    # --- with verifier: only green cards are saved, amber go to the tray
    green_idx = [i for i, c in enumerate(scored_cards) if c["verdict"] == "ok"]
    green = [card_to_fact(scored_cards[i], guess=False) for i in green_idx]
    gpairs, g_un_p, _ = match(green, golds)
    g_mc = [i for i, j in gpairs if golds[j].get("must_confirm")]
    ver_silent = len(g_un_p) + len(g_mc)
    ver_correct_saved = len(gpairs) - len(g_mc)
    amber = len(scored_cards) - len(green_idx)

    # drops: gold facts the model never produced at all; did V7 flag that student?
    flagged_names = {c2["name"] for m in missing_cards for c2 in m.get("candidates", [])}
    drops = [golds[j] for j in un_g]
    drops_caught = [d for d in drops if d.get("student") in flagged_names
                    or set(d.get("student_any") or []) & flagged_names]

    golds_clean = [g for g in golds if not g.get("must_confirm")]
    return {
        "n_gold": len(golds),
        "n_gold_clean": len(golds_clean),
        "n_pred": len(raw),
        "raw_matched": len(pairs),
        "raw_correct": raw_correct,
        "raw_silent": raw_silent,
        "raw_exact": not un_p and not un_g and not mc_hits,
        "green": len(green),
        "amber": amber,
        "missing_cards": len(missing_cards),
        "ver_silent": ver_silent,
        "ver_correct_saved": ver_correct_saved,
        "auto_complete": ver_silent == 0 and amber == 0 and not missing_cards and ver_correct_saved == len(golds_clean)
                         and not any(g.get("must_confirm") for g in golds),
        "drops": len(drops),
        "drops_caught": len(drops_caught),
        "any_confirm": amber > 0 or bool(missing_cards),
        "silent_raw_facts": [raw[i] for i in un_p] + [raw[i] for i in mc_hits],
        "silent_ver_facts": [green[i] for i in g_un_p] + [green[i] for i in g_mc],
        "dropped_facts": drops,
    }


def aggregate(rows: list[dict], golds: list[dict]) -> dict:
    s = lambda k: sum(r[k] for r in rows)
    n_pred, n_gold = s("n_pred"), s("n_gold")
    exp = [r for r, g in zip(rows, golds) if g.get("expect_confirm")]
    clean = [r for r, g in zip(rows, golds) if not g.get("expect_confirm")]
    total_cards = s("green") + s("amber")
    return {
        "lines": len(rows),
        "gold_facts": n_gold,
        "pred_facts": n_pred,
        "precision": s("raw_matched") / n_pred if n_pred else 0.0,
        "recall": s("raw_matched") / n_gold if n_gold else 0.0,
        "line_exact": sum(r["raw_exact"] for r in rows) / len(rows) if rows else 0.0,
        "silent_no_verifier": s("raw_silent"),
        "silent_with_verifier": s("ver_silent"),
        "correct_saved_green": s("ver_correct_saved"),
        "gold_clean_facts": s("n_gold_clean"),
        "amber": s("amber"),
        "missing_cards": s("missing_cards"),
        "confirm_rate": s("amber") / total_cards if total_cards else 0.0,
        "expect_confirm_lines": len(exp),
        "expect_confirm_caught": sum(r["any_confirm"] for r in exp),
        "clean_lines_with_confirm": sum(r["any_confirm"] for r in clean),
        "clean_lines": len(clean),
        "auto_complete_lines": sum(r["auto_complete"] for r in rows),
        "drops": s("drops"),
        "drops_caught_v7": s("drops_caught"),
    }
