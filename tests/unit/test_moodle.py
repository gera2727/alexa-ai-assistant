from datetime import date, timedelta

import pytest

from assistant.integrations import moodle


def test_parse_events_sorted_with_course(sample_events):
    assert [e.title for e in sample_events] == [
        "Entrega Sprint 1",
        "Teste de ESINF",
        "Entrega relatório LAPR3",
        "Exame de época normal",
    ]
    assert sample_events[0].course == "LAPR3"
    assert sample_events[-1].course is None


def test_utc_times_are_converted_to_lisbon(sample_events):
    # 23:59 UTC in November is 23:59 in Lisbon (winter time, UTC+0).
    assert sample_events[0].start.strftime("%H:%M") == "23:59"
    assert sample_events[0].start.tzinfo == moodle.TIMEZONE


def test_all_day_event_starts_at_local_midnight(sample_events):
    exam = sample_events[-1]
    assert (exam.start.hour, exam.start.minute) == (0, 0)


def test_events_between_is_half_open(sample_events, now):
    upcoming = moodle.events_between(sample_events, now, now + timedelta(days=7))
    assert len(upcoming) == 3


def test_events_on(sample_events):
    assert [e.title for e in moodle.events_on(sample_events, date(2026, 11, 6))] == ["Teste de ESINF"]


def test_next_event(sample_events, now):
    assert moodle.next_event(sample_events, now).title == "Entrega Sprint 1"
    assert moodle.next_event([], now) is None


def test_fetch_rejects_non_https_urls():
    with pytest.raises(ValueError, match="https"):
        moodle.fetch_ics("file:///etc/passwd")
