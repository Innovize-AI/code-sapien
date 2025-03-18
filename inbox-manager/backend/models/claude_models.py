import requests
import json
import os
from langchain_core.messages.human import HumanMessage
from langchain_anthropic import ChatAnthropic

def get_claude_ai(temperature=0, model='gpt-3.5-turbo'):

    llm = ChatAnthropic(
    model=model,
    temperature = temperature,
)
    return llm

def get_claude_ai_json(temperature=0, model='gpt-3.5-turbo'):
    llm = ChatAnthropic(
    model=model,
    temperature = temperature,
    model_kwargs={"response_format": {"type": "json_object"}},
)
    return llm