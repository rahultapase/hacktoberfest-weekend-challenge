"""Display helpers: Indian rupee grouping and month names (en / hinglish / hi)."""

MONTH_EN = ["January", "February", "March", "April", "May", "June", "July", "August",
            "September", "October", "November", "December"]
MONTH_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त",
            "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]


def inr(n: int) -> str:
    """1500 -> '1,500', 150000 -> '1,50,000'."""
    neg = n < 0
    s = str(abs(int(n)))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if neg else "") + s


def month_name(ym: str, lang: str = "en", with_year: bool = False) -> str:
    y, m = ym.split("-")
    name = (MONTH_HI if lang == "hi" else MONTH_EN)[int(m) - 1]
    return f"{name} {y}" if with_year else name
