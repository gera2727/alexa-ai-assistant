"""AWS Lambda entry point (the file name is required by Alexa-hosted skills)."""

import logging

from assistant.skill import build_skill

logging.getLogger().setLevel(logging.INFO)

lambda_handler = build_skill().lambda_handler()
