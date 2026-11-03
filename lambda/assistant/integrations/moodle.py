"""Moodle calendar integration (iCal export).

Moodle lets each user export their calendar as an ``.ics`` URL that contains a
personal auth token. This module downloads and parses that feed.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar

TIMEZONE = ZoneInfo("Europe/Lisbon")

# Alexa waits ~8 s for a response, so the download must fail fast.
DEFAULT_TIMEOUT_S = 4.0


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime  # always timezone-aware, in TIMEZONE
    course: str | None = None


def fetch_ics(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> str:
    if not url.startswith("https://"):
        raise ValueError("The Moodle calendar URL must use https://")
    request = urllib.request.Request(url, headers={"User-Agent": "alexa-ai-assistant"})  # noqa: S310 (scheme checked above)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read().decode("utf-8")


def _to_local_datetime(value: date | datetime) -> datetime:
    """Normalise DTSTART (date or datetime, naive or aware) to TIMEZONE."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=TIMEZONE)
        return value.astimezone(TIMEZONE)
    # All-day event: treat as midnight local time.
    return datetime(value.year, value.month, value.day, tzinfo=TIMEZONE)


def _course_of(component) -> str | None:
    """Moodle stores the course short name in CATEGORIES."""
    categories = component.get("CATEGORIES")
    if categories is None:
        return None
    entries = categories if isinstance(categories, list) else [categories]
    names = [str(name) for entry in entries for name in entry.cats]
    return names[0] if names else None


def parse_events(ics_text: str) -> list[Event]:
    """Parse an iCal document into events sorted by start time."""
    calendar = Calendar.from_ical(ics_text)
    events = [
        Event(
            title=str(component.get("SUMMARY", "Sem título")).strip(),
            start=_to_local_datetime(component.get("DTSTART").dt),
            course=_course_of(component),
        )
        for component in calendar.walk("VEVENT")
        if component.get("DTSTART") is not None
    ]
    return sorted(events, key=lambda event: event.start)


def events_between(events: list[Event], start: datetime, end: datetime) -> list[Event]:
    """Events with ``start <= event.start < end``."""
    return [event for event in events if start <= event.start < end]


# TODO(v0.2): rename this module to moodle_calendar.py. events_on() and next_event() go away
# when the fixed intents are replaced by free-form questions answered by the LLM.
def events_on(events: list[Event], day: date) -> list[Event]:
    midnight = datetime(day.year, day.month, day.day, tzinfo=TIMEZONE)
    return events_between(events, midnight, midnight + timedelta(days=1))


def next_event(events: list[Event], now: datetime) -> Event | None:
    return next((event for event in events if event.start >= now), None)


class MoodleCalendar:
    """Event provider backed by a Moodle iCal URL."""

    def __init__(self, ical_url: str) -> None:
        self._ical_url = ical_url

    def __call__(self) -> list[Event]:
        return parse_events(fetch_ics(self._ical_url))
