"""End-to-end tests: a raw Alexa request envelope in, a spoken response out. No network."""

import pytest

from assistant import config
from assistant.integrations.llm import LLMError
from assistant.skill import build_skill


def _envelope(request_type, intent=None, slots=None, new_session=True):
    request = {"type": request_type, "requestId": "req-1", "locale": "pt-BR", "timestamp": "2026-11-03T14:00:00Z"}
    if intent:
        request["intent"] = {"name": intent, "confirmationStatus": "NONE", "slots": slots or {}}
    ids = {"application": {"applicationId": "app-1"}, "user": {"userId": "user-1"}}
    return {
        "version": "1.0",
        "session": {"new": new_session, "sessionId": "session-1", **ids},
        "context": {"System": {**ids, "apiEndpoint": "https://api.amazonalexa.com"}},
        "request": request,
    }


def _question(text):
    return {"question": {"name": "question", "value": text, "confirmationStatus": "NONE"}}


class FakeAssistant:
    def __init__(self, reply="Amanhã tens a entrega do Sprint 1 às 23:59.", error=None):
        self.reply, self.error, self.questions = reply, error, []

    def answer(self, question):
        self.questions.append(question)
        if self.error:
            raise self.error
        return self.reply


def _run(assistant, *args, **kwargs):
    response = build_skill(assistant).lambda_handler()(_envelope(*args, **kwargs), None)["response"]
    return response["outputSpeech"]["ssml"], response.get("shouldEndSession")


def test_launch_keeps_session_open():
    speech, ends = _run(FakeAssistant(), "LaunchRequest")
    assert "Olá" in speech
    assert not ends


def test_one_shot_question_is_answered_and_ends():
    assistant = FakeAssistant()
    speech, ends = _run(assistant, "IntentRequest", "QuestionIntent", _question("o que tenho amanhã"))
    assert assistant.questions == ["o que tenho amanhã"]
    assert "entrega do Sprint 1" in speech
    assert ends


def test_question_inside_a_conversation_keeps_session_open():
    _, ends = _run(FakeAssistant(), "IntentRequest", "QuestionIntent", _question("e depois?"), new_session=False)
    assert not ends


def test_empty_question_asks_again():
    speech, ends = _run(FakeAssistant(), "IntentRequest", "QuestionIntent", {})
    assert "Podes repetir" in speech
    assert not ends


def test_rate_limit_is_explained():
    speech, _ = _run(
        FakeAssistant(error=LLMError("429", rate_limited=True)), "IntentRequest", "QuestionIntent", _question("x")
    )
    assert "muitos pedidos" in speech


def test_unexpected_failure_is_spoken_not_raised():
    speech, _ = _run(FakeAssistant(error=OSError("network down")), "IntentRequest", "QuestionIntent", _question("x"))
    assert "tive um problema" in speech


@pytest.mark.parametrize("name", ["MOODLE_URL", "MOODLE_TOKEN", "GROQ_API_KEY"])
def test_missing_config_is_spoken_not_raised(monkeypatch, name):
    monkeypatch.setattr(config, "_file_settings", dict)  # ignore a developer's local config.json
    for setting in ("MOODLE_URL", "MOODLE_TOKEN", "GROQ_API_KEY"):
        monkeypatch.setenv(setting, "https://example.test")
    monkeypatch.delenv(name)
    speech, _ = _run(None, "IntentRequest", "QuestionIntent", _question("o que tenho amanhã"))
    assert "tive um problema" in speech
