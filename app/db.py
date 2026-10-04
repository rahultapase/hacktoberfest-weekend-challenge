"""SQLite storage (spec section 6). Parameterized SQL only.

DB file: TR_DB env var, default data/private/register.db (gitignored).
Roster: TR_ROSTER env var or --roster flag, default eval/demo_roster.csv (synthetic).
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from app import names

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "private" / "register.db"
DEFAULT_ROSTER = ROOT / "eval" / "demo_roster.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  aliases TEXT NOT NULL DEFAULT '[]',
  batch TEXT,
  monthly_fee INTEGER NOT NULL,
  start_month TEXT NOT NULL,
  end_month TEXT,
  parent_label TEXT
);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,
  student_id INTEGER REFERENCES students(id),
  type TEXT NOT NULL,
  entry_date TEXT NOT NULL,
  status TEXT,
  amount INTEGER,
  for_month TEXT,
  on_date TEXT,
  note TEXT,
  raw_line TEXT NOT NULL,
  verdict TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entries_student ON entries(student_id);
CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(entry_date);
CREATE TABLE IF NOT EXISTS reminder_templates (
  lang TEXT NOT NULL,
  tone TEXT NOT NULL,
  template TEXT NOT NULL,
  model TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (lang, tone)
);
"""

STUDENT_FIELDS = ["name", "aliases", "batch", "monthly_fee", "start_month", "end_month", "parent_label"]


def db_path() -> Path:
    return Path(os.environ.get("TR_DB", DEFAULT_DB))


def roster_path() -> Path:
    return Path(os.environ.get("TR_ROSTER", DEFAULT_ROSTER))


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    p = Path(path) if path else db_path()
    if str(p) != ":memory:":
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _student(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["aliases"] = json.loads(d["aliases"] or "[]")
    return d


def list_students(conn) -> list[dict]:
    return [_student(r) for r in conn.execute("SELECT * FROM students ORDER BY name")]


def get_student(conn, sid: int) -> dict | None:
    r = conn.execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
    return _student(r) if r else None


def add_student(conn, s: dict) -> int:
    cur = conn.execute(
        "INSERT INTO students (name, aliases, batch, monthly_fee, start_month, end_month, parent_label)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (s["name"], json.dumps(s.get("aliases") or []), s.get("batch"), int(s["monthly_fee"]),
         s["start_month"], s.get("end_month"), s.get("parent_label")),
    )
    conn.commit()
    return cur.lastrowid


def update_student(conn, sid: int, changes: dict) -> None:
    cols, vals = [], []
    for k in STUDENT_FIELDS:  # whitelist: column names never come from the request
        if k in changes:
            v = changes[k]
            if k == "aliases":
                v = json.dumps(v or [])
            cols.append(f"{k} = ?")
            vals.append(v)
    if not cols:
        return
    vals.append(sid)
    conn.execute(f"UPDATE students SET {', '.join(cols)} WHERE id = ?", vals)
    conn.commit()


def import_roster(conn, path: str | Path, replace: bool = False) -> int:
    rows = names.load_roster_csv(path)
    if replace:
        conn.execute("DELETE FROM entries")
        conn.execute("DELETE FROM students")
    for r in rows:
        r = dict(r)
        r.pop("id", None)
        add_student(conn, r)
    return len(rows)


def ensure_roster(conn, path: str | Path | None = None) -> int:
    """Import the roster only if the students table is empty."""
    n = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if n:
        return 0
    return import_roster(conn, path or roster_path())


def add_entry(conn, e: dict) -> int:
    cur = conn.execute(
        "INSERT INTO entries (student_id, type, entry_date, status, amount, for_month, on_date, note,"
        " raw_line, verdict, model, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (e["student_id"], e["type"], e["entry_date"], e.get("status"), e.get("amount"),
         e.get("for_month"), e.get("on_date"), e.get("note"), e["raw_line"], e["verdict"],
         e["model"], datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return cur.lastrowid


def delete_entry(conn, eid: int) -> bool:
    cur = conn.execute("DELETE FROM entries WHERE id = ?", (eid,))
    conn.commit()
    return cur.rowcount > 0


def list_entries(conn, entry_date: str | None = None, student_id: int | None = None,
                 limit: int = 500) -> list[dict]:
    sql, args = "SELECT e.*, s.name AS student_name FROM entries e LEFT JOIN students s ON s.id = e.student_id", []
    where = []
    if entry_date:
        where.append("e.entry_date = ?")
        args.append(entry_date)
    if student_id is not None:
        where.append("e.student_id = ?")
        args.append(student_id)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY e.entry_date DESC, e.id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args)]


def entries_by_student(conn) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for r in conn.execute("SELECT * FROM entries ORDER BY entry_date, id"):
        d = dict(r)
        out.setdefault(d["student_id"], []).append(d)
    return out


def get_template(conn, lang: str, tone: str) -> str | None:
    r = conn.execute("SELECT template FROM reminder_templates WHERE lang = ? AND tone = ?",
                     (lang, tone)).fetchone()
    return r[0] if r else None


def set_template(conn, lang: str, tone: str, template: str, model: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO reminder_templates (lang, tone, template, model, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (lang, tone, template, model, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
