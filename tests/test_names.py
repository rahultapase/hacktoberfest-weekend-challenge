from pathlib import Path

import pytest

from app import names
from app.textnorm import normalize

ROSTER = names.load_roster_csv(Path(__file__).parent.parent / "eval" / "demo_roster.csv")


def by_name(n):
    return next(s for s in ROSTER if s["name"] == n)


def test_roster_loaded():
    assert len(ROSTER) == 18
    assert by_name("Aman")["aliases"] == ["Amaan", "Amu"]
    assert by_name("Tanvi")["end_month"] == "2026-08"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("aman", "Aman"),
        ("Aman", "Aman"),
        ("amaan", "Aman"),
        ("amu", "Aman"),
        ("riyu", "Riya"),
        ("riya", "Riya"),
        ("priya", "Priya"),
        ("pinky", "Priyanka"),
        ("priyanka", "Priyanka"),
        ("rohit", "Rohit"),
        ("rohan", "Rohan"),
        ("neha 6th", "Neha Sharma"),
        ("neha 8th", "Neha Gupta"),
        ("aman ki mummy", "Aman"),
        ("pinky ki mummy ne", "Priyanka"),
        ("kanu", "Karan"),
        ("monu", "Mohit"),
        ("shreyaa", "Shreya"),
    ],
)
def test_match_confident(text, expected):
    m = names.match(text, ROSTER)
    assert m.student is not None, m
    assert m.student["name"] == expected


def test_match_ambiguous_neha():
    m = names.match("neha", ROSTER)
    assert m.student is None
    top = {c["name"] for c, _ in m.candidates[:2]}
    assert top == {"Neha Sharma", "Neha Gupta"}


def test_match_unknown():
    m = names.match("rahul", ROSTER)
    assert m.student is None


def test_match_empty():
    assert names.match("", ROSTER).student is None


def test_word_count_ignores_stopwords():
    assert names.name_word_count("pinky ki mummy ne") == 1
    assert names.name_word_count("riya nahi aayi aman ne 1500 diye") > 3


def test_scan_finds_mentions():
    line = normalize("riya nahi aayi, aman ne 1500 diye oct ke, baaki 500 next week")
    found = names.scan(line, ROSTER)
    ids = [m.student_ids for m in found]
    assert [by_name("Riya")["id"]] in ids
    assert [by_name("Aman")["id"]] in ids
    assert len(found) == 2


def test_scan_neha_batch_alias_is_one_mention():
    found = names.scan(normalize("neha 6th absent"), ROSTER)
    assert len(found) == 1
    assert found[0].student_ids == [by_name("Neha Sharma")["id"]]


def test_scan_ambiguous_neha():
    found = names.scan(normalize("neha absent"), ROSTER)
    assert len(found) == 1
    assert set(found[0].student_ids) == {by_name("Neha Sharma")["id"], by_name("Neha Gupta")["id"]}


def test_scan_no_false_positives_on_common_words():
    assert names.scan(normalize("aaj bijli nahi thi, kal test hai sabka"), ROSTER) == []
