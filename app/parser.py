"""parse_line(): one register line -> raw events (verbatim spans) from the local model.

CLI smoke test:
    python -m app.parser "riya nahi aayi, aman ne 1500 diye oct ke, baaki 500 next week"
"""

import json
import sys
from datetime import date
from pathlib import Path

from app import llm

SPAN_FIELDS = ["student_text", "amount_text", "month_text", "date_text", "note_text"]
FIELDS = ["type", "student_text", "status", *SPAN_FIELDS[1:]]


def clean_events(raw: dict | list | None) -> list[dict]:
    """Normalize model output: '' -> None, drop junk, inherit student for bare promises,
    merge identical events within one line."""
    items = raw.get("events", []) if isinstance(raw, dict) else (raw or [])
    out: list[dict] = []
    for item in items:
        if not isinstance(item, dict) or item.get("type") not in llm.EVENT_TYPES:
            continue
        ev = {}
        for f in FIELDS:
            v = item.get(f)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                v = str(v)
            if isinstance(v, str):
                v = v.strip()
                if v == "" or v.lower() in {"null", "none", "n/a"}:
                    v = None
            elif v is not None:
                v = None
            ev[f] = v
        if ev["status"] not in (None, "present", "absent", "late"):
            ev["status"] = None
        if not ev["student_text"] and ev["type"] == "promise" and out:
            ev["student_text"] = out[-1]["student_text"]
        if not ev["student_text"]:
            ev["student_text"] = None
        if ev not in out:
            out.append(ev)
    return out


def parse_line(line: str, entry_date: date | None = None, roster: list | None = None,
               model: str | None = None) -> dict:
    """Ask the model for raw events. entry_date/roster are accepted for API symmetry; the
    model never sees the roster or dates (code resolves those)."""
    raw, secs = llm.chat_json(llm.parse_messages(line), llm.PARSE_SCHEMA, model)
    return {"events": clean_events(raw), "raw": raw, "seconds": secs, "model": model or llm.DEFAULT_MODEL}


def _main(argv: list[str]) -> int:
    from app import names, verifier

    if not argv:
        print(__doc__)
        return 2
    line = " ".join(argv)
    roster = names.load_roster_csv(Path(__file__).parent.parent / "eval" / "demo_roster.csv")
    entry = date.today()
    res = parse_line(line, entry, roster)
    print(f"model={res['model']}  {res['seconds']:.2f}s")
    print("raw events:")
    print(json.dumps(res["events"], ensure_ascii=False, indent=2))
    print("verdicts:")
    for v in verifier.verify(line, entry, res["events"], roster):
        tag = "OK     " if v["verdict"] == "ok" else "CONFIRM"
        detail = {k: v[k] for k in ("type", "student_name", "status", "amount", "for_month", "on_date") if v.get(k)}
        reasons = "; ".join(r["en"] for r in v["reasons"])
        print(f"  [{tag}] {detail} {('-> ' + reasons) if reasons else ''}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(_main(sys.argv[1:]))
