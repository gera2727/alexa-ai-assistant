from datetime import datetime
from pathlib import Path

import pytest

from assistant.integrations.moodle import TIMEZONE, parse_events

FIXTURES = Path(__file__).parent / "fixtures"

# Tuesday, 3 November 2026, 14:00 in Lisbon. All tests are relative to this instant.
NOW = datetime(2026, 11, 3, 14, 0, tzinfo=TIMEZONE)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def sample_events():
    return parse_events((FIXTURES / "moodle_sample.ics").read_text(encoding="utf-8"))
