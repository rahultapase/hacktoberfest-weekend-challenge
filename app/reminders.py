"""Fee reminders (spec section 10). The model writes the tone; code writes the numbers.

The model returns a template with exactly {name}, {amount}, {month} and no digits.
Code validates it (else falls back to a built-in template), caches it per (lang, tone),
and fills in values from the ledger.
"""

import re

from app import db, llm
from app.fmt import inr, month_name

LANGS = ["hinglish", "en", "hi"]
TONES = ["gentle", "normal", "firm-but-polite"]
PLACEHOLDERS = {"name", "amount", "month"}

FALLBACK = {
    ("hinglish", "gentle"): "Namaste! {name} ki {month} ki fees ₹{amount} abhi baaki hai. Jab suvidha ho bhej dijiyega. Dhanyavaad 🙏",
    ("hinglish", "normal"): "Namaste, {name} ki {month} ki fees ₹{amount} baaki hai. Kripya is hafte bhej dein. Dhanyavaad.",
    ("hinglish", "firm-but-polite"): "Namaste, {name} ki {month} ki fees ₹{amount} ab tak baaki hai. Kripya jaldi se jaldi bhej dijiye. Dhanyavaad.",
    ("en", "gentle"): "Hello! Just a gentle reminder that {name}'s fees of ₹{amount} for {month} are pending. Please send whenever convenient. Thank you 🙏",
    ("en", "normal"): "Hello, {name}'s tuition fees of ₹{amount} for {month} are pending. Please send them this week. Thank you.",
    ("en", "firm-but-polite"): "Hello, {name}'s tuition fees of ₹{amount} for {month} are still pending. Kindly clear them at the earliest. Thank you.",
    ("hi", "gentle"): "नमस्ते! {name} की {month} की फ़ीस ₹{amount} अभी बाकी है। जब सुविधा हो, भेज दीजिएगा। धन्यवाद 🙏",
    ("hi", "normal"): "नमस्ते, {name} की {month} की फ़ीस ₹{amount} बाकी है। कृपया इस हफ़्ते भेज दें। धन्यवाद।",
    ("hi", "firm-but-polite"): "नमस्ते, {name} की {month} की फ़ीस ₹{amount} अब तक बाकी है। कृपया जल्द से जल्द भेज दीजिए। धन्यवाद।",
}

LANG_DESC = {
    "hinglish": "Hinglish (Hindi written in English letters, like a WhatsApp message)",
    "en": "simple Indian English",
    "hi": "Hindi in Devanagari script",
}
TONE_DESC = {
    "gentle": "very gentle and warm, no pressure",
    "normal": "polite and clear",
    "firm-but-polite": "firm but still respectful, asking to pay soon",
}

STYLE_EXAMPLE = {
    "hinglish": "\"Namaste ji, {name} ki {month} ki fees ₹{amount} baaki hai, kripya bhej dijiye. Dhanyavaad.\"",
    "en": "\"Hello, {name}'s fees of ₹{amount} for {month} are pending. Thank you.\"",
    "hi": "\"नमस्ते जी, {name} की {month} की फ़ीस ₹{amount} बाकी है। धन्यवाद।\"",
}

TEMPLATE_SCHEMA = {
    "type": "object",
    "properties": {"template": {"type": "string"}},
    "required": ["template"],
}

_DIGITS = re.compile(r"[0-9\u0966-\u096F]")


HINGLISH_WORDS = {"hai", "ki", "ka", "ke", "baaki", "kripya", "dhanyavaad", "namaste", "ji", "dijiye",
                  "dijiyega", "fees", "abhi", "bhej"}
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def _lang_ok(t: str, lang: str | None) -> bool:
    if lang == "hi":
        return len(_DEVANAGARI.findall(t)) >= 10
    if lang == "hinglish":
        words = set(re.findall(r"[a-z]+", t.lower()))
        return len(words & HINGLISH_WORDS) >= 3 and not _DEVANAGARI.search(t)
    if lang == "en":
        return not _DEVANAGARI.search(t)
    return True


def validate_template(t: str | None, lang: str | None = None) -> bool:
    if not t or len(t) > 400:
        return False
    if "[" in t or "]" in t or "<" in t or ">" in t:  # leaked slots like "[Parent's Name]"
        return False
    if not _lang_ok(t, lang):
        return False
    found = re.findall(r"\{([^{}]*)\}", t)
    if sorted(found) != sorted(PLACEHOLDERS):  # each exactly once, nothing else in braces
        return False
    stripped = re.sub(r"\{(name|amount|month)\}", "", t)
    if "{" in stripped or "}" in stripped:
        return False
    return not _DIGITS.search(stripped)


def fill(template: str, name: str, amount: int, month: str) -> str:
    return (template.replace("{name}", name).replace("{amount}", inr(amount))
            .replace("{month}", month))


def generate_template(lang: str, tone: str, model: str | None = None) -> str | None:
    prompt = (
        "Write a short WhatsApp message from a home-tuition teacher to a student's parent, "
        f"reminding them about pending tuition fees. Language: {LANG_DESC[lang]}. Tone: {TONE_DESC[tone]}.\n"
        "Use these placeholders exactly once each: {name} for the student's name, {amount} for the "
        "amount, {month} for the month. Write ₹ before {amount}. Do NOT write any digits or numbers. "
        "Do not use any other placeholder or brackets. Maximum 2 sentences plus a thank you.\n"
        f"Example of the language style (write your own, in the requested tone): {STYLE_EXAMPLE[lang]}\n"
        "Return JSON: {\"template\": \"...\"}"
    )
    try:
        out, _ = llm.chat_json([{"role": "user", "content": prompt}], TEMPLATE_SCHEMA, model,
                               temperature=0.3, num_predict=200)
    except llm.LLMError:
        return None
    t = (out.get("template") or "").strip()
    return t if validate_template(t, lang) else None


def get_template(conn, lang: str, tone: str, model: str | None = None,
                 use_model: bool = True) -> tuple[str, str]:
    """Return (template, source) with source in cached | model | fallback."""
    cached = db.get_template(conn, lang, tone)
    if cached and validate_template(cached, lang):
        return cached, "cached"
    if use_model:
        t = generate_template(lang, tone, model)
        if t:
            db.set_template(conn, lang, tone, t, model or llm.DEFAULT_MODEL)
            return t, "model"
    return FALLBACK[(lang, tone)], "fallback"


def build(conn, student: dict, month: str, amount: int, lang: str, tone: str,
          model: str | None = None, use_model: bool = True) -> dict:
    template, source = get_template(conn, lang, tone, model, use_model)
    text = fill(template, student["name"], amount, month_name(month, lang))
    return {"text": text, "template": template, "source": source, "amount": amount, "month": month}
