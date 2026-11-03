"""Handlers that answer questions about the Moodle calendar.

Handlers receive their dependencies (where events come from, what time it is)
through the constructor, so tests can inject fakes instead of hitting the network.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import get_slot_value, is_intent_name

from assistant import speech
from assistant.dates import parse_amazon_date
from assistant.handlers.base import respond
from assistant.integrations import moodle
from assistant.integrations.moodle import Event

# TODO(v0.2): replace these fixed intents with a single QuestionIntent (handlers/question.py)
# whose free-form question is answered by the LLM using Moodle tools.
EventProvider = Callable[[], list[Event]]
Clock = Callable[[], datetime]

UPCOMING_DAYS = 7
UNSUPPORTED_DATE = "Desculpa, só percebo dias ou semanas, como amanhã ou para a semana."


class _CalendarHandler(AbstractRequestHandler):
    intent_name: str

    def __init__(self, events: EventProvider, clock: Clock) -> None:
        self._events = events
        self._clock = clock

    def can_handle(self, handler_input):
        return is_intent_name(self.intent_name)(handler_input)


class UpcomingEventsIntentHandler(_CalendarHandler):
    """ "o que tenho esta semana" -> the next 7 days."""

    intent_name = "UpcomingEventsIntent"

    def handle(self, handler_input):
        now = self._clock()
        events = moodle.events_between(self._events(), now, now + timedelta(days=UPCOMING_DAYS))
        return respond(handler_input, speech.event_list(events, now, f"nos próximos {UPCOMING_DAYS} dias"))


class EventsByDateIntentHandler(_CalendarHandler):
    """ "o que tenho amanhã" / "para a semana" -> AMAZON.DATE slot."""

    intent_name = "EventsByDateIntent"

    def handle(self, handler_input):
        date_range = parse_amazon_date(get_slot_value(handler_input, "date"))
        if date_range is None:
            return respond(handler_input, UNSUPPORTED_DATE, keep_open=True)
        now = self._clock()
        events = moodle.events_between(self._events(), date_range.start, date_range.end)
        return respond(handler_input, speech.event_list(events, now, speech.describe_range(date_range, now)))


class NextEventIntentHandler(_CalendarHandler):
    """ "qual é a próxima entrega" -> first future event."""

    intent_name = "NextEventIntent"

    def handle(self, handler_input):
        now = self._clock()
        return respond(handler_input, speech.next_event(moodle.next_event(self._events(), now), now))
