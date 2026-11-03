from __future__ import annotations

import logging

from ask_sdk_core.dispatch_components import AbstractExceptionHandler

from assistant.handlers.base import respond

logger = logging.getLogger(__name__)

# TODO(v0.2): add a specific message when the LLM rate limit (HTTP 429) is hit.
GENERIC_ERROR = "Não consegui ler o teu calendário do Moodle. Tenta outra vez daqui a pouco."


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Last line of defence: log the error and never leave the user in silence."""

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.exception("Unhandled error", exc_info=exception)
        return respond(handler_input, GENERIC_ERROR)
