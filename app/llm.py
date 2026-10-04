"""Ollama client, prompts and JSON schemas.

Only talks to the local Ollama server (default http://localhost:11434). No other network calls.
"""

import json
import os
import time

import httpx

OLLAMA_URL = os.environ.get("TR_OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("TR_MODEL", "gemma4:e2b")
TIMEOUT = httpx.Timeout(180.0, connect=5.0)

EVENT_TYPES = ["attendance", "payment", "promise", "fee_set", "note"]

PARSE_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": EVENT_TYPES},
                    "student_text": {"type": "string"},
                    "status": {"type": ["string", "null"], "enum": ["present", "absent", "late", None]},
                    "amount_text": {"type": ["string", "null"]},
                    "month_text": {"type": ["string", "null"]},
                    "date_text": {"type": ["string", "null"]},
                    "note_text": {"type": ["string", "null"]},
                },
                "required": ["type", "student_text"],
            },
        }
    },
    "required": ["events"],
}

PARSE_SYSTEM = """You read one line from a home-tuition teacher's register and extract events as JSON.
The line can be Hindi, English or Hinglish (Hindi in Latin letters), often lowercase with typos.
It can also be a WhatsApp message from a parent.

Event types:
- attendance: a student was present, absent or late. "nahi aaya/aayi", "absent", "chhutti" = absent. "aaya/aayi", "present" = present. "late" = late.
- payment: money received. "diye", "de diya", "de di", "bheja/bheje/bhej di", "paid", "mil gaye", "received", "jama".
- promise: money that will come later. "baaki", "bacha", "baad mein dega/degi", "next week dega", "will pay".
- fee_set: the monthly fee is set or changed. "fees ab 1200", "fee 1000 from nov".
- note: something about one specific student that is not attendance or money.

Rules:
- Copy every value EXACTLY as written in the line. Never translate, normalize, convert or compute.
  amount_text is the amount as written ("1.5k", "dedh hazaar", "1,500"). month_text is the month as written ("oct", "pichle mahine", "sep oct"). date_text is a day as written ("kal", "next week", "12 ko").
- student_text is ONLY the student's name as written (1 or 2 words, e.g. "riyu", "neha 6th"). Never copy the whole line.
- One event per fact. A line can have several students and several facts.
- If one payment covers two months ("sep oct dono ke"), output ONE payment with month_text "sep oct".
- For "baaki 500 next week" after a payment, the promise belongs to the same student.
- "baaki sab aaye" (everyone else came) is not an event.
- Use null for anything not written. Do not guess.
- General remarks with no specific student ("kal test hai", "aaj chhutti hai sabki") have no events: return {"events": []}."""

# Few-shot examples. Names here are NOT in the demo roster and phrasings are kept
# different from eval/gold.jsonl, so there is no train/test leakage.
FEW_SHOT = [
    ("meera aur tushar nahi aaye, gauri late aayi",
     [{"type": "attendance", "student_text": "meera", "status": "absent"},
      {"type": "attendance", "student_text": "tushar", "status": "absent"},
      {"type": "attendance", "student_text": "gauri", "status": "late"}]),
    ("Ma'am Dev ki fees 1000 bhej di hai 🙏",
     [{"type": "payment", "student_text": "Dev", "amount_text": "1000"}]),
    ("sonu ne 800 diye, baaki 400 parso",
     [{"type": "payment", "student_text": "sonu", "amount_text": "800"},
      {"type": "promise", "student_text": "sonu", "amount_text": "400", "date_text": "parso"}]),
    ("gugu ki mummy ne 2k diye aug ke",
     [{"type": "payment", "student_text": "gugu", "amount_text": "2k", "month_text": "aug"}]),
    ("gauri ne 1600 diye jul aug dono ke",
     [{"type": "payment", "student_text": "gauri", "amount_text": "1600", "month_text": "jul aug"}]),
    ("tushar ki fees ab 900 hogi dec se",
     [{"type": "fee_set", "student_text": "tushar", "amount_text": "900", "month_text": "dec"}]),
    ("Meera paid 1200 for August, Dev was absent",
     [{"type": "payment", "student_text": "Meera", "amount_text": "1200", "month_text": "August"},
      {"type": "attendance", "student_text": "Dev", "status": "absent"}]),
    ("kal holiday hai, padhai nahi hogi", []),
]


def _example_json(events: list[dict]) -> str:
    full = []
    for e in events:
        full.append({
            "type": e["type"], "student_text": e["student_text"], "status": e.get("status"),
            "amount_text": e.get("amount_text"), "month_text": e.get("month_text"),
            "date_text": e.get("date_text"), "note_text": e.get("note_text"),
        })
    return json.dumps({"events": full}, ensure_ascii=False)


def parse_messages(line: str) -> list[dict]:
    msgs = [{"role": "system", "content": PARSE_SYSTEM}]
    for ex_line, ex_events in FEW_SHOT:
        msgs.append({"role": "user", "content": ex_line})
        msgs.append({"role": "assistant", "content": _example_json(ex_events)})
    msgs.append({"role": "user", "content": line})
    return msgs


class LLMError(RuntimeError):
    pass


def chat_json(messages: list[dict], schema: dict, model: str | None = None,
              temperature: float = 0.0, num_predict: int = 512) -> tuple[dict, float]:
    """Call Ollama /api/chat with a JSON schema. Returns (parsed_json, seconds)."""
    model = model or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": messages,
        "format": schema,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": temperature, "num_ctx": 2048, "num_predict": num_predict},
    }
    if model.startswith("gemma4") or model.startswith("qwen3"):
        body["think"] = False
    t0 = time.perf_counter()
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise LLMError(f"Ollama not reachable at {OLLAMA_URL}: {e}") from e
    secs = time.perf_counter() - t0
    if r.status_code != 200:
        raise LLMError(f"Ollama error {r.status_code}: {r.text[:200]}")
    content = r.json().get("message", {}).get("content", "")
    try:
        return json.loads(content), secs
    except json.JSONDecodeError as e:
        raise LLMError(f"Model returned invalid JSON: {content[:200]}") from e


def health(model: str | None = None) -> dict:
    model = model or DEFAULT_MODEL
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3.0)
        names = [m["name"] for m in r.json().get("models", [])]
        return {"ollama": True, "model": model, "model_available": model in names, "models": names}
    except (httpx.HTTPError, ValueError):
        return {"ollama": False, "model": model, "model_available": False, "models": []}


def warmup(model: str | None = None) -> None:
    """Load the model into memory so the first real line isn't a ~1 min wait."""
    try:
        chat_json([{"role": "user", "content": "ok"}],
                  {"type": "object", "properties": {"ok": {"type": "boolean"}}}, model, num_predict=8)
    except LLMError:
        pass
