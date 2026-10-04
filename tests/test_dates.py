from datetime import date

import pytest

from app import dates

D = date(2026, 10, 5)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("oct", "2026-10"),
        ("october", "2026-10"),
        ("October", "2026-10"),
        ("sep", "2026-09"),
        ("sept", "2026-09"),
        ("dec", "2026-12"),
        ("nov", "2026-11"),
        ("may", "2026-05"),
        ("apr", "2026-04"),
        ("is mahine", "2026-10"),
        ("this month", "2026-10"),
        ("pichle mahine", "2026-09"),
        ("last month", "2026-09"),
        ("agle mahine", "2026-11"),
        ("next month", "2026-11"),
        ("oct ke", "2026-10"),
        ("from nov", "2026-11"),
        ("janvari", "2027-01"),
        ("oct 2025", "2025-10"),
        ("kuch bhi", None),
        ("", None),
    ],
)
def test_resolve_month(text, expected):
    assert dates.resolve_month(text, D) == expected


def test_nearest_month_prefers_past_when_far_ahead():
    # From May 2026, "dec" is 7 months ahead -> previous December.
    assert dates.resolve_month("dec", date(2026, 5, 10)) == "2025-12"


def test_two_months():
    assert dates.resolve_months("sep oct", D) == ["2026-09", "2026-10"]
    assert dates.resolve_months("sep aur oct dono ke", D) == ["2026-09", "2026-10"]
    assert dates.resolve_month("sep oct", D) is None  # single resolver refuses


@pytest.mark.parametrize(
    "text,kind,expected",
    [
        ("aaj", "past", "2026-10-05"),
        ("today", "past", "2026-10-05"),
        ("kal", "past", "2026-10-04"),
        ("kal", "future", "2026-10-06"),
        ("parso", "past", "2026-10-03"),
        ("parso", "future", "2026-10-07"),
        ("yesterday", "future", "2026-10-04"),
        ("tomorrow", "past", "2026-10-06"),
        ("next week", "future", "2026-10-12"),
        ("agle hafte", "future", "2026-10-12"),
        ("12 ko", "future", "2026-10-12"),
        ("12 oct", "future", "2026-10-12"),
        ("12 oct tak", "future", "2026-10-12"),
        ("oct 12", "past", "2026-10-12"),
        ("3 ko", "future", "2026-11-03"),
        ("3 ko", "past", "2026-10-03"),
        ("20 tarikh", "past", "2026-09-20"),
        ("kuch bhi", "past", None),
        ("", "past", None),
    ],
)
def test_resolve_date(text, kind, expected):
    assert dates.resolve_date(text, D, kind) == expected


def test_vague():
    assert dates.is_vague("baad mein")
    assert dates.is_vague("later")
    assert not dates.is_vague("kal")
