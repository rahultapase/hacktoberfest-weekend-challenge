"""Shared text normalization used by the verifier and the name scanner."""

import re

_NON_WORD = re.compile(r"[^\w\s.,]", re.UNICODE)
_LOOSE_PUNCT = re.compile(r"(?<!\d)[.,]|[.,](?!\d)")
_SPACES = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    """Lowercase, drop punctuation/emoji, keep '.' and ',' only inside numbers."""
    if not text:
        return ""
    s = text.lower().replace("\u2019", "'").replace("'", "")
    s = s.replace("_", " ")
    s = _NON_WORD.sub(" ", s)
    s = _LOOSE_PUNCT.sub(" ", s)
    return _SPACES.sub(" ", s).strip()
