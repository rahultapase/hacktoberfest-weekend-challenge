"""Resolve month and date spans (Hinglish + English) against the entry date.

Pure code. 'kal' is ambiguous in Hindi (yesterday or tomorrow), so callers pass
kind='past' (payments, attendance) or kind='future' (promises).
"""

import re
from datetime import date, timedelta

from app.textnorm import normalize

MONTHS = {
    1: ["jan", "january", "janvari", "janwari", "janauary"],
    2: ["feb", "february", "farvari", "farwari", "febuary"],
    3: ["mar", "march", "maarch"],
    4: ["apr", "april", "aprail", "aprl"],
    5: ["may", "mai", "mei"],
    6: ["jun", "june", "joon"],
    7: ["jul", "july", "julai"],
    8: ["aug", "august", "agast", "agust"],
    9: ["sep", "sept", "september", "sitambar", "setember"],
    10: ["oct", "october", "aktubar", "octobar", "octomber", "okt"],
    11: ["nov", "november", "navambar", "novmber"],
    12: ["dec", "december", "disambar", "dismbar"],
}
MONTH_WORDS = {w: m for m, ws in MONTHS.items() for w in ws}

THIS_MONTH = ["is mahine", "iss mahine", "is mahina", "this month", "is month", "current month"]
LAST_MONTH = ["pichle mahine", "pichhle mahine", "pichla mahina", "pichhla mahina", "last month",
              "previous month", "pichle month"]
NEXT_MONTH = ["agle mahine", "agla mahina", "next month", "agle month"]

VAGUE = {"baad mein", "baad me", "later", "jaldi", "soon", "baad mai", "thode din mein", "kabhi"}

WEEKDAYS = {
    0: ["monday", "mon", "somvar", "somwar"],
    1: ["tuesday", "tue", "mangalvar", "mangalwar"],
    2: ["wednesday", "wed", "budhvar", "budhwar"],
    3: ["thursday", "thu", "guruvar", "guruwar", "brihaspativar"],
    4: ["friday", "fri", "shukravar", "shukrawar"],
    5: ["saturday", "sat", "shanivar", "shaniwar"],
    6: ["sunday", "sun", "ravivar", "raviwar", "itvar", "itwar"],
}
WEEKDAY_WORDS = {w: d for d, ws in WEEKDAYS.items() for w in ws}


def _ym(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def _shift_month(d: date, delta: int) -> tuple[int, int]:
    idx = d.year * 12 + (d.month - 1) + delta
    return idx // 12, idx % 12 + 1


def _nearest_year(month: int, entry: date) -> int:
    """Pick the year that puts `month` nearest to the entry month (ties go to the past)."""
    best = None
    for y in (entry.year - 1, entry.year, entry.year + 1):
        dist = (y * 12 + month) - (entry.year * 12 + entry.month)
        key = (abs(dist), 0 if dist <= 0 else 1)
        if best is None or key < best[0]:
            best = (key, y)
    return best[1]


def _contains(s: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", s) is not None


def resolve_months(text: str | None, entry: date) -> list[str]:
    """All months mentioned, in order. 'sep oct dono ke' -> ['2026-09', '2026-10']."""
    s = normalize(text)
    if not s:
        return []
    for phrases, delta in ((THIS_MONTH, 0), (LAST_MONTH, -1), (NEXT_MONTH, 1)):
        if any(_contains(s, p) for p in phrases):
            return [_ym(*_shift_month(entry, delta))]
    tokens = s.split()
    year = next((int(t) for t in tokens if re.fullmatch(r"20\d\d", t)), None)
    out = []
    for t in tokens:
        if t in MONTH_WORDS:
            m = MONTH_WORDS[t]
            ym = _ym(year if year else _nearest_year(m, entry), m)
            if ym not in out:
                out.append(ym)
    return out


def resolve_month(text: str | None, entry: date) -> str | None:
    """Exactly one month, or None."""
    months = resolve_months(text, entry)
    return months[0] if len(months) == 1 else None


def is_vague(text: str | None) -> bool:
    s = normalize(text)
    return any(_contains(s, v) for v in VAGUE)


def resolve_date(text: str | None, entry: date, kind: str = "past") -> str | None:
    """Resolve a date span to YYYY-MM-DD. kind: 'past' or 'future' (used for 'kal'/'parso')."""
    s = normalize(text)
    if not s:
        return None
    sign = 1 if kind == "future" else -1
    toks = s.split()

    def has(*words):
        return any(_contains(s, w) for w in words)

    if has("aaj", "today", "abhi"):
        return entry.isoformat()
    if has("yesterday"):
        return (entry - timedelta(days=1)).isoformat()
    if has("tomorrow"):
        return (entry + timedelta(days=1)).isoformat()
    if has("parso", "parson"):
        return (entry + timedelta(days=2 * sign)).isoformat()
    if has("kal"):
        return (entry + timedelta(days=sign)).isoformat()
    if has("next week", "agle hafte", "agle week", "agla hafta", "agle hafta", "agli week"):
        return (entry + timedelta(days=7)).isoformat()
    if has("last week", "pichle hafte", "pichle week"):
        return (entry - timedelta(days=7)).isoformat()

    for t in toks:
        if t in WEEKDAY_WORDS:
            wd = WEEKDAY_WORDS[t]
            if kind == "future":
                delta = (wd - entry.weekday()) % 7 or 7
                return (entry + timedelta(days=delta)).isoformat()
            delta = (entry.weekday() - wd) % 7 or 7
            return (entry - timedelta(days=delta)).isoformat()

    # "12 ko", "12 oct", "oct 12", "12th", "20 tarikh"
    day = None
    for t in toks:
        m = re.fullmatch(r"(\d{1,2})(st|nd|rd|th)?", t)
        if m and 1 <= int(m.group(1)) <= 31:
            day = int(m.group(1))
            break
    if day is None:
        return None
    month_tokens = [MONTH_WORDS[t] for t in toks if t in MONTH_WORDS]
    try:
        if month_tokens:
            mth = month_tokens[0]
            return date(_nearest_year(mth, entry), mth, day).isoformat()
        if kind == "future":
            y, mth = (entry.year, entry.month) if day >= entry.day else _shift_month(entry, 1)
        else:
            y, mth = (entry.year, entry.month) if day <= entry.day else _shift_month(entry, -1)
        return date(y, mth, day).isoformat()
    except ValueError:
        return None  # e.g. 31 Sep
