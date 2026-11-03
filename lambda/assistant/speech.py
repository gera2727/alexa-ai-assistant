"""Turns calendar data into natural (European) Portuguese sentences."""

# TODO(v0.2): remove. The LLM writes the spoken answer from the tool results.

from __future__ import annotations

from datetime import datetime, timedelta

from assistant.dates import DateRange
from assistant.integrations.moodle import Event

WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MONTHS = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

MAX_EVENTS_SPOKEN = 5


def spoken_date(moment: datetime) -> str:
    return f"{moment.day} de {MONTHS[moment.month - 1]}"


def _when(event: Event, now: datetime) -> str:
    days_ahead = (event.start.date() - now.date()).days
    if days_ahead == 0:
        day = "hoje"
    elif days_ahead == 1:
        day = "amanhã"
    elif 1 < days_ahead < 7:
        day = WEEKDAYS[event.start.weekday()]
    else:
        day = f"dia {spoken_date(event.start)}"
    return f"{day} às {event.start:%H:%M}"


def describe_event(event: Event, now: datetime) -> str:
    course = f", de {event.course}" if event.course else ""
    return f"{event.title}{course}, {_when(event, now)}"


def describe_range(date_range: DateRange, now: datetime) -> str:
    if date_range.is_week:
        return f"na semana de {spoken_date(date_range.start)}"
    if date_range.start.date() == now.date():
        return "hoje"
    if date_range.start.date() == now.date() + timedelta(days=1):
        return "amanhã"
    return f"no dia {spoken_date(date_range.start)}"


def event_list(events: list[Event], now: datetime, period: str) -> str:
    """E.g. 'Amanhã tens 1 evento: Entrega Sprint 1, de LAPR3, amanhã às 23:59.'"""
    if not events:
        return f"Não tens nada no Moodle {period}."
    parts = [describe_event(event, now) for event in events[:MAX_EVENTS_SPOKEN]]
    body = parts[0] if len(parts) == 1 else "; ".join(parts[:-1]) + "; e " + parts[-1]
    noun = "evento" if len(events) == 1 else "eventos"
    sentence = f"{period[0].upper()}{period[1:]} tens {len(events)} {noun}: {body}."
    if len(events) > MAX_EVENTS_SPOKEN:
        sentence += f" E mais {len(events) - MAX_EVENTS_SPOKEN}, que podes ver no Moodle."
    return sentence


def next_event(event: Event | None, now: datetime) -> str:
    if event is None:
        return "Não encontrei eventos futuros no teu calendário do Moodle."
    return f"O próximo é {describe_event(event, now)}."
