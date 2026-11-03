# 0001. Host the skill on Alexa-hosted Lambda

**Status:** Accepted · **Date:** 2026-11-03

## Context

The project must cost nothing and must not require a credit card. A custom skill
needs a backend: either an AWS Lambda in our own account, or an Alexa-hosted skill,
where Amazon provisions and pays for the Lambda.

## Decision

Use an **Alexa-hosted** skill (Python runtime).

## Consequences

- ✅ Free within Amazon's limits, which are far above personal use. No AWS account needed.
- ✅ Deploys from the developer console in one click.
- ❌ No environment variables, so secrets go in a git-ignored `config.json`.
- ❌ Less control (region, runtime version, IAM). Moving to our own Lambda later only
  requires setting `MOODLE_ICAL_URL` as an env var. The code already supports both.
