import pytest

from assistant.dates import parse_amazon_date


def test_day():
    r = parse_amazon_date("2026-11-04")
    assert (r.start.day, r.end.day, r.is_week) == (4, 5, False)


def test_week_is_not_mistaken_for_a_day():
    # date.fromisoformat("2026-W45") succeeds on Python 3.11+, which is the trap this guards against.
    r = parse_amazon_date("2026-W45")
    assert r.is_week
    assert (r.start.day, r.start.weekday()) == (2, 0)  # Monday 2 November
    assert (r.end - r.start).days == 7


@pytest.mark.parametrize("value", [None, "", "2026-11", "2026", "PRESENT_REF", "2026-WE"])
def test_unsupported_values(value):
    assert parse_amazon_date(value) is None
