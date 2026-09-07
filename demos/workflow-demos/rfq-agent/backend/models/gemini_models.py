import os
from langchain_google_genai import ChatGoogleGenerativeAI


def get_gemini(temperature=0, model=None):
    return ChatGoogleGenerativeAI(
        model=model or os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
        temperature=temperature,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )
