# Setup

## Prerequisites

- An [Amazon Developer](https://developer.amazon.com/) account (free).
- Python 3.10+ for local development.
- Your Moodle calendar export URL.

## 1. Get the Moodle calendar URL

1. In Moodle, open **Calendar → Import or export calendars → Export calendar**.
2. Choose **All events** and **Recent and next 60 days**, then **Get calendar URL**.
3. Copy the URL.

> ⚠️ The URL contains a personal `authtoken`. Anyone with it can read your calendar.
> Never commit it, paste it in an issue, or include it in logs.

## 2. Create the skill (Alexa-hosted)

1. In the [Alexa developer console](https://developer.amazon.com/alexa/console/ask), create a skill:
   - **Locale:** Portuguese (BR)
   - **Model:** Custom
   - **Hosting:** Alexa-hosted (Python)
   - **Template:** Start from scratch
2. **Build → Interaction Model → JSON Editor:** paste
   `skill-package/interactionModels/custom/pt-BR.json`, then **Save** and **Build skill**.
3. **Code tab:** replace the contents of `lambda/` with this repository's `lambda/` folder
   (`lambda_function.py`, `requirements.txt` and the `assistant/` package).
4. Create `lambda/config.json` from `lambda/config.example.json` and paste your URL.
5. **Deploy.**

If you use your own AWS Lambda instead, set the `MOODLE_ICAL_URL` environment variable
rather than creating `config.json`.

## 3. Test

In the console's **Test** tab, enable *Development* and type:

```
abre a agenda do isep
o que tenho esta semana
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest                         # unit + end-to-end tests
ruff check . && ruff format .  # lint and format
```
