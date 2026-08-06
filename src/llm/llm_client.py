import os
import json
import logging
from pathlib import Path

from openai import OpenAI

from src.core import timezone
from src.services.user_service import get_user_instructions
from src.services.message_service import get_history

OPENAI_API_KEY = os.getenv("AI_TOKEN")
AI_URL = os.getenv("AI_URL")
AI_MODEL = os.getenv("AI_MODEL")

logger = logging.getLogger(__name__)

LLM_DIR = Path(__file__).resolve().parent

client = OpenAI(base_url=AI_URL, api_key=OPENAI_API_KEY)

with open(LLM_DIR / "tools.json", mode='r') as file:
    schema = json.load(file)

with open(LLM_DIR / "instructions.md", mode='r') as file:
    GENERAL_INSTRUCTIONS_TEMPLATE = ''.join(file.readlines())

def _general_instructions(user):
    return GENERAL_INSTRUCTIONS_TEMPLATE.format(
        get_user_instructions(user.id),
        user.first_name,
        timezone.jhuman_readable(timezone.jnow()),
        timezone.jnow_to_str()
    )

def _create_general_talk_prompt(user, limit=10):
    general_instructions = _general_instructions(user)
    messages = get_history(user.id, limit=limit)
    messages.insert(0, {
        "role": "system",
        "content": general_instructions
    })
    return messages

def get_response_from_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return client.chat.completions.create(
        model=AI_MODEL,
        messages=messages,
        tools=schema,
        tool_choice="auto"
    )


def get_final_response_from_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return client.chat.completions.create(
        model=AI_MODEL,
        messages=messages
    )

def get_help_response_from_model(user):
    general_instructions = _general_instructions(user)
    messages = [
        {"role": "system", "content": general_instructions},
        {"role": "user", "content": "راهنمای نحوه کار با بازو"},
    ]

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=messages
    )
    return response.choices[0].message.content
