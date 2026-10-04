import pytest

from app.amounts import parse


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1500", 1500),
        ("1,500", 1500),
        ("₹1500", 1500),
        ("rs 1500", 1500),
        ("1500/-", 1500),
        ("1.5k", 1500),
        ("2k", 2000),
        ("15 sau", 1500),
        ("1 hazaar", 1000),
        ("1 hazar", 1000),
        ("dedh hazaar", 1500),
        ("dhai hazaar", 2500),
        ("paanch sau", 500),
        ("ek hazaar paanch sau", 1500),
        ("sava hazaar", 1250),
        ("2 thousand", 2000),
        ("abc", None),
        ("", None),
        (None, None),
        ("0", None),
        ("1.5", None),  # not a whole rupee amount
    ],
)
def test_parse(text, expected):
    assert parse(text) == expected
