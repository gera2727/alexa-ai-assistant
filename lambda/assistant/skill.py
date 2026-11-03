"""Composition root: wires handlers and their dependencies into a skill."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ask_sdk_core.skill_builder import SkillBuilder

from assistant.agent import Assistant
from assistant.config import get_setting
from assistant.handlers.builtin import (
    CancelOrStopIntentHandler,
    FallbackIntentHandler,
    HelpIntentHandler,
    LaunchRequestHandler,
    SessionEndedRequestHandler,
)
from assistant.handlers.errors import CatchAllExceptionHandler
from assistant.handlers.question import Answerer, QuestionIntentHandler
from assistant.integrations.llm import DEFAULT_MODEL, GroqClient
from assistant.integrations.moodle_api import TIMEZONE, MoodleApi
from assistant.tools import build_toolbox


def _lisbon_now() -> datetime:
    return datetime.now(TIMEZONE)


def assistant_from_config(clock: Callable[[], datetime] = _lisbon_now) -> Assistant:
    moodle = MoodleApi(get_setting("MOODLE_URL"), get_setting("MOODLE_TOKEN"))
    llm = GroqClient(get_setting("GROQ_API_KEY"), model=get_setting("GROQ_MODEL", DEFAULT_MODEL))
    return Assistant(llm, build_toolbox(moodle, clock), clock)


class _LazyAssistant:
    """Builds the real assistant on first use, so a missing setting becomes a spoken error, not a cold-start crash."""

    def __init__(self) -> None:
        self._assistant: Assistant | None = None

    def answer(self, question: str) -> str:
        if self._assistant is None:
            self._assistant = assistant_from_config()
        return self._assistant.answer(question)


def build_skill(assistant: Answerer | None = None) -> SkillBuilder:
    builder = SkillBuilder()
    for handler in (
        LaunchRequestHandler(),
        QuestionIntentHandler(assistant or _LazyAssistant()),
        HelpIntentHandler(),
        CancelOrStopIntentHandler(),
        FallbackIntentHandler(),
        SessionEndedRequestHandler(),
    ):
        builder.add_request_handler(handler)
    builder.add_exception_handler(CatchAllExceptionHandler())
    return builder
