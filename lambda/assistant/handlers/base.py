from __future__ import annotations

from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response

REPROMPT = "Queres saber mais alguma coisa?"


def respond(handler_input: HandlerInput, speech: str, *, keep_open: bool = False) -> Response:
    """Speak ``speech``; keep the session open (with a reprompt) only if asked."""
    builder = handler_input.response_builder.speak(speech)
    if keep_open:
        builder.ask(REPROMPT)
    else:
        builder.set_should_end_session(True)
    return builder.response
