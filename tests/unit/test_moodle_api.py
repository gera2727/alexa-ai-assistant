import urllib.parse
from datetime import datetime

import pytest

from assistant.integrations.moodle_api import TIMEZONE, MoodleApi, MoodleError

RESPONSES = {
    "core_webservice_get_site_info": {"userid": 42},
    "core_enrol_get_users_courses": [
        {"id": 1, "shortname": "ARQCP(85515)", "fullname": "Arquitetura de Computadores"},
        {"id": 2, "shortname": "LAPR3(85519)", "fullname": "Laboratório/Projeto III"},
    ],
    "core_course_get_contents": [
        {"name": "Aulas teóricas", "modules": [{"name": "Slides T1"}, {"name": "Oculto", "uservisible": False}]},
        {"name": "Secção escondida", "uservisible": False, "modules": [{"name": "x"}]},
    ],
    "core_calendar_get_calendar_events": {
        "events": [
            {"name": "Teste ", "timestart": 1794045600, "courseid": 1},
            {"name": "Pessoal", "timestart": 1793836740, "courseid": 0},
            {"name": "Fora do intervalo", "timestart": 1893456000, "courseid": 1},
        ]
    },
    "mod_assign_get_assignments": {
        "courses": [
            {"id": 2, "assignments": [{"name": "Sprint 1", "duedate": 1793836740}, {"name": "Sem data", "duedate": 0}]}
        ]
    },
}


@pytest.fixture
def calls():
    return []


@pytest.fixture
def api(calls):
    def transport(url, body, timeout):
        params = dict(urllib.parse.parse_qsl(body.decode()))
        calls.append((url, params))
        return RESPONSES[params["wsfunction"]]

    return MoodleApi("https://moodle.example/", "tok", transport=transport)


def test_token_goes_in_the_body_not_the_url(api, calls):
    api.call("core_webservice_get_site_info")
    url, params = calls[0]
    assert url == "https://moodle.example/webservice/rest/server.php"
    assert params["wstoken"] == "tok"
    assert params["moodlewsrestformat"] == "json"


def test_courses_are_cached(api, calls):
    assert [c.shortname for c in api.courses()] == ["ARQCP(85515)", "LAPR3(85519)"]
    api.courses()
    assert [p["wsfunction"] for _, p in calls] == ["core_webservice_get_site_info", "core_enrol_get_users_courses"]
    assert calls[1][1]["userid"] == "42"


def test_course_contents_hide_invisible_items(api):
    sections = api.course_contents(1)
    assert [(s.name, s.items) for s in sections] == [("Aulas teóricas", ("Slides T1",))]


def test_assignments_send_lists_and_convert_due_dates(api, calls):
    assignments = api.assignments([1, 2])
    assert calls[0][1]["courseids[0]"] == "1" and calls[0][1]["courseids[1]"] == "2"
    assert assignments[0].due == datetime(2026, 11, 4, 23, 59, tzinfo=TIMEZONE)
    assert assignments[1].due is None


def test_calendar_events_send_nested_params_and_sort(api, calls):
    start = datetime(2026, 11, 3, tzinfo=TIMEZONE)
    events = api.calendar_events(start, datetime(2026, 11, 10, tzinfo=TIMEZONE))
    params = calls[-1][1]
    assert params["events[courseids][0]"] == "1" and params["events[courseids][1]"] == "2"
    assert params["options[timestart]"] == str(int(start.timestamp()))
    assert [(e.title, e.course_id) for e in events] == [("Pessoal", None), ("Teste", 1)]


def test_moodle_exceptions_raise():
    api = MoodleApi("https://m.example", "bad", transport=lambda *_: {"exception": "x", "errorcode": "invalidtoken"})
    with pytest.raises(MoodleError, match="invalidtoken"):
        api.courses()


def test_rejects_non_https():
    with pytest.raises(ValueError, match="https"):
        MoodleApi("http://m.example", "tok").call("core_webservice_get_site_info")
