"""Ask box (spec section 9). The model only picks an intent and copies spans;
code runs the query and fills a fixed template, so the model never states a number."""

from datetime import date

from app import dates, db, ledger, llm, names
from app.fmt import inr, month_name

INTENTS = ["who_owes", "student_balance", "absences", "paid_list", "unknown"]

ASK_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": INTENTS},
        "student_text": {"type": ["string", "null"]},
        "month_text": {"type": ["string", "null"]},
    },
    "required": ["intent"],
}

ASK_SYSTEM = """You map a tuition teacher's question (Hindi, English or Hinglish) to one intent.
Intents:
- who_owes: which students still owe fees (for a month)
- student_balance: how much one student owes
- absences: how many days one student was absent (in a month)
- paid_list: who has paid fees (for a month)
- unknown: anything else
Copy student_text and month_text EXACTLY as written, or null. Never answer the question yourself."""

FEW_SHOT = [
    ("kiski fees abhi tak nahi aayi aug ki?", {"intent": "who_owes", "student_text": None, "month_text": "aug"}),
    ("meera ka kitna dena baaki hai", {"intent": "student_balance", "student_text": "meera", "month_text": None}),
    ("how many days was tushar absent last month", {"intent": "absences", "student_text": "tushar", "month_text": "last month"}),
    ("pichle mahine kis kis ne fees bhari", {"intent": "paid_list", "student_text": None, "month_text": "pichle mahine"}),
    ("kal kitne baje class hai", {"intent": "unknown", "student_text": None, "month_text": None}),
]

HELP_EN = ("I can answer 4 kinds of questions: who still owes fees, how much one student owes, "
           "how many days a student was absent, and who has paid.")
HELP_HI = ("Yeh 4 tarah ke sawaal samajhta hai: kiski fees baaki hai, ek bachche ka kitna baaki hai, "
           "bachcha kitne din nahi aaya, aur kisne fees de di.")


def classify(question: str, model: str | None = None) -> dict:
    import json
    msgs = [{"role": "system", "content": ASK_SYSTEM}]
    for q, a in FEW_SHOT:
        msgs.append({"role": "user", "content": q})
        msgs.append({"role": "assistant", "content": json.dumps(a)})
    msgs.append({"role": "user", "content": question})
    out, _ = llm.chat_json(msgs, ASK_SCHEMA, model, num_predict=80)
    intent = out.get("intent") if out.get("intent") in INTENTS else "unknown"
    clean = lambda v: (v.strip() or None) if isinstance(v, str) else None
    return {"intent": intent, "student_text": clean(out.get("student_text")),
            "month_text": clean(out.get("month_text"))}


def _names_list(items: list[str]) -> str:
    return ", ".join(items)


def answer(conn, question: str, today: date, model: str | None = None,
           parsed: dict | None = None, student_id: int | None = None) -> dict:
    """parsed: optional pre-classified intent (used by tests). student_id: her pick after a
    'which student?' prompt."""
    p = parsed or classify(question, model)
    intent = p["intent"]
    res = {"intent": intent, "params": p, "en": "", "hi": "", "candidates": []}
    students = db.list_students(conn)
    by_student = db.entries_by_student(conn)

    month = ledger.ym(today)
    if p.get("month_text"):
        m = dates.resolve_month(p["month_text"], today)
        if not m:
            res["en"] = f"I couldn't work out the month \"{p['month_text']}\". Try a month name like \"October\"."
            res["hi"] = f"Mahina samajh nahi aaya: \"{p['month_text']}\". Mahine ka naam likhiye, jaise \"October\"."
            return res
        month = m
    res["params"] = dict(p, month=month)
    mon_en, mon_hi = month_name(month, "en", True), month_name(month, "en")

    student = None
    if intent in ("student_balance", "absences"):
        if student_id is not None:
            student = next((s for s in students if s["id"] == student_id), None)
        else:
            m = names.match(p.get("student_text"), students)
            student = m.student
            if not student:
                res["candidates"] = [{"id": s["id"], "name": s["name"]} for s, _ in m.candidates]
                res["en"] = f"Which student do you mean by \"{p.get('student_text') or ''}\"?"
                res["hi"] = f"\"{p.get('student_text') or ''}\" se kaun sa bachcha?"
                return res

    if intent == "who_owes":
        rows = [r for r in ledger.dues_for_month(students, by_student, month, today) if r["balance"] > 0]
        if not rows:
            res["en"], res["hi"] = f"Everyone has paid for {mon_en}.", f"{mon_hi} ki sabki fees aa gayi hai."
        else:
            total = sum(r["balance"] for r in rows)
            lst = _names_list([f"{r['name']} ₹{inr(r['balance'])}" for r in rows])
            res["en"] = f"{mon_en}: {len(rows)} students still owe ₹{inr(total)}. {lst}."
            res["hi"] = f"{mon_hi} mein {len(rows)} bachchon ki fees baaki hai, kul ₹{inr(total)}. {lst}."
    elif intent == "student_balance":
        alloc = ledger.allocate(student, by_student.get(student["id"], []), max(month, ledger.ym(today)))
        owed = [r for r in alloc["months"] if r["balance"] > 0]
        if not owed:
            res["en"], res["hi"] = f"{student['name']} has nothing due.", f"{student['name']} ka kuch baaki nahi hai."
            if alloc["advance"]:
                res["en"] += f" Advance: ₹{inr(alloc['advance'])}."
                res["hi"] += f" Advance: ₹{inr(alloc['advance'])}."
        else:
            detail = _names_list([f"{month_name(r['month'])} ₹{inr(r['balance'])}" for r in owed])
            res["en"] = f"{student['name']} owes ₹{inr(alloc['outstanding'])} in total ({detail})."
            res["hi"] = f"{student['name']} ka kul ₹{inr(alloc['outstanding'])} baaki hai ({detail})."
    elif intent == "absences":
        c = ledger.attendance(by_student.get(student["id"], []), month)
        res["en"] = f"{student['name']} was absent {c['absent']} days in {mon_en} (late {c['late']})."
        res["hi"] = f"{student['name']} {mon_hi} mein {c['absent']} din absent rahe (late {c['late']})."
    elif intent == "paid_list":
        rows = ledger.dues_for_month(students, by_student, month, today)
        full = [r["name"] for r in rows if r["due"] > 0 and r["balance"] == 0]
        part = [f"{r['name']} (₹{inr(r['paid'])} / ₹{inr(r['due'])})" for r in rows if 0 < r["paid"] < r["due"]]
        if not full and not part:
            res["en"], res["hi"] = f"Nobody has paid for {mon_en} yet.", f"{mon_hi} ki fees abhi kisi ne nahi di."
        else:
            res["en"] = f"{mon_en}: paid in full: {_names_list(full) or 'none'}. Paid part: {_names_list(part) or 'none'}."
            res["hi"] = f"{mon_hi}: poori fees: {_names_list(full) or 'koi nahi'}. Thodi fees: {_names_list(part) or 'koi nahi'}."
    else:
        res["en"], res["hi"] = HELP_EN, HELP_HI
    return res
