import json

import pytest

from assistant.integrations.llm import API_URL, GroqClient, LLMError


def _client(response, sent):
    def transport(url, headers, payload, timeout):
        sent.update(url=url, headers=headers, payload=payload)
        return response

    return GroqClient("secret-key", model="test-model", transport=transport)


def test_plain_answer():
    sent = {}
    reply = _client({"choices": [{"message": {"role": "assistant", "content": " Olá! "}}]}, sent).chat(
        [{"role": "user", "content": "olá"}]
    )
    assert reply.content == "Olá!"
    assert reply.tool_calls == []
    assert sent["url"] == API_URL
    assert sent["headers"]["Authorization"] == "Bearer secret-key"
    assert sent["payload"]["model"] == "test-model"
    assert "tools" not in sent["payload"]


def test_tool_calls_are_parsed():
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "list_courses", "arguments": "{}"}},
            {"id": "c2", "type": "function", "function": {"name": "x", "arguments": json.dumps({"course": "ARQCP"})}},
        ],
    }
    sent = {}
    reply = _client({"choices": [{"message": message}]}, sent).chat([], tools=[{"type": "function"}])
    assert [(c.id, c.name, c.arguments) for c in reply.tool_calls] == [
        ("c1", "list_courses", {}),
        ("c2", "x", {"course": "ARQCP"}),
    ]
    assert reply.message == {"role": "assistant", "content": "", "tool_calls": message["tool_calls"]}
    assert sent["payload"]["tools"] == [{"type": "function"}]


def test_malformed_tool_arguments_become_empty():
    message = {"tool_calls": [{"id": "c1", "function": {"name": "x", "arguments": "not json"}}]}
    reply = _client({"choices": [{"message": message}]}, {}).chat([])
    assert reply.tool_calls[0].arguments == {}


def test_unexpected_response_raises():
    with pytest.raises(LLMError):
        _client({"error": "boom"}, {}).chat([])


def test_reasoning_models_think_briefly_and_extra_fields_are_dropped():
    sent = {}
    response = {"choices": [{"message": {"role": "assistant", "content": "Olá", "reasoning": "..."}}]}
    client = GroqClient("k", model="openai/gpt-oss-120b", transport=lambda u, h, p, t: sent.update(p) or response)
    reply = client.chat([])
    assert sent["reasoning_effort"] == "low"
    assert reply.message == {"role": "assistant", "content": "Olá"}


def test_other_models_get_no_reasoning_option():
    sent = {}
    _client({"choices": [{"message": {"content": "x"}}]}, sent).chat([])
    assert "reasoning_effort" not in sent["payload"]
