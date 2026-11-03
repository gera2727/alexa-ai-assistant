# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-03

### Added

- Free-form questions: a single catch-all `QuestionIntent` sends the whole question to an LLM ([ADR 0004](docs/adr/0004-free-form-questions.md)).
- Groq client with tool calling (OpenAI-compatible API, no extra dependencies).
- Moodle Web Services client: calendar events, enrolled courses, course materials and assignment deadlines.
- Read-only tools for the LLM: calendar events, courses, materials, assignments.
- Setup helpers: `scripts/get_moodle_token.py` and `scripts/check_moodle_api.py`.

### Changed

- **Breaking:** the fixed intents (`UpcomingEventsIntent`, `EventsByDateIntent`, `NextEventIntent`) were replaced by `QuestionIntent`. Re-import the interaction model.
- The calendar is read through Moodle Web Services with the same token, so the iCal URL setting is no longer needed.

### Removed

- `dates.py` and `speech.py`: the LLM now resolves dates and writes the answer.
- The iCal integration (`integrations/moodle.py`) and the `icalendar` dependency.

## [0.1.0] - 2026-11-03

### Added

- Moodle calendar integration: downloads and parses the personal iCal export.
- Intents: upcoming events (next 7 days), events on a day or week, next event.
- European Portuguese speech formatting ("amanhã às 23:59", "sexta-feira às 10:00").
- Unit and end-to-end tests with a sample `.ics`; CI with ruff and pytest.
