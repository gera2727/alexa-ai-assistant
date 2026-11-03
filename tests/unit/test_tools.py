from datetime import datetime

import pytest

from assistant.integrations.moodle_api import TIMEZONE, Assignment, Course, Event, Section
from assistant.tools import ToolError, build_toolbox, find_course

COURSES = [
    Course(1, "ARQCP(85515)", "Arquitetura de Computadores"),
    Course(2, "LAPR3(85519)", "Laboratório/Projeto III"),
    Course(3, "LAPR4(85521)", "Laboratório/Projeto IV"),
]


class FakeMoodle:
    def courses(self):
        return COURSES

    def calendar_events(self, start, end):
        self.asked_range = (start, end)
        events = [
            Event(
                "Entrega Sprint 1",
                datetime(2026, 11, 4, 23, 59, tzinfo=TIMEZONE),
                2,
                kind="assign",
                details="Relatório do Sprint 1",
            ),
            Event("Teste de ARQCP", datetime(2026, 11, 6, 10, 0, tzinfo=TIMEZONE), 1),
            Event("Lembrete pessoal", datetime(2026, 11, 6, 18, 0, tzinfo=TIMEZONE), None),
        ]
        return [e for e in events if start <= e.start < end]

    def course_contents(self, course_id):
        return [Section("Teóricas", ("Slides T1", "Slides T2")), Section("Vazia", ())]

    def assignments(self, course_ids):
        self.asked = course_ids
        return [
            Assignment(2, "Relatório", datetime(2026, 11, 9, 12, 0, tzinfo=TIMEZONE)),
            Assignment(2, "Sprint 0", datetime(2026, 10, 1, 12, 0, tzinfo=TIMEZONE)),  # past
            Assignment(2, "Sem data", None),
            Assignment(1, "Ficha 3", datetime(2026, 11, 4, 23, 59, tzinfo=TIMEZONE)),
        ]


@pytest.fixture
def moodle():
    return FakeMoodle()


@pytest.fixture
def tools(moodle, now):
    return build_toolbox(moodle, lambda: now)


@pytest.mark.parametrize(
    ("query", "expected"),
    [("ARQCP", 1), ("arqcp", 1), ("lapr3", 2), ("computadores", 1), ("Laboratório/Projeto IV", 3)],
)
def test_find_course(query, expected):
    assert find_course(COURSES, query).id == expected


def test_find_course_lists_options_when_ambiguous():
    with pytest.raises(ToolError, match="Known courses: ARQCP"):
        find_course(COURSES, "lapr")


def test_schemas_are_openai_functions(tools):
    names = [s["function"]["name"] for s in tools.schemas]
    assert names == ["get_calendar_events", "list_courses", "get_course_materials", "get_assignments"]
    assert all(s["type"] == "function" for s in tools.schemas)


def test_calendar_events_end_date_is_inclusive(tools, moodle):
    events = tools.run("get_calendar_events", {"start_date": "2026-11-04", "end_date": "2026-11-06"})
    assert [(e["title"], e["course"], e["weekday"], e["time"]) for e in events] == [
        ("Entrega Sprint 1", "LAPR3(85519)", "quarta-feira", "23:59"),
        ("Teste de ARQCP", "ARQCP(85515)", "sexta-feira", "10:00"),
        ("Lembrete pessoal", None, "sexta-feira", "18:00"),
    ]
    assert (events[0]["activity"], events[0]["details"]) == ("entrega de trabalho", "Relatório do Sprint 1")
    assert "activity" not in events[1] and "details" not in events[1]
    start, end = moodle.asked_range
    assert (start.isoformat(), end.isoformat()) == ("2026-11-04T00:00:00+00:00", "2026-11-07T00:00:00+00:00")


def test_course_materials_skip_empty_sections(tools):
    result = tools.run("get_course_materials", {"course": "arqcp"})
    assert result == {
        "course": "Arquitetura de Computadores",
        "sections": [{"section": "Teóricas", "items": ["Slides T1", "Slides T2"]}],
    }


def test_assignments_only_upcoming_and_sorted(tools, moodle):
    result = tools.run("get_assignments", {})
    assert [(a["course"], a["name"]) for a in result] == [("ARQCP(85515)", "Ficha 3"), ("LAPR3(85519)", "Relatório")]
    assert moodle.asked == [1, 2, 3]
    tools.run("get_assignments", {"course": "LAPR3"})
    assert moodle.asked == [2]


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        ("nope", {}, "Unknown tool"),
        ("get_calendar_events", {"start_date": "amanhã", "end_date": "2026-11-06"}, "YYYY-MM-DD"),
        ("get_calendar_events", {"start": "2026-11-04"}, "argument"),
        ("get_course_materials", {"course": "xyz"}, "No single course"),
    ],
)
def test_bad_calls_return_errors_for_the_model(tools, name, arguments, message):
    assert message in tools.run(name, arguments)["error"]
