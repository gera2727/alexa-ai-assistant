"""Parsing of the ``AMAZON.DATE`` slot.

Alexa resolves spoken dates to ISO-like strings, for example:

* ``"2026-11-04"`` for "amanhã" or "quarta-feira";
* ``"2026-W45"`` for "esta semana" or "para a semana";
* ``"2026-11"`` for "novembro" (not supported yet).

Note: since Python 3.11, ``date.fromisoformat("2026-W45")`` *succeeds* and
returns the Monday of that week, so weeks must be matched before days.
"""

# TODO(v0.2): remove. With free-form questions the LLM resolves dates, so the AMAZON.DATE slot is no longer used.

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from assistant.integrations.moodle import TIMEZONE

_WEEK = re.compile(r"(\d{4})-W(\d{2})")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class DateRange:
    start: datetime
    end: datetime  # exclusive
    is_week: bool


def _midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=TIMEZONE)


def parse_amazon_date(value: str | None) -> DateRange | None:
    """Return the range a slot value covers, or ``None`` if unsupported."""
    if not value:
        return None
    if week := _WEEK.fullmatch(value):
        monday = date.fromisocalendar(int(week[1]), int(week[2]), 1)
        return DateRange(_midnight(monday), _midnight(monday) + timedelta(days=7), is_week=True)
    if _DAY.fullmatch(value):
        day = date.fromisoformat(value)
        return DateRange(_midnight(day), _midnight(day) + timedelta(days=1), is_week=False)
    return None
