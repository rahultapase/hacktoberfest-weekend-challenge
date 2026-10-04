"""Verifier rules V1..V8 (spec section 5).

Takes raw model events (verbatim spans), resolves them with code, and gives each one a
verdict: 'ok' (green, safe to save) or 'confirm' (amber, needs a tap). Also adds
'missing' cards for students mentioned in the line that no event covers (V7).
"""

from datetime import date

from rapidfuzz import fuzz

from app import amounts, dates, names
from app.textnorm import normalize

SANE_CAP_UNKNOWN_FEE = 20000
SANE_MULTIPLE = 6
MAX_NAME_WORDS = 3
SPAN_FIELDS = ["student_text", "amount_text", "month_text", "date_text", "note_text"]
MONEY_TYPES = {"payment", "promise", "fee_set"}


def _r(code: str, en: str, hi: str) -> dict:
    return {"code": code, "en": en, "hi": hi}


def span_in_line(span: str, norm_line: str) -> bool:
    s = normalize(span)
    if not s:
        return True
    if s in norm_line:
        return True
    return fuzz.partial_ratio(s, norm_line) >= 90


def _cand(c):
    return [{"id": s["id"], "name": s["name"], "score": round(score)} for s, score in c]


def verify_event(ev: dict, norm_line: str, entry: date, roster: list[dict],
                 existing: list[dict] | None = None) -> dict:
    """Resolve and check one raw event."""
    reasons: list[dict] = []
    out = dict(ev)
    out.update({"student_id": None, "student_name": None, "candidates": [], "amount": None,
                "for_month": None, "on_date": None, "note": ev.get("note_text")})
    etype = ev.get("type")

    # V1: every span must be in what she wrote
    for f in SPAN_FIELDS:
        if f == "note_text":
            continue  # free-text summary, not checked for money/names
        v = ev.get(f)
        if v and not span_in_line(v, norm_line):
            reasons.append(_r("V1", f"This wasn't in what you wrote: \"{v}\"",
                              f"Yeh aapki line mein nahi tha: \"{v}\""))

    # V4: student resolves to exactly one roster entry
    st = ev.get("student_text")
    student = None
    if not st:
        reasons.append(_r("V4", "Which student is this for?", "Yeh kis bachche ka hai?"))
    elif names.name_word_count(st) > MAX_NAME_WORDS:
        reasons.append(_r("V4", f"Name looks wrong: \"{st}\"", f"Naam sahi nahi lag raha: \"{st}\""))
    else:
        m = names.match(st, roster)
        out["candidates"] = _cand(m.candidates)
        if m.student:
            student = m.student
            out["student_id"], out["student_name"] = student["id"], student["name"]
        elif m.reason == "ambiguous":
            opts = " or ".join(c["name"] for c in out["candidates"][:3])
            opts_hi = " ya ".join(c["name"] for c in out["candidates"][:3])
            reasons.append(_r("V4", f"Which student? {opts}", f"Kaun sa bachcha? {opts_hi}"))
        elif m.candidates:
            opts = ", ".join(c["name"] for c in out["candidates"][:3])
            reasons.append(_r("V4", f"Not sure who \"{st}\" is. Maybe: {opts}",
                              f"\"{st}\" kaun hai pakka nahi. Shayad: {opts}"))
        else:
            reasons.append(_r("V4", f"New student? \"{st}\" is not in your list",
                              f"Naya bachcha? \"{st}\" list mein nahi hai"))

    # V6: required fields
    if etype in MONEY_TYPES and not ev.get("amount_text"):
        reasons.append(_r("V6", "Amount missing", "Rakam nahi likhi"))
    if etype == "attendance" and not ev.get("status"):
        reasons.append(_r("V6", "Present, absent or late?", "Aaya, nahi aaya ya late?"))

    # V2 / V3: amount parses and is sane
    if etype in MONEY_TYPES and ev.get("amount_text"):
        amt = amounts.parse(ev["amount_text"])
        if amt is None:
            reasons.append(_r("V2", f"Couldn't read the amount \"{ev['amount_text']}\"",
                              f"Rakam samajh nahi aayi: \"{ev['amount_text']}\""))
        else:
            out["amount"] = amt
            cap = SANE_MULTIPLE * student["monthly_fee"] if student else SANE_CAP_UNKNOWN_FEE
            if amt > cap:
                reasons.append(_r("V3", f"Amount looks unusual: ₹{amt}", f"Rakam zyada lag rahi hai: ₹{amt}"))

    # V5: month / date resolve
    mt = ev.get("month_text")
    if mt:
        months = dates.resolve_months(mt, entry)
        if not months or (len(months) > 1 and etype != "payment"):
            reasons.append(_r("V5", f"Couldn't work out the month \"{mt}\"",
                              f"Mahina samajh nahi aaya: \"{mt}\""))
        else:
            out["for_month"] = ",".join(months)
    elif etype == "fee_set":
        out["for_month"] = f"{entry.year:04d}-{entry.month:02d}"

    dt = ev.get("date_text")
    kind = "future" if etype == "promise" else "past"
    if dt:
        resolved = dates.resolve_date(dt, entry, kind)
        if resolved:
            out["on_date"] = resolved
        elif not dates.is_vague(dt):
            # a promise "agle mahine" is a month, not a day: accept it as the 1st of that month
            m = dates.resolve_month(dt, entry) if etype == "promise" else None
            if m:
                out["on_date"] = f"{m}-01"
            else:
                reasons.append(_r("V5", f"Couldn't work out the date \"{dt}\"",
                                  f"Tarikh samajh nahi aayi: \"{dt}\""))
    elif etype == "attendance":
        out["on_date"] = entry.isoformat()

    # V8: duplicate of something already saved today
    if existing and out["student_id"] is not None:
        key = (out["student_id"], etype, out["amount"], out["for_month"])
        for e in existing:
            if (e.get("student_id"), e.get("type"), e.get("amount"), e.get("for_month")) == key \
                    and e.get("entry_date") == entry.isoformat() \
                    and (etype != "attendance" or e.get("on_date") == out["on_date"]):
                reasons.append(_r("V8", "Already saved today?", "Aaj pehle hi save ho chuka hai?"))
                break

    out["reasons"] = reasons
    out["verdict"] = "confirm" if reasons else "ok"
    return out


def coverage_cards(norm_line: str, verified: list[dict], roster: list[dict]) -> list[dict]:
    """V7: every student mentioned in the line must appear in at least one event."""
    by_id = {s["id"]: s for s in roster}
    cards = []
    for mention in names.scan(norm_line, roster):
        ids = set(mention.student_ids)
        covered = False
        for v in verified:
            if v.get("student_id") in ids or ids & {c["id"] for c in v.get("candidates", [])}:
                covered = True
            elif v.get("student_text") and mention.text in normalize(v["student_text"]):
                covered = True
        if covered:
            continue
        cand_names = [by_id[i]["name"] for i in mention.student_ids]
        label = " / ".join(cand_names)
        cards.append({
            "type": "missing", "student_text": mention.text, "status": None, "amount_text": None,
            "month_text": None, "date_text": None, "note_text": None,
            "student_id": mention.student_ids[0] if len(ids) == 1 else None,
            "student_name": cand_names[0] if len(ids) == 1 else None,
            "candidates": [{"id": i, "name": by_id[i]["name"], "score": 100} for i in mention.student_ids],
            "amount": None, "for_month": None, "on_date": None, "note": None,
            "verdict": "confirm",
            "reasons": [_r("V7", f"You mentioned {label}. Nothing saved for them.",
                           f"Aapne {label} likha, par unka kuch save nahi hua.")],
        })
    return cards


def verify(line: str, entry: date, events: list[dict], roster: list[dict],
           existing: list[dict] | None = None) -> list[dict]:
    norm_line = normalize(line)
    verified = [verify_event(e, norm_line, entry, roster, existing) for e in events]
    return verified + coverage_cards(norm_line, verified, roster)
