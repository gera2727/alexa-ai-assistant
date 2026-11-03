# Setup

## Prerequisites

- An [Amazon Developer](https://developer.amazon.com/) account (free).
- A [Groq](https://console.groq.com/) account and API key (free tier).
- Python 3.10+ for local development.
- A Moodle account whose site allows the mobile app (most universities do).

## 1. Create `lambda/config.json`

Copy `lambda/config.example.json` to `lambda/config.json`. This file is git-ignored.

| Key | How to get it |
|---|---|
| `moodle_url` | Your Moodle address, e.g. `https://moodle.example.edu`. |
| `moodle_token` | Run `python3 scripts/get_moodle_token.py` (same username and password as the Moodle app). It saves the token for you. |
| `groq_api_key` | Groq console → **API Keys → Create API Key**. |
| `groq_model` | Optional. Defaults to `openai/gpt-oss-120b`. |

Check that Moodle answers:

```bash
python3 scripts/check_moodle_api.py
```

> ⚠️ All of these values are personal credentials. Never commit them, paste them in an issue,
> or include them in logs.

## 2. Create the skill (Alexa-hosted)

1. In the [Alexa developer console](https://developer.amazon.com/alexa/console/ask), create a skill:
   - **Locale:** Portuguese (BR)
   - **Model:** Custom
   - **Hosting:** Alexa-hosted (Python)
   - **Template:** Start from scratch
2. **Build → Interaction Model → JSON Editor:** paste
   `skill-package/interactionModels/custom/pt-BR.json`, then **Save** and **Build skill**.
3. **Code tab:** replace the contents of `lambda/` with this repository's `lambda/` folder,
   including your `config.json`.
4. **Deploy.**

If you use your own AWS Lambda instead, set the environment variables
`MOODLE_URL`, `MOODLE_TOKEN` and `GROQ_API_KEY` rather than creating `config.json`.

## 3. Test

In the console's **Test** tab, enable *Development* and type:

```
abre o meu painel
o que tenho amanhã
quando é o próximo teste
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest                         # unit + end-to-end tests (no network)
ruff check . && ruff format .  # lint and format
```
