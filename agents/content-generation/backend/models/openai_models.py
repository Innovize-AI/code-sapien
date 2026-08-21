from langchain_openai import ChatOpenAI
import os


def get_open_ai(temperature=0, model='gpt-3.5-turbo'):

    llm = ChatOpenAI(
    model=model,
    temperature = temperature,
)
    return llm

def get_open_ai_json(temperature=0, model='gpt-3.5-turbo'):
    llm = ChatOpenAI(
    model=model,
    temperature = temperature,
    model_kwargs={"response_format": {"type": "json_object"}},
)
    return llm
