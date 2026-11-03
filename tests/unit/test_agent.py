import json

from assistant.agent import MAX_TOOL_ROUNDS, NO_ANSWER, Assistant
from assistant.integrations.llm import Reply, ToolCall
from assistant.tools import Tool, ToolBox


class ScriptedLLM:
    """Returns the given replies in order and records what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append((list(messages), tools))
        return self.replies.pop(0)


def _tool_reply(*calls):
    return Reply(content="", tool_calls=list(calls), message={"role": "assistant", "tool_calls": ["..."]})


def _toolbox():
    return ToolBox([Tool("list_courses", "", {"type": "object", "properties": {}}, lambda: [{"shortname": "ARQCP"}])])


def _assistant(llm, now):
    return Assistant(llm, _toolbox(), lambda: now)


def test_direct_answer_with_date_in_system_prompt(now):
    llm = ScriptedLLM(Reply(content="Olá!"))
    assert _assistant(llm, now).answer("olá") == "Olá!"
    system = llm.calls[0][0][0]["content"]
    assert "2026-11-03 14:00 (terça-feira)" in system


def test_tool_results_are_sent_back(now):
    llm = ScriptedLLM(_tool_reply(ToolCall("c1", "list_courses", {})), Reply(content="Tens ARQCP."))
    assert _assistant(llm, now).answer("que disciplinas tenho") == "Tens ARQCP."
    second_messages = llm.calls[1][0]
    assert second_messages[-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": json.dumps([{"shortname": "ARQCP"}]),
    }


def test_stops_calling_tools_after_max_rounds(now):
    loop = [_tool_reply(ToolCall(f"c{i}", "list_courses", {})) for i in range(MAX_TOOL_ROUNDS)]
    llm = ScriptedLLM(*loop, Reply(content="Resposta final."))
    assert _assistant(llm, now).answer("?") == "Resposta final."
    assert llm.calls[-1][1] is None  # the last call offers no tools


def test_empty_answer_falls_back(now):
    assert _assistant(ScriptedLLM(Reply(content="")), now).answer("?") == NO_ANSWER
