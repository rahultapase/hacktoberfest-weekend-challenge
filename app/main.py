"""FastAPI app: API (spec section 8) + static UI.

Run (local only, default):   python -m app.main
Run on home Wi-Fi (opt-in):  $env:TR_PIN="1234"; python -m app.main --lan
"""

import argparse
import csv
import hmac
import io
import os
import threading
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import ask, db, ledger, llm, parser, reminders, verifier

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
MONTH_RE = r"^\d{4}-(0[1-9]|1[0-2])$"
MONTHS_RE = r"^\d{4}-(0[1-9]|1[0-2])(,\d{4}-(0[1-9]|1[0-2]))*$"
SAVE_TYPES = ("attendance", "payment", "promise", "fee_set", "note")
STATE = {"lan": False}


def today() -> date:
    v = os.environ.get("TR_TODAY")
    return date.fromisoformat(v) if v else date.today()


def conn():
    c = db.connect()
    db.init(c)
    return c


@asynccontextmanager
async def lifespan(_app):
    c = conn()
    db.ensure_roster(c)
    c.close()
    if os.environ.get("TR_NO_WARMUP") != "1":
        threading.Thread(target=llm.warmup, daemon=True).start()
    yield


app = FastAPI(title="Tuition Register", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.middleware("http")
async def pin_and_headers(request: Request, call_next):
    pin = os.environ.get("TR_PIN")
    path = request.url.path
    if pin and path.startswith("/api/") and path != "/api/health":
        given = request.headers.get("x-tr-pin", "")
        if not hmac.compare_digest(given.encode(), pin.encode()):
            return JSONResponse({"detail": "PIN required"}, status_code=401)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'")
    return resp


# ---------- models ----------

class ParseIn(BaseModel):
    line: str = Field(min_length=1, max_length=1000)
    entry_date: date | None = None
    model: str | None = Field(default=None, max_length=64)


class EventIn(BaseModel):
    type: Literal["attendance", "payment", "promise", "fee_set", "note"]
    student_id: int
    status: Literal["present", "absent", "late"] | None = None
    amount: int | None = Field(default=None, ge=1, le=1_000_000)
    for_month: str | None = Field(default=None, pattern=MONTHS_RE, max_length=80)
    on_date: date | None = None
    note: str | None = Field(default=None, max_length=500)
    confirmed: bool = False


class EntriesIn(BaseModel):
    raw_line: str = Field(min_length=1, max_length=1000)
    entry_date: date
    events: list[EventIn] = Field(min_length=1, max_length=50)
    model: str | None = Field(default=None, max_length=64)


class StudentIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    aliases: list[str] = Field(default_factory=list, max_length=10)
    batch: str | None = Field(default=None, max_length=20)
    monthly_fee: int = Field(ge=0, le=100_000)
    start_month: str = Field(pattern=MONTH_RE)
    end_month: str | None = Field(default=None, pattern=MONTH_RE)
    parent_label: str | None = Field(default=None, max_length=80)


class StudentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    aliases: list[str] | None = Field(default=None, max_length=10)
    batch: str | None = Field(default=None, max_length=20)
    monthly_fee: int | None = Field(default=None, ge=0, le=100_000)
    start_month: str | None = Field(default=None, pattern=MONTH_RE)
    end_month: str | None = Field(default=None, pattern=MONTH_RE)
    parent_label: str | None = Field(default=None, max_length=80)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    student_id: int | None = None


class ReminderIn(BaseModel):
    student_id: int
    month: str = Field(pattern=MONTH_RE)
    lang: Literal["hinglish", "en", "hi"] = "hinglish"
    tone: Literal["gentle", "normal", "firm-but-polite"] = "gentle"
    use_model: bool = True


# ---------- routes ----------

@app.get("/api/health")
def health():
    h = llm.health()
    h.update({"offline_note": "Runs on this computer. No internet needed.",
              "pin_required": bool(os.environ.get("TR_PIN")), "lan": STATE["lan"],
              "today": today().isoformat()})
    return h


@app.post("/api/parse")
def parse(body: ParseIn):
    entry = body.entry_date or today()
    c = conn()
    try:
        roster = db.list_students(c)
        try:
            res = parser.parse_line(body.line, entry, roster, body.model)
        except llm.LLMError as e:
            raise HTTPException(503, f"Local model not available: {e}")
        existing = db.list_entries(c, entry_date=entry.isoformat())
        cards = verifier.verify(body.line, entry, res["events"], roster, existing)
    finally:
        c.close()
    return {"line": body.line, "entry_date": entry.isoformat(), "model": res["model"],
            "seconds": round(res["seconds"], 2), "events": cards}


@app.post("/api/entries")
def save_entries(body: EntriesIn):
    c = conn()
    try:
        ids_ok = {s["id"] for s in db.list_students(c)}
        for e in body.events:
            if e.student_id not in ids_ok:
                raise HTTPException(400, f"Unknown student id {e.student_id}")
            if e.type in ("payment", "promise", "fee_set") and not e.amount:
                raise HTTPException(400, f"{e.type} needs an amount")
            if e.type == "attendance" and not e.status:
                raise HTTPException(400, "attendance needs a status")
        saved = []
        for e in body.events:
            on_date = e.on_date.isoformat() if e.on_date else None
            if e.type == "attendance" and not on_date:
                on_date = body.entry_date.isoformat()
            saved.append(db.add_entry(c, {
                "student_id": e.student_id, "type": e.type, "entry_date": body.entry_date.isoformat(),
                "status": e.status, "amount": e.amount, "for_month": e.for_month, "on_date": on_date,
                "note": e.note, "raw_line": body.raw_line,
                "verdict": "confirmed_by_user" if e.confirmed else "ok",
                "model": body.model or llm.DEFAULT_MODEL,
            }))
    finally:
        c.close()
    return {"ids": saved}


@app.get("/api/entries")
def get_entries(entry_date: date | None = None, student_id: int | None = None,
                limit: int = Query(100, ge=1, le=1000)):
    c = conn()
    try:
        return db.list_entries(c, entry_date.isoformat() if entry_date else None, student_id, limit)
    finally:
        c.close()


@app.delete("/api/entries/{eid}")
def delete_entry(eid: int):
    c = conn()
    try:
        if not db.delete_entry(c, eid):
            raise HTTPException(404, "Not found")
    finally:
        c.close()
    return {"deleted": eid}


@app.get("/api/students")
def students():
    c = conn()
    try:
        ss = db.list_students(c)
        by = db.entries_by_student(c)
    finally:
        c.close()
    cur = ledger.ym(today())
    for s in ss:
        a = ledger.allocate(s, by.get(s["id"], []), cur)
        s["outstanding"], s["advance"] = a["outstanding"], a["advance"]
        s["active"] = ledger.is_active(s, cur)
    return ss


@app.post("/api/students", status_code=201)
def create_student(body: StudentIn):
    c = conn()
    try:
        sid = db.add_student(c, body.model_dump())
        return db.get_student(c, sid)
    finally:
        c.close()


@app.patch("/api/students/{sid}")
def patch_student(sid: int, body: StudentPatch):
    c = conn()
    try:
        if not db.get_student(c, sid):
            raise HTTPException(404, "Not found")
        db.update_student(c, sid, body.model_dump(exclude_unset=True))
        return db.get_student(c, sid)
    finally:
        c.close()


@app.post("/api/students/import")
async def import_students(file: UploadFile = File(...)):
    data = await file.read(200_001)
    if len(data) > 200_000:
        raise HTTPException(413, "File too large")
    try:
        text = data.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        students_in = [StudentIn(
            name=r["name"].strip(),
            aliases=[a.strip() for a in (r.get("aliases") or "").split("|") if a.strip()],
            batch=(r.get("batch") or "").strip() or None,
            monthly_fee=int(r["monthly_fee"]),
            start_month=r["start_month"].strip(),
            end_month=(r.get("end_month") or "").strip() or None,
        ) for r in rows]
    except (KeyError, ValueError, UnicodeDecodeError) as e:
        raise HTTPException(400, f"Could not read CSV: {e}")
    c = conn()
    try:
        for s in students_in:
            db.add_student(c, s.model_dump())
    finally:
        c.close()
    return {"count": len(students_in)}


@app.get("/api/dues")
def dues(month: str | None = Query(None, pattern=MONTH_RE)):
    t = today()
    month = month or ledger.ym(t)
    c = conn()
    try:
        rows = ledger.dues_for_month(db.list_students(c), db.entries_by_student(c), month, t)
    finally:
        c.close()
    return {"month": month, "rows": rows,
            "total_due": sum(r["due"] for r in rows),
            "total_paid": sum(r["paid"] for r in rows),
            "total_balance": sum(max(r["balance"], 0) for r in rows)}


@app.get("/api/students/{sid}/ledger")
def student_ledger(sid: int):
    t = today()
    c = conn()
    try:
        s = db.get_student(c, sid)
        if not s:
            raise HTTPException(404, "Not found")
        es = db.entries_by_student(c).get(sid, [])
    finally:
        c.close()
    alloc = ledger.allocate(s, es, ledger.ym(t))
    for row in alloc["months"]:
        row["attendance"] = ledger.attendance(es, row["month"])
    return {"student": s, **alloc, "promises": ledger.promises(es, t),
            "entries": sorted(es, key=lambda e: (e["entry_date"], e["id"]), reverse=True)}


@app.post("/api/ask")
def ask_route(body: AskIn):
    c = conn()
    try:
        return ask.answer(c, body.question, today(), student_id=body.student_id)
    except llm.LLMError as e:
        raise HTTPException(503, f"Local model not available: {e}")
    finally:
        c.close()


@app.post("/api/reminders")
def reminder(body: ReminderIn):
    t = today()
    c = conn()
    try:
        s = db.get_student(c, body.student_id)
        if not s:
            raise HTTPException(404, "Not found")
        es = db.entries_by_student(c).get(s["id"], [])
        alloc = ledger.allocate(s, es, max(body.month, ledger.ym(t)))
        row = next((r for r in alloc["months"] if r["month"] == body.month), None)
        if not row or row["balance"] <= 0:
            raise HTTPException(400, "Nothing due for that month")
        return reminders.build(c, s, body.month, row["balance"], body.lang, body.tone,
                               use_model=body.use_model)
    finally:
        c.close()


# ---------- static UI ----------

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


def main() -> None:
    import uvicorn

    ap = argparse.ArgumentParser(description="Tuition Register (local)")
    ap.add_argument("--lan", action="store_true", help="listen on 0.0.0.0 so a phone on home Wi-Fi can connect")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--roster", help="roster CSV to import if the DB is empty (default: eval/demo_roster.csv)")
    ap.add_argument("--db", help="SQLite file (default: data/private/register.db)")
    ap.add_argument("--model", help="Ollama model (default: gemma4:e2b)")
    args = ap.parse_args()
    if args.roster:
        os.environ["TR_ROSTER"] = args.roster
    if args.db:
        os.environ["TR_DB"] = args.db
    if args.model:
        llm.DEFAULT_MODEL = args.model
    host = "127.0.0.1"
    if args.lan:
        host = "0.0.0.0"
        STATE["lan"] = True
        print("WARNING: LAN mode. Anyone on this network can open the register.")
        if os.environ.get("TR_PIN"):
            print("A PIN (TR_PIN) is required for every API call. It is a simple shared PIN, not real auth.")
        else:
            print("No TR_PIN set. Set one with $env:TR_PIN='1234' before starting. Use only on a trusted home network.")
    print(f"Tuition Register on http://{'<this-computer-ip>' if args.lan else host}:{args.port}  model={llm.DEFAULT_MODEL}")
    uvicorn.run(app, host=host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
