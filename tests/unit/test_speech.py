from datetime import timedelta

from assistant import speech
from assistant.integrations import moodle


def test_event_list(sample_events, now):
    events = moodle.events_between(sample_events, now, now + timedelta(days=3))
    assert speech.event_list(events, now, "nos próximos 3 dias") == (
        "Nos próximos 3 dias tens 2 eventos: "
        "Entrega Sprint 1, de LAPR3, amanhã às 23:59; "
        "e Teste de ESINF, de ESINF, sexta-feira às 10:00."
    )


def test_event_list_empty(now):
    assert speech.event_list([], now, "hoje") == "Não tens nada no Moodle hoje."


def test_event_list_truncates_long_lists(sample_events, now):
    many = sample_events[:1] * (speech.MAX_EVENTS_SPOKEN + 2)
    assert speech.event_list(many, now, "hoje").endswith("E mais 2, que podes ver no Moodle.")


def test_far_away_event_uses_full_date(sample_events, now):
    assert speech.describe_event(sample_events[-1], now) == "Exame de época normal, dia 15 de janeiro às 00:00"


def test_next_event(sample_events, now):
    assert speech.next_event(sample_events[0], now) == "O próximo é Entrega Sprint 1, de LAPR3, amanhã às 23:59."
    assert speech.next_event(None, now).startswith("Não encontrei")
