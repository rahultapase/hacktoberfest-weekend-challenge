"""Roster name matching (fuzzy, with nicknames) and a coverage scan of the raw line."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

from app.textnorm import normalize

# Words that often surround a name in a span ("aman ki mummy ne") but aren't the name.
STOPWORDS = {
    "ne", "ki", "ka", "ke", "ko", "se", "aur", "and", "mummy", "mumma", "mummyji", "papa",
    "mom", "dad", "maa", "mother", "father", "ji", "maam", "madam", "didi", "bhaiya",
    "wali", "wala", "ka", "beta", "beti", "bhi",
}

CONFIDENT_SCORE = 85
MARGIN = 10
SCAN_SCORE = 90


@dataclass
class Match:
    student: dict | None
    candidates: list = field(default_factory=list)  # [(student, score)], best first
    reason: str = ""  # "ok" | "ambiguous" | "low_score" | "unknown" | "empty"


@dataclass
class Mention:
    text: str
    student_ids: list


def load_roster_csv(path: str | Path) -> list[dict]:
    """Read the roster CSV (name,aliases,batch,monthly_fee,start_month[,end_month])."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            out.append({
                "id": i,
                "name": row["name"].strip(),
                "aliases": [a.strip() for a in (row.get("aliases") or "").split("|") if a.strip()],
                "batch": (row.get("batch") or "").strip() or None,
                "monthly_fee": int(row["monthly_fee"]),
                "start_month": row["start_month"].strip(),
                "end_month": (row.get("end_month") or "").strip() or None,
            })
    return out


def _keys(student: dict) -> list[str]:
    return [normalize(k) for k in [student["name"], *student.get("aliases", [])] if k]


def clean_name_text(text: str | None) -> str:
    return " ".join(t for t in normalize(text).split() if t not in STOPWORDS)


def name_word_count(text: str | None) -> int:
    return len(clean_name_text(text).split())


def match(text: str | None, roster: list[dict]) -> Match:
    """Resolve a name span to one roster student, or explain why not."""
    q = clean_name_text(text)
    if not q:
        return Match(None, [], "empty")

    exact = [s for s in roster if q in _keys(s)]
    scored = []
    for s in roster:
        score = 100.0 if s in exact else max(fuzz.WRatio(q, k) for k in _keys(s))
        scored.append((s, score))
    scored.sort(key=lambda x: -x[1])
    candidates = [c for c in scored if c[1] >= 60][:3]

    if len(exact) == 1:
        return Match(exact[0], candidates, "ok")
    if len(exact) > 1:
        return Match(None, [(s, 100.0) for s in exact], "ambiguous")

    best_s, best = scored[0]
    second = scored[1][1] if len(scored) > 1 else 0
    if best >= CONFIDENT_SCORE and best - second >= MARGIN:
        return Match(best_s, candidates, "ok")
    if not candidates:
        return Match(None, [], "unknown")
    return Match(None, candidates, "ambiguous" if best >= CONFIDENT_SCORE else "low_score")


def scan(norm_line: str, roster: list[dict]) -> list[Mention]:
    """Find roster names/aliases mentioned in an already-normalized line (1 and 2 word n-grams).

    Used by V7 to catch students the model dropped. 2-word matches ("neha 6th") win over
    their 1-word parts. Uses plain ratio (not WRatio) so short common words don't match.
    """
    tokens = norm_line.split()
    keymap: dict[str, set] = {}
    for s in roster:
        for k in _keys(s):
            keymap.setdefault(k, set()).add(s["id"])

    def lookup(gram: str) -> set:
        if len(gram) < 3:
            return set()
        if gram in keymap:
            return set(keymap[gram])
        ids = set()
        for k, sids in keymap.items():
            if abs(len(k) - len(gram)) <= 2 and fuzz.ratio(gram, k) >= SCAN_SCORE:
                ids |= sids
        return ids

    found: list[Mention] = []
    used = set()
    for i in range(len(tokens) - 1):
        gram = f"{tokens[i]} {tokens[i + 1]}"
        if gram in keymap:  # exact only for 2-grams
            found.append(Mention(gram, sorted(keymap[gram])))
            used |= {i, i + 1}
    for i, t in enumerate(tokens):
        if i in used:
            continue
        ids = lookup(t)
        if ids:
            found.append(Mention(t, sorted(ids)))

    # one mention per distinct student set, keep first text
    seen, out = set(), []
    for m in found:
        key = tuple(m.student_ids)
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out
