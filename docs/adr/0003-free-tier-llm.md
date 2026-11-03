# 0003. Use a free-tier LLM behind a provider interface

**Status:** Accepted · **Date:** 2026-11-03

## Context

Phase 2 adds open-ended questions answered by an LLM. Requirements:

- **Zero cost.** Paid APIs (e.g. Anthropic, OpenAI) are out for now.
- **Low latency.** Alexa gives the whole request about 8 seconds.

Options considered:

| Option | Cost | Latency | Notes |
|---|---|---|---|
| Groq (open models) | Free tier | Very low | Chosen |
| Google Gemini Flash | Free tier | Low | Free-tier data may be used for training |
| Local model (Ollama) | Free | Depends on PC | PC must be on and exposed to the internet |
| Claude / GPT APIs | Paid | Low | Best quality, revisit later |

## Decision

Start with **Groq**. Hide the provider behind one module (`integrations/llm.py`, `GroqClient.chat`)
using the OpenAI-compatible chat API, so switching provider is a one-file change.

## Consequences

- ✅ No cost, fast answers.
- ❌ Free-tier rate limits and terms can change. The handler must degrade gracefully.
