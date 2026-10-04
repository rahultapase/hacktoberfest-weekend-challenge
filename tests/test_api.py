"""API flow tests: parse -> save -> dues, with the model call mocked (no Ollama needed)."""

import pytest
from fastapi.testclient import TestClient

from app import llm, main, parser, reminders

SMOKE = "riya nahi aayi, aman ne 1500 diye oct ke, baaki 500 next week"
SMOKE_EVENTS = [
    {"type": "attendance", "student_text": "riya", "status": "absent", "amount_text": None,
     "month_text": None, "date_text": None, "note_text": None},
    {"type": "payment", "student_text": "aman", "status": None, "amount_text": "1500",
     "month_text": "oct", "date_text": None, "note_text": None},
    {"type": "promise", "student_text": "aman", "status": None, "amount_text": "500",
     "month_text": None, "date_text": "next week", "note_text": None},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TR_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("TR_NO_WARMUP", "1")
    monkeypatch.setenv("TR_TODAY", "2026-10-05")
    monkeypatch.delenv("TR_PIN", raising=False)
    monkeypatch.setattr(parser, "parse_line", lambda line, *a, **k: {
        "events": SMOKE_EVENTS if line == SMOKE else [], "raw": {}, "seconds": 0.1, "model": "mock"})
    with TestClient(main.app) as c:
        yield c


def student_id(client, name):
    return next(s["id"] for s in client.get("/api/students").json() if s["name"] == name)


def save_green(client, parsed):
    events = [dict(e, confirmed=False) for e in parsed["events"] if e["verdict"] == "ok"]
    payload = {"raw_line": parsed["line"], "entry_date": parsed["entry_date"], "model": "mock",
               "events": [{k: e[k] for k in ("type", "student_id", "status", "amount", "for_month",
                                              "on_date", "note", "confirmed")} for e in events]}
    return client.post("/api/entries", json=payload)


def test_parse_save_dues_flow(client):
    parsed = client.post("/api/parse", json={"line": SMOKE, "entry_date": "2026-10-05"}).json()
    assert [e["verdict"] for e in parsed["events"]] == ["ok", "ok", "ok"]
    r = save_green(client, parsed)
    assert r.status_code == 200 and len(r.json()["ids"]) == 3

    dues = client.get("/api/dues", params={"month": "2026-10"}).json()
    aman = next(r for r in dues["rows"] if r["name"] == "Aman")
    riya = next(r for r in dues["rows"] if r["name"] == "Riya")
    # Aman: fee 1200, paid 1500 for Oct -> Oct cleared, 300 overflow to oldest unpaid (Apr)
    assert aman["balance"] == 0 and aman["paid"] == 1200
    assert aman["promise"]["amount"] == 500 and aman["promise"]["on_date"] == "2026-10-12"
    assert riya["balance"] == 800
    assert all(r["name"] != "Tanvi" for r in dues["rows"])  # left in August

    # V8: same line again is flagged as a duplicate
    again = client.post("/api/parse", json={"line": SMOKE, "entry_date": "2026-10-05"}).json()
    assert any(r["code"] == "V8" for e in again["events"] for r in e["reasons"])

    led = client.get(f"/api/students/{student_id(client, 'Riya')}/ledger").json()
    oct_row = next(m for m in led["months"] if m["month"] == "2026-10")
    assert oct_row["attendance"]["absent"] == 1


def test_undo(client):
    parsed = client.post("/api/parse", json={"line": SMOKE, "entry_date": "2026-10-05"}).json()
    ids = save_green(client, parsed).json()["ids"]
    assert client.delete(f"/api/entries/{ids[1]}").status_code == 200
    assert client.delete(f"/api/entries/{ids[1]}").status_code == 404


def test_validation(client):
    assert client.post("/api/parse", json={"line": "x" * 1001}).status_code == 422
    bad = {"raw_line": "x", "entry_date": "2026-10-05",
           "events": [{"type": "payment", "student_id": 1}]}
    assert client.post("/api/entries", json=bad).status_code == 400
    bad["events"][0] = {"type": "attendance", "student_id": 9999, "status": "absent"}
    assert client.post("/api/entries", json=bad).status_code == 400
    bad["events"][0] = {"type": "payment", "student_id": 1, "amount": 100, "for_month": "2026-13"}
    assert client.post("/api/entries", json=bad).status_code == 422
    assert client.get("/api/dues", params={"month": "oct"}).status_code == 422


def test_pin(client, monkeypatch):
    monkeypatch.setenv("TR_PIN", "4321")
    assert client.get("/api/students").status_code == 401
    assert client.get("/api/students", headers={"X-TR-PIN": "4321"}).status_code == 200
    assert client.get("/api/health").status_code == 200


def test_students_crud(client):
    r = client.post("/api/students", json={"name": "Test Kid", "monthly_fee": 900, "start_month": "2026-10"})
    assert r.status_code == 201
    sid = r.json()["id"]
    r = client.patch(f"/api/students/{sid}", json={"monthly_fee": 1000, "aliases": ["TK"]})
    assert r.json()["monthly_fee"] == 1000 and r.json()["aliases"] == ["TK"]
    csv_bytes = b"name,aliases,batch,monthly_fee,start_month\nNew One,N1,6th,800,2026-10\n"
    r = client.post("/api/students/import", files={"file": ("r.csv", csv_bytes, "text/csv")})
    assert r.json()["count"] == 1


def test_reminder_uses_ledger_amount(client):
    rid = student_id(client, "Riya")
    r = client.post("/api/reminders", json={"student_id": rid, "month": "2026-10", "lang": "hinglish",
                                            "tone": "gentle", "use_model": False}).json()
    assert r["source"] == "fallback" and "₹800" in r["text"] and "Riya" in r["text"]
    assert "October" in r["text"]


def test_reminder_template_validation():
    assert reminders.validate_template("Hi {name}, ₹{amount} for {month} pending.")
    assert not reminders.validate_template("Hi {name}, ₹1500 for {month} pending.")  # no amount slot
    assert not reminders.validate_template("Hi {name}, ₹{amount} for {month}, pay in 2 days.")  # digit
    assert not reminders.validate_template("Hi {name} {name}, ₹{amount} {month}")  # duplicate
    assert not reminders.validate_template("Hi {student}, ₹{amount} {month} {name}")  # extra slot
    assert not reminders.validate_template("Hi [Parent's Name], {name} ₹{amount} {month}")
    english = "Hello, a reminder that {name}'s fees ₹{amount} for {month} are pending. Thank you."
    assert reminders.validate_template(english, "en")
    assert not reminders.validate_template(english, "hinglish")
    for (lang, _), t in reminders.FALLBACK.items():
        assert reminders.validate_template(t, lang)


def test_reminder_model_template_cached(client, monkeypatch):
    calls = []

    def fake_chat(messages, schema, model=None, **kw):
        calls.append(1)
        return {"template": "Namaste ji, {name} ki {month} ki fees ₹{amount} baaki hai. Dhanyavaad."}, 0.1

    monkeypatch.setattr(llm, "chat_json", fake_chat)
    rid = student_id(client, "Riya")
    body = {"student_id": rid, "month": "2026-10", "lang": "hinglish", "tone": "normal"}
    r1 = client.post("/api/reminders", json=body).json()
    r2 = client.post("/api/reminders", json=body).json()
    assert r1["source"] == "model" and r2["source"] == "cached" and len(calls) == 1
    assert "₹800" in r2["text"]


def test_reminder_bad_model_template_falls_back(client, monkeypatch):
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: ({"template": "Pay ₹800 now for {month}"}, 0.1))
    rid = student_id(client, "Riya")
    r = client.post("/api/reminders", json={"student_id": rid, "month": "2026-10", "tone": "firm-but-polite"}).json()
    assert r["source"] == "fallback"


def test_ask_intents(client, monkeypatch):
    parsed = client.post("/api/parse", json={"line": SMOKE, "entry_date": "2026-10-05"}).json()
    save_green(client, parsed)

    def fake(intent, st=None, mt=None):
        monkeypatch.setattr(main.ask, "classify",
                            lambda q, m=None: {"intent": intent, "student_text": st, "month_text": mt})

    fake("who_owes", mt="oct")
    r = client.post("/api/ask", json={"question": "kis kis ka october baaki hai?"}).json()
    assert "Riya ₹800" in r["en"] and "Aman" not in r["en"]

    fake("student_balance", st="riya")
    r = client.post("/api/ask", json={"question": "riya ka kitna baaki hai?"}).json()
    assert "₹5,600" in r["en"]  # Apr..Oct = 7 x 800

    fake("absences", st="riyu", mt="is mahine")
    r = client.post("/api/ask", json={"question": "riyu kitne din nahi aayi is mahine?"}).json()
    assert "absent 1 days" in r["en"]

    fake("paid_list", mt="oct")
    r = client.post("/api/ask", json={"question": "is mahine kisne fees de di?"}).json()
    assert "Aman" in r["en"]

    fake("student_balance", st="neha")
    r = client.post("/api/ask", json={"question": "neha ka kitna baaki"}).json()
    assert len(r["candidates"]) == 2
    r = client.post("/api/ask", json={"question": "neha ka kitna baaki",
                                      "student_id": r["candidates"][0]["id"]}).json()
    assert "owes" in r["en"]

    fake("unknown")
    r = client.post("/api/ask", json={"question": "mausam kaisa hai"}).json()
    assert "4 kinds" in r["en"]
