"""Parse rupee amounts as written in a register: '1,500', '1.5k', '15 sau', 'dedh hazaar'.

Pure code. The model only copies the span; this turns it into an integer.
"""

import re

_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?|[a-z]+")

WORD_NUMBERS = {
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "che": 6, "chah": 6, "saat": 7, "sat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "baarah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnis": 19, "bees": 20, "pachas": 50,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20,
    "dedh": 1.5, "dhai": 2.5, "dhaai": 2.5, "adhai": 2.5,
}
# "sava X" = X + 0.25, "paune X" = X - 0.25 ("sava hazaar" = 1250)
MODIFIERS = {"sava": 0.25, "savaa": 0.25, "paune": -0.25}
THOUSAND = {"k", "hazaar", "hazar", "hajar", "hajaar", "hazzar", "thousand", "hzr"}
HUNDRED = {"sau", "hundred"}


def parse(text: str | None) -> int | None:
    """Return the amount in whole rupees, or None if it can't be read safely."""
    if not text:
        return None
    s = text.lower().replace("₹", " ").replace("/-", " ")
    tokens = _TOKEN.findall(s)

    total = 0.0
    current: float | None = None
    modifier = 0.0
    seen_number = False

    for tok in tokens:
        if tok[0].isdigit():
            num = float(tok.replace(",", ""))
        elif tok in WORD_NUMBERS:
            num = float(WORD_NUMBERS[tok])
        else:
            num = None

        if num is not None:
            if current is not None:
                return None  # two numbers in a row ("1500 500"): ambiguous
            current = num + modifier
            modifier = 0.0
            seen_number = True
        elif tok in MODIFIERS:
            modifier = MODIFIERS[tok]
        elif tok in THOUSAND:
            base = current if current is not None else (1 + modifier if modifier else None)
            if base is None:
                return None
            total += base * 1000
            current, modifier, seen_number = None, 0.0, True
        elif tok in HUNDRED:
            base = current if current is not None else (1 + modifier if modifier else None)
            if base is None:
                return None
            current, modifier, seen_number = base * 100, 0.0, True
        # other words ("rs", "rupaye", "only") are ignored

    if not seen_number:
        return None
    value = total + (current or 0)
    if value <= 0 or abs(value - round(value)) > 1e-9:
        return None
    return int(round(value))
