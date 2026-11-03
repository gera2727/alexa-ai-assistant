"""Moodle Web Services client (REST, read-only).

Uses the personal token of the ``moodle_mobile_app`` service, the same one the
official Moodle app uses. See ``scripts/get_moodle_token.py``.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Europe/Lisbon")
DEFAULT_TIMEOUT_S = 3.0

# (url, form-encoded body, timeout) -> decoded JSON. Injected in tests.
Transport = Callable[[str, bytes, float], Any]


class MoodleError(RuntimeError):
    """Moodle answered with an exception (bad token, missing permission...)."""


@dataclass(frozen=True)
class Course:
    id: int
    shortname: str
    fullname: str


@dataclass(frozen=True)
class Section:
    name: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class Event:
    title: str
    start: datetime  # timezone-aware, in TIMEZONE
    course_id: int | None  # None for personal and site events
    kind: str = ""  # activity type, e.g. "assign" or "quiz"; empty for plain calendar entries
    details: str = ""  # the event description as plain text, shortened


@dataclass(frozen=True)
class Assignment:
    course_id: int
    name: str
    due: datetime | None  # None when the assignment has no due date
    details: str = ""  # the assignment's instructions, or where it sits on the course page


def _post_json(url: str, body: bytes, timeout: float) -> Any:
    if not url.startswith("https://"):
        raise ValueError("The Moodle URL must use https://")
    request = urllib.request.Request(url, data=body, headers={"User-Agent": "alexa-ai-assistant"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (scheme checked above)
        return json.load(response)


def _flatten(params: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Moodle expects nested values as ``events[courseids][0]=1&options[timestart]=...``."""
    flat: dict[str, Any] = {}
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, (list, tuple)):
            value = dict(enumerate(value))
        if isinstance(value, dict):
            flat.update(_flatten(value, name))
        else:
            flat[name] = value
    return flat


MAX_DETAILS_CHARS = 300
_TAG = re.compile(r"<[^>]+>")


def _plain_text(markup: str | None) -> str:
    """Moodle descriptions are HTML. Keep only the words, shortened for the LLM."""
    text = " ".join(html.unescape(_TAG.sub(" ", markup or "")).split())
    return text if len(text) <= MAX_DETAILS_CHARS else text[: MAX_DETAILS_CHARS - 1].rstrip() + "…"


def _timestamp(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value, TIMEZONE) if value else None


class MoodleApi:
    def __init__(
        self, base_url: str, token: str, timeout: float = DEFAULT_TIMEOUT_S, transport: Transport = _post_json
    ) -> None:
        self._endpoint = f"{base_url.rstrip('/')}/webservice/rest/server.php"
        self._token = token
        self._timeout = timeout
        self._transport = transport
        self._courses: list[Course] | None = None
        self._where: dict[int, dict[tuple[str, int], str]] = {}

    def call(self, function: str, **params: Any) -> Any:
        # The token goes in the POST body, so it never ends up in server or proxy logs.
        body = {"wstoken": self._token, "wsfunction": function, "moodlewsrestformat": "json", **_flatten(params)}
        result = self._transport(self._endpoint, urllib.parse.urlencode(body).encode(), self._timeout)
        if isinstance(result, dict) and "exception" in result:
            raise MoodleError(f"{function}: {result.get('errorcode')}")
        return result

    def courses(self) -> list[Course]:
        """Courses the user is enrolled in. Cached: it rarely changes during a session."""
        if self._courses is None:
            user_id = self.call("core_webservice_get_site_info")["userid"]
            self._courses = [
                Course(id=c["id"], shortname=c["shortname"], fullname=c["fullname"])
                for c in self.call("core_enrol_get_users_courses", userid=user_id)
            ]
        return self._courses

    def course_contents(self, course_id: int) -> list[Section]:
        """Sections of a course with the names of the materials/activities the user can see."""
        return [
            Section(
                name=section.get("name", "").strip(),
                items=tuple(m["name"].strip() for m in section.get("modules", []) if m.get("uservisible", True)),
            )
            for section in self.call("core_course_get_contents", courseid=course_id)
            if section.get("uservisible", True)
        ]

    def calendar_events(self, start: datetime, end: datetime) -> list[Event]:
        """Course, group, personal and site events with ``start <= event.start < end``, sorted."""
        result = self.call(
            "core_calendar_get_calendar_events",
            events={"courseids": [course.id for course in self.courses()]},
            options={
                "userevents": 1,
                "siteevents": 1,
                "timestart": int(start.timestamp()),
                "timeend": int(end.timestamp()),
            },
        )
        enrolled = {course.id for course in self.courses()}
        events = [
            Event(
                title=event["name"].strip(),
                start=_timestamp(event["timestart"]),
                course_id=event.get("courseid") if event.get("courseid") in enrolled else None,
                kind=event.get("modulename") or "",
                details=_plain_text(event.get("description")) or self._where_is(event, enrolled),
            )
            for event in result.get("events", [])
            if start <= _timestamp(event["timestart"]) < end
        ]
        return sorted(events, key=lambda e: e.start)

    def _where_is(self, event: dict[str, Any], enrolled: set[int]) -> str:
        """For an activity without a description, say where it sits on the course page.

        Teachers often name activities after class groups ("1DE - 1DF") and put the real
        subject in the section title or in a heading just above (e.g. "Delivery Sprint 1").
        """
        course_id, kind, instance = event.get("courseid"), event.get("modulename"), event.get("instance")
        if course_id not in enrolled or not kind or not instance:
            return ""
        if course_id not in self._where:
            try:
                self._where[course_id] = self._activity_places(course_id)
            except MoodleError:
                self._where[course_id] = {}
        return self._where[course_id].get((kind, instance), "")

    def _activity_places(self, course_id: int) -> dict[tuple[str, int], str]:
        places: dict[tuple[str, int], str] = {}
        for section in self.call("core_course_get_contents", courseid=course_id):
            heading = ""
            for module in section.get("modules", []):
                if module.get("modname") == "label":
                    heading = _plain_text(module.get("name"))
                elif module.get("instance"):
                    parts = [_plain_text(section.get("name")), heading]
                    places[(module.get("modname", ""), module["instance"])] = " — ".join(p for p in parts if p)
        return places

    def assignments(self, course_ids: list[int]) -> list[Assignment]:
        result = self.call("mod_assign_get_assignments", courseids=course_ids)
        enrolled = {course.id for course in self.courses()}
        return [
            Assignment(
                course_id=course["id"],
                name=a["name"].strip(),
                due=_timestamp(a.get("duedate")),
                details=_plain_text(a.get("intro"))
                or self._where_is(
                    {"courseid": course["id"], "modulename": "assign", "instance": a.get("id")}, enrolled
                ),
            )
            for course in result.get("courses", [])
            for a in course.get("assignments", [])
        ]
