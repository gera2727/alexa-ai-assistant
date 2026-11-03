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
        {
            "name": "Skills Assignment",
            "modules": [
                {"name": "Delivery Sprint 1 Intermediate Report", "modname": "label", "instance": 7},
                {"name": "1DE - 1DF", "modname": "assign", "instance": 5867},
            ],
        },
    ],
    "core_calendar_get_calendar_events": {
        "events": [
            {
                "name": "Teste ",
                "timestart": 1794045600,
                "courseid": 1,
                "modulename": "quiz",
                "description": "<p>Matéria:&nbsp;<b>capítulos 1-3</b></p>",
            },
            {"name": "Pessoal", "timestart": 1793836740, "courseid": 0},
            {
                "name": "Termina o prazo de '1DE - 1DF'",
                "timestart": 1793836800,
                "courseid": 2,
                "modulename": "assign",
                "instance": 5867,
            },
            {"name": "Fora do intervalo", "timestart": 1893456000, "courseid": 1},
        ]
    },
    "mod_assign_get_assignments": {
        "courses": [
            {
                "id": 2,
                "assignments": [
                    {"id": 5867, "name": "Sprint 1", "duedate": 1793836740},
                    {"id": 9, "name": "Sem data", "duedate": 0, "intro": "<p>Ler o enunciado</p>"},
                ],
            }
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
    assert [(s.name, s.items) for s in sections][0] == ("Aulas teóricas", ("Slides T1",))
    assert "Secção escondida" not in [s.name for s in sections]


def test_assignments_send_lists_and_convert_due_dates(api, calls):
    assignments = api.assignments([1, 2])
    assert calls[0][1]["courseids[0]"] == "1" and calls[0][1]["courseids[1]"] == "2"
    assert assignments[0].due == datetime(2026, 11, 4, 23, 59, tzinfo=TIMEZONE)
    assert assignments[1].due is None
    assert assignments[0].details == "Skills Assignment — Delivery Sprint 1 Intermediate Report"
    assert assignments[1].details == "Ler o enunciado"


def test_calendar_events_send_nested_params_and_sort(api, calls):
    start = datetime(2026, 11, 3, tzinfo=TIMEZONE)
    events = api.calendar_events(start, datetime(2026, 11, 10, tzinfo=TIMEZONE))
    params = next(p for _, p in calls if p["wsfunction"] == "core_calendar_get_calendar_events")
    assert params["events[courseids][0]"] == "1" and params["events[courseids][1]"] == "2"
    assert params["options[timestart]"] == str(int(start.timestamp()))
    assert [(e.title, e.course_id) for e in events] == [
        ("Pessoal", None),
        ("Termina o prazo de '1DE - 1DF'", 2),
        ("Teste", 1),
    ]
    assert (events[0].kind, events[0].details) == ("", "")
    assert (events[2].kind, events[2].details) == ("quiz", "Matéria: capítulos 1-3")


def test_activity_without_description_says_where_it_is(api):
    events = api.calendar_events(datetime(2026, 11, 3, tzinfo=TIMEZONE), datetime(2026, 11, 10, tzinfo=TIMEZONE))
    assert events[1].details == "Skills Assignment — Delivery Sprint 1 Intermediate Report"


def test_long_descriptions_are_shortened():
    from assistant.integrations.moodle_api import MAX_DETAILS_CHARS, _plain_text

    text = _plain_text("<div>" + "palavra " * 200 + "</div>")
    assert len(text) == MAX_DETAILS_CHARS and text.endswith("…")


def test_moodle_exceptions_raise():
    api = MoodleApi("https://m.example", "bad", transport=lambda *_: {"exception": "x", "errorcode": "invalidtoken"})
    with pytest.raises(MoodleError, match="invalidtoken"):
        api.courses()


def test_rejects_non_https():
    with pytest.raises(ValueError, match="https"):
        MoodleApi("http://m.example", "tok").call("core_webservice_get_site_info")
