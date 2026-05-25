import os
from tenacity import retry, stop_after_delay, wait_fixed
import logging
from openai import OpenAI
import json
from services.user_service import get_user_instructions
from services.message_service import get_history
from src.commons import timezone
OPENAI_API_KEY = os.getenv("AI_TOKEN")
AI_URL = os.getenv("AI_URL")
MODEL = os.getenv("MODEL")
SUB_MODEL = os.getenv("SUB_MODEL")

logger = logging.getLogger(__name__)

client = OpenAI(base_url=AI_URL, api_key=OPENAI_API_KEY)

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

@retry(stop=stop_after_delay(3), wait=wait_fixed(3))
def get_response_from_main_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return client.responses.create(
        model=MODEL,
        input=messages,
        tools=schema,
        tool_choice="auto"
    )

@retry(stop=stop_after_delay(2), wait=wait_fixed(3))
def get_response_from_sub_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return client.responses.create(
        model=SUB_MODEL,
        input=messages,
        tools=schema,
        tool_choice="auto"
    )

@retry(stop=stop_after_delay(2), wait=wait_fixed(3))
def get_final_response_from_main_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return client.responses.create(
        model=MODEL,
        input=messages
    )

@retry(stop=stop_after_delay(3), wait=wait_fixed(3))
def get_final_response_from_sub_model(user, limit):
    messages = _create_general_talk_prompt(user, limit=limit)

    return client.responses.create(
        model=SUB_MODEL,
        input=messages
    )