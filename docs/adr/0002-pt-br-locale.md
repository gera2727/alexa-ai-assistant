# 0002. Use the pt-BR locale with European Portuguese responses

**Status:** Accepted · **Date:** 2026-11-03

## Context

Alexa does not offer a Portuguese (Portugal) locale. The user speaks European Portuguese.

## Decision

Register the skill under **pt-BR**, but write every response in **European Portuguese**
("tens", "amanhã às 23:59").

## Consequences

- ✅ The skill works on Echo devices in Portugal.
- ❌ Speech recognition and the voice have a Brazilian accent.
- ❌ Some European expressions may be misrecognised. Sample utterances should include
  common variants.
