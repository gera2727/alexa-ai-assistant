"""The catch-all intent: whatever the user asks goes to the assistant."""

from __future__ import annotations

from typing import Protocol

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import get_slot_value, is_intent_name

from assistant.handlers.base import respond

ASK_AGAIN = "Não percebi a pergunta. Podes repetir?"


class Answerer(Protocol):
    def answer(self, question: str) -> str: ...


class QuestionIntentHandler(AbstractRequestHandler):
    def __init__(self, assistant: Answerer) -> None:
        self._assistant = assistant

    def can_handle(self, handler_input):
        return is_intent_name("QuestionIntent")(handler_input)

    def handle(self, handler_input):
        question = (get_slot_value(handler_input, "question") or "").strip()
        if not question:
            return respond(handler_input, ASK_AGAIN, keep_open=True)
        # One-shot ("Alexa, pergunta à agenda do isep ...") ends; a conversation started with "abre" stays open.
        session = handler_input.request_envelope.session
        return respond(handler_input, self._assistant.answer(question), keep_open=bool(session and not session.new))
