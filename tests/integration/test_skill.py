"""End-to-end tests: a raw Alexa request envelope in, a spoken response out. No network."""

import pytest

from assistant import config
from assistant.skill import build_skill


def _envelope(request_type, intent=None, slots=None):
    request = {"type": request_type, "requestId": "req-1", "locale": "pt-BR", "timestamp": "2026-11-03T14:00:00Z"}
    if intent:
        request["intent"] = {"name": intent, "confirmationStatus": "NONE", "slots": slots or {}}
    ids = {"application": {"applicationId": "app-1"}, "user": {"userId": "user-1"}}
    return {
        "version": "1.0",
        "session": {"new": True, "sessionId": "session-1", **ids},
        "context": {"System": {**ids, "apiEndpoint": "https://api.amazonalexa.com"}},
        "request": request,
    }


def _date_slot(value):
    return {"date": {"name": "date", "value": value, "confirmationStatus": "NONE"}}


@pytest.fixture
def invoke(sample_events, now):
    handler = build_skill(events=lambda: sample_events, clock=lambda: now).lambda_handler()

    def _invoke(*args, **kwargs):
        response = handler(_envelope(*args, **kwargs), None)["response"]
        return response["outputSpeech"]["ssml"], response.get("shouldEndSession")

    return _invoke


def test_launch_keeps_session_open(invoke):
    speech, ends = invoke("LaunchRequest")
    assert "Olá" in speech
    assert not ends


def test_upcoming_events(invoke):
    speech, ends = invoke("IntentRequest", "UpcomingEventsIntent")
    assert "Nos próximos 7 dias tens 3 eventos" in speech
    assert ends


def test_events_this_week(invoke):
    speech, _ = invoke("IntentRequest", "EventsByDateIntent", _date_slot("2026-W45"))
    assert "Na semana de 2 de novembro tens 2 eventos" in speech


def test_events_tomorrow(invoke):
    speech, _ = invoke("IntentRequest", "EventsByDateIntent", _date_slot("2026-11-04"))
    assert "Amanhã tens 1 evento: Entrega Sprint 1" in speech


def test_unsupported_date_asks_again(invoke):
    speech, ends = invoke("IntentRequest", "EventsByDateIntent", _date_slot("2026-11"))
    assert "só percebo dias ou semanas" in speech
    assert not ends


def test_next_event(invoke):
    speech, _ = invoke("IntentRequest", "NextEventIntent")
    assert "O próximo é Entrega Sprint 1" in speech


def test_network_failure_is_spoken_not_raised(now):
    def broken():
        raise OSError("network down")

    handler = build_skill(events=broken, clock=lambda: now).lambda_handler()
    response = handler(_envelope("IntentRequest", "NextEventIntent"), None)
    assert "Não consegui ler" in response["response"]["outputSpeech"]["ssml"]


def test_missing_config_is_spoken_not_raised(monkeypatch):
    monkeypatch.delenv("MOODLE_ICAL_URL", raising=False)
    monkeypatch.setattr(config, "_file_settings", dict)  # ignore a developer's local config.json
    handler = build_skill().lambda_handler()
    response = handler(_envelope("IntentRequest", "NextEventIntent"), None)
    assert "Não consegui ler" in response["response"]["outputSpeech"]["ssml"]
