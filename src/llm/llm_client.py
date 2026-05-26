import os
import logging
from openai import OpenAI
import json
from src.services.user_service import get_user_instructions
from src.services.message_service import get_history
from src.commons import timezone

GAPGPT_AI_URL = os.getenv("GAPGPT_AI_URL")
GAPGPT_MODEL = os.getenv("GAPGPT_MODEL")
GAPGPT_AI_TOKEN = os.getenv("GAPGPT_AI_TOKEN")

ARVAN_AI_URL = os.getenv("ARVAN_AI_URL")
ARVAN_MODEL = os.getenv("ARVAN_MODEL")
ARVAN_SUB_MODEL = os.getenv("ARVAN_SUB_MODEL")
ARVAN_AI_TOKEN = os.getenv("ARVAN_AI_TOKEN")

logger = logging.getLogger(__name__)

gapgpt_client = OpenAI(base_url=GAPGPT_AI_URL, api_key=GAPGPT_AI_TOKEN)
arvan_client = OpenAI(base_url=ARVAN_AI_URL, api_key=ARVAN_AI_TOKEN)

current_dir = os.path.dirname(os.path.abspath(__file__))

json_file_path = os.path.join(current_dir, 'tools.json')
with open(json_file_path, mode='r') as file:
    schema = json.load(file)

md_file_path = os.path.join(current_dir, 'instructions.md')
with open(md_file_path, mode='r') as file:
    GENERAL_INSTRUCTIONS_TEMPLATE = ''.join(file.readlines())

def _general_instructions(user):
    return GENERAL_INSTRUCTIONS_TEMPLATE.format(
        get_user_instructions(user.id),
        timezone.jhuman_readable(timezone.jnow()),
    )

def _create_general_talk_prompt(user, limit=10):
    general_instructions = _general_instructions(user)
    messages = get_history(user.id, limit=limit)
    messages.insert(0, {
        "role": "system",
        "content": general_instructions
    })
    return messages

def get_response_from_main_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return gapgpt_client.chat.completions.create(
        model=GAPGPT_MODEL,
        messages=messages,
        tools=schema,
        tool_choice="auto"
    )

def get_final_response_from_main_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return gapgpt_client.chat.completions.create(
        model=GAPGPT_MODEL,
        messages=messages
    )

def get_response_from_sub_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return arvan_client.chat.completions.create(
        model=ARVAN_MODEL,
        messages=messages,
        tools=schema,
        tool_choice="auto"
    )

def get_final_response_from_sub_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return arvan_client.chat.completions.create(
        model=ARVAN_MODEL,
        messages=messages
    )