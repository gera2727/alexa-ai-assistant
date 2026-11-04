"""The catch-all intent: whatever the user asks goes to the assistant."""

from __future__ import annotations

from typing import Dict, List, Protocol, Sequence

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import get_slot_value, is_intent_name

from assistant.handlers.base import respond

ASK_AGAIN = "Não percebi a pergunta. Podes repetir?"
# Earlier turns kept in the Alexa session so follow-ups like "e a seguir?" make sense. Kept short: it is
# sent with every request and resent to the LLM each time.
HISTORY_KEY = "history"
MAX_HISTORY_MESSAGES = 6  # three questions and answers

History = List[Dict[str, str]]


class Answerer(Protocol):
    def answer(self, question: str, history: Sequence[dict[str, str]] = ()) -> str: ...


class QuestionIntentHandler(AbstractRequestHandler):
    def __init__(self, assistant: Answerer) -> None:
        self._assistant = assistant

    def can_handle(self, handler_input):
        return is_intent_name("QuestionIntent")(handler_input)

    def handle(self, handler_input):
        question = (get_slot_value(handler_input, "question") or "").strip()
        if not question:
            return respond(handler_input, ASK_AGAIN, keep_open=True)
        attributes = handler_input.attributes_manager.session_attributes
        history: History = list(attributes.get(HISTORY_KEY, []))
        answer = self._assistant.answer(question, history)
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        attributes[HISTORY_KEY] = history[-MAX_HISTORY_MESSAGES:]
        # One-shot ("Alexa, pergunta ao meu painel ...") ends; a conversation started with "abre" stays open.
        session = handler_input.request_envelope.session
        return respond(handler_input, answer, keep_open=bool(session and not session.new))
