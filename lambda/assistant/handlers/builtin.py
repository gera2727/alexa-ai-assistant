"""Handlers for Alexa's built-in requests and intents."""

from __future__ import annotations

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name, is_request_type

from assistant.handlers.base import respond

WELCOME = "Olá! Pergunta-me o que quiseres sobre as tuas aulas, testes, entregas ou materiais do Moodle."
HELP = "Podes perguntar, por exemplo: o que tenho amanhã, quando é o teste de ARQCP, ou que materiais há em LAPR3."
GOODBYE = "Até já! Bom estudo."
FALLBACK = "Não percebi. Experimenta perguntar, por exemplo, o que tens amanhã."


def _is_any_intent(handler_input, *names: str) -> bool:
    return any(is_intent_name(name)(handler_input) for name in names)


class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        return respond(handler_input, WELCOME, keep_open=True)


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        return respond(handler_input, HELP, keep_open=True)


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return _is_any_intent(handler_input, "AMAZON.CancelIntent", "AMAZON.StopIntent")

    def handle(self, handler_input):
        return respond(handler_input, GOODBYE)


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return _is_any_intent(handler_input, "AMAZON.FallbackIntent", "AMAZON.NavigateHomeIntent")

    def handle(self, handler_input):
        return respond(handler_input, FALLBACK, keep_open=True)


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        return handler_input.response_builder.response
