# 0004. Answer free-form questions with one catch-all intent and LLM tool calling

**Status:** Accepted · **Date:** 2026-11-03

## Context

v0.1 had one intent per question type (upcoming events, events on a date, next event).
Every new kind of question needed a new intent, new sample utterances and a new handler.
In practice students ask about Moodle in many ways: "quando é o teste de ARQCP?",
"que materiais há em LAPR3?", "tenho entregas esta semana?".

Options considered:

| Option | Pros | Cons |
|---|---|---|
| More fixed intents and slots | Predictable, no LLM cost | Never covers how people actually speak |
| Catch-all intent, LLM with **all** data in the prompt | One LLM call | Prompt grows with every course and file; slow and hits token limits |
| Catch-all intent, LLM with **tool calling** | Fetches only what the question needs; new data source = new tool | Up to a few LLM round trips per answer |

## Decision

- A single `QuestionIntent` with a custom catch-all slot (`QUESTION_TEXT`) captures the whole utterance.
  `AMAZON.SearchQuery` was not used because it requires a carrier phrase in every sample.
- The question goes to an LLM (Groq, see [ADR 0003](0003-free-tier-llm.md)) together with a small set of
  **read-only tools**: calendar events, courses, course materials and assignment deadlines.
- The loop is capped at `MAX_TOOL_ROUNDS = 3`, with short HTTP timeouts, to stay within Alexa's ~8 s limit.
- Tool results are passed as data. The system prompt says so explicitly, to limit prompt injection from
  course content.

## Consequences

- ✅ New questions need no new intents: a new data source is a new tool in `tools.py`.
- ✅ Each layer (LLM client, Moodle client, tools, agent loop, Alexa handler) is tested on its own.
- ❌ Answers depend on the model following instructions. The prompt forbids inventing dates, rooms or grades.
- ❌ Latency is higher than v0.1. If it becomes a problem, add an Alexa progressive response or cache
  `list_courses` across requests (already cached per warm Lambda container).
