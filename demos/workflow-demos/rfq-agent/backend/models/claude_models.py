import os
from langchain_anthropic import ChatAnthropic


def get_claude(temperature=0, model=None):
    return ChatAnthropic(
        model=model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
        temperature=temperature,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
