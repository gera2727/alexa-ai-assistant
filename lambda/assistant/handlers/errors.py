from __future__ import annotations

import logging

from ask_sdk_core.dispatch_components import AbstractExceptionHandler

from assistant.handlers.base import respond
from assistant.integrations.llm import LLMError

logger = logging.getLogger(__name__)

GENERIC_ERROR = "Desculpa, tive um problema a responder. Tenta outra vez daqui a pouco."
RATE_LIMITED = "Estou com muitos pedidos neste momento. Tenta outra vez daqui a um minuto."


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Last line of defence: log the error and never leave the user in silence."""

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.exception("Unhandled error", exc_info=exception)
        if isinstance(exception, LLMError) and exception.rate_limited:
            return respond(handler_input, RATE_LIMITED)
        return respond(handler_input, GENERIC_ERROR)
