"""Composition root: wires handlers and their dependencies into a skill."""

from __future__ import annotations

from datetime import datetime

from ask_sdk_core.skill_builder import SkillBuilder

from assistant.config import get_setting
from assistant.handlers.builtin import (
    CancelOrStopIntentHandler,
    FallbackIntentHandler,
    HelpIntentHandler,
    LaunchRequestHandler,
    SessionEndedRequestHandler,
)
from assistant.handlers.calendar import (
    Clock,
    EventProvider,
    EventsByDateIntentHandler,
    NextEventIntentHandler,
    UpcomingEventsIntentHandler,
)
from assistant.handlers.errors import CatchAllExceptionHandler
from assistant.integrations.moodle import TIMEZONE, MoodleCalendar


def _lisbon_now() -> datetime:
    return datetime.now(TIMEZONE)


def _lazy_moodle_calendar() -> EventProvider:
    """Read the URL on first use, so a missing setting becomes a spoken error, not a cold-start crash."""

    def provider():
        return MoodleCalendar(get_setting("MOODLE_ICAL_URL"))()

    return provider


# TODO(v0.2): wire QuestionIntentHandler with a lazily built Assistant (LLM + Moodle tools).
def build_skill(events: EventProvider | None = None, clock: Clock = _lisbon_now) -> SkillBuilder:
    events = events or _lazy_moodle_calendar()
    builder = SkillBuilder()
    for handler in (
        LaunchRequestHandler(),
        UpcomingEventsIntentHandler(events, clock),
        EventsByDateIntentHandler(events, clock),
        NextEventIntentHandler(events, clock),
        HelpIntentHandler(),
        CancelOrStopIntentHandler(),
        FallbackIntentHandler(),
        SessionEndedRequestHandler(),
    ):
        builder.add_request_handler(handler)
    builder.add_exception_handler(CatchAllExceptionHandler())
    return builder
