"""Tools the LLM can call to read the student's data.

Each tool is a plain function that returns JSON-serialisable data. The schemas
follow the OpenAI/Groq "function" format. All tools are read-only.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from assistant.integrations.moodle_api import TIMEZONE, Course, MoodleApi

Clock = Callable[[], datetime]

MAX_EVENTS = 25
MAX_ITEMS_PER_SECTION = 15
# Moodle module names -> words the LLM can say in Portuguese.
ACTIVITY_NAMES = {"assign": "entrega de trabalho", "quiz": "teste/quiz", "forum": "fórum", "lesson": "lição"}
WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


class ToolError(ValueError):
    """Bad arguments from the model. The message is sent back so it can correct itself."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    run: Callable[..., Any]

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


class ToolBox:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema for tool in self._tools.values()]

    def run(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"Unknown tool {name!r}."}
        try:
            return tool.run(**arguments)
        except (ToolError, TypeError) as error:
            return {"error": str(error)}


def _normalise(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(without_accents.casefold().split())


def find_course(courses: list[Course], query: str) -> Course:
    """Match "arqcp", "ARQCP(85515)" or part of the full name."""
    wanted = _normalise(query)
    for matches in (
        lambda c: _normalise(c.shortname).split("(")[0].strip() == wanted,
        lambda c: wanted in _normalise(c.shortname),
        lambda c: wanted in _normalise(c.fullname),
    ):
        found = [course for course in courses if matches(course)]
        if len(found) == 1:
            return found[0]
    known = ", ".join(course.shortname for course in courses)
    raise ToolError(f"No single course matches {query!r}. Known courses: {known}.")


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ToolError(f"Dates must be YYYY-MM-DD, got {value!r}.") from error


def _describe(moment: datetime) -> dict[str, str]:
    return {"date": moment.date().isoformat(), "weekday": WEEKDAYS[moment.weekday()], "time": moment.strftime("%H:%M")}


def build_toolbox(moodle: MoodleApi, clock: Clock) -> ToolBox:
    def course_names() -> dict[int, str]:
        return {c.id: c.shortname for c in moodle.courses()}

    def get_calendar_events(start_date: str, end_date: str) -> list[dict[str, Any]]:
        first, last = _parse_day(start_date), _parse_day(end_date)
        start = datetime(first.year, first.month, first.day, tzinfo=TIMEZONE)
        end = datetime(last.year, last.month, last.day, tzinfo=TIMEZONE) + timedelta(days=1)
        names = course_names()
        found = moodle.calendar_events(start, end)[:MAX_EVENTS]
        return [
            {
                "title": e.title,
                "course": names.get(e.course_id),
                **({"activity": ACTIVITY_NAMES.get(e.kind, e.kind)} if e.kind else {}),
                **({"details": e.details} if e.details else {}),
                **_describe(e.start),
            }
            for e in found
        ]

    def list_courses() -> list[dict[str, str]]:
        return [{"shortname": c.shortname, "fullname": c.fullname} for c in moodle.courses()]

    def get_course_materials(course: str) -> dict[str, Any]:
        match = find_course(moodle.courses(), course)
        sections = [
            {"section": s.name, "items": list(s.items[:MAX_ITEMS_PER_SECTION])}
            for s in moodle.course_contents(match.id)
            if s.items
        ]
        return {"course": match.fullname, "sections": sections}

    def get_assignments(course: str | None = None) -> list[dict[str, Any]]:
        courses = moodle.courses()
        selected = [find_course(courses, course)] if course else courses
        names = course_names()
        now = clock()
        pending = sorted(
            (a for a in moodle.assignments([c.id for c in selected]) if a.due and a.due >= now),
            key=lambda a: a.due,
        )
        return [{"course": names.get(a.course_id), "name": a.name, **_describe(a.due)} for a in pending]

    return ToolBox(
        [
            Tool(
                "get_calendar_events",
                "Moodle calendar events (tests, exams, deadlines, course events) between two dates, inclusive. "
                "'activity' and 'details' say what an event is about (e.g. which work is due).",
                {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "First day, YYYY-MM-DD."},
                        "end_date": {"type": "string", "description": "Last day, YYYY-MM-DD."},
                    },
                    "required": ["start_date", "end_date"],
                },
                get_calendar_events,
            ),
            Tool(
                "list_courses",
                "Courses (unidades curriculares) the student is enrolled in, with short and full names.",
                {"type": "object", "properties": {}},
                list_courses,
            ),
            Tool(
                "get_course_materials",
                "Sections and materials (files, links, activities) posted in one course.",
                {
                    "type": "object",
                    "properties": {"course": {"type": "string", "description": "Course short name, e.g. ARQCP."}},
                    "required": ["course"],
                },
                get_course_materials,
            ),
            Tool(
                "get_assignments",
                "Upcoming assignment deadlines, optionally for one course.",
                {
                    "type": "object",
                    "properties": {"course": {"type": "string", "description": "Optional course short name."}},
                },
                get_assignments,
            ),
        ]
    )
