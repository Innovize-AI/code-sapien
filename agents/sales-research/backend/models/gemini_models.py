from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

def get_gemini_model(temperature=0, model='gemini-3-flash-preview', enable_search=False):
    """
    Factory function for Gemini models.
    Use 'gemini-3-flash-preview' for standard tasks.
    Use 'gemini-3-flash-preview' for tasks requiring high reasoning.
    """
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    # Determine thinking level based on model and user preference
    thinking_level = "high"
    if "flash" in model.lower():
        thinking_level = "minimal"
    
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=api_key,
        thinking_level= thinking_level
    )
    
    if enable_search:
        llm = llm.bind(tools=[{"google_search": {}}])
        
    return llm
