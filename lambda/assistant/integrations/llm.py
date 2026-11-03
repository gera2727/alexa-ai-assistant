"""LLM client: Groq's OpenAI-compatible chat completions API, with tool calling.

Only this module knows which provider is used (see ADR 0003). Switching to another
OpenAI-compatible provider is a matter of changing ``API_URL`` and the model name.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT_S = 4.0

# (url, headers, JSON payload, timeout) -> decoded JSON. Injected in tests.
Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


class LLMError(RuntimeError):
    def __init__(self, message: str, *, rate_limited: bool = False) -> None:
        super().__init__(message)
        self.rate_limited = rate_limited


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Reply:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    message: dict[str, Any] = field(default_factory=dict)  # raw assistant message, to send back in the history


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)  # noqa: S310 (constant https URL)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise LLMError(f"LLM API returned HTTP {error.code}", rate_limited=error.code == 429) from error


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    try:
        arguments = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return arguments if isinstance(arguments, dict) else {}


class GroqClient:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT_S,
        transport: Transport = _post_json,
    ) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "alexa-ai-assistant",
        }
        self._model = model
        self._timeout = timeout
        self._transport = transport

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> Reply:
        payload: dict[str, Any] = {"model": self._model, "messages": messages, "temperature": 0.2, "max_tokens": 300}
        if tools:
            payload["tools"] = tools
        response = self._transport(API_URL, self._headers, payload, self._timeout)
        try:
            message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMError("Unexpected LLM response") from error

        calls = [
            ToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=_parse_arguments(call["function"].get("arguments")),
            )
            for call in message.get("tool_calls") or []
        ]
        return Reply(content=(message.get("content") or "").strip(), tool_calls=calls, message=message)
