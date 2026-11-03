from datetime import datetime

import pytest

from assistant.integrations.moodle_api import TIMEZONE

# Tuesday, 3 November 2026, 14:00 in Lisbon. All tests are relative to this instant.
NOW = datetime(2026, 11, 3, 14, 0, tzinfo=TIMEZONE)


@pytest.fixture
def now() -> datetime:
    return NOW
