from agents.node import Node

from models import openai_models
from models import claude_models
from models import gemini_models
from models import vllm_models
from models import groq_models
from models import ollama_models
from typing import Optional
class LLMNode(Node):
    def __init__(self, state:Optional[str] = None,model=None, server=None, temperature=0, model_endpoint=None, stop=None, guided_json=None, ):
        self.state = state 
        self.model = model
        self.server = server
        self.temperature = temperature
        self.model_endpoint = model_endpoint
        self.stop = stop
        self.guided_json = guided_json

    def get_llm(self, json_model=False):
        if self.server == 'openai':
            return openai_models.get_open_ai_json(model=self.model, temperature=self.temperature) if json_model else openai_models.get_open_ai(model=self.model, temperature=self.temperature)
        if self.server == 'ollama':
            return ollama_models.OllamaJSONModel(model=self.model, temperature=self.temperature) if json_model else ollama_models.astOllamaModel(model=self.model, temperature=self.temperature)
        if self.server == 'vllm':
            return vllm_models.VllmJSONModel(
                model=self.model, 
                guided_json=self.guided_json,
                stop=self.stop,
                model_endpoint=self.model_endpoint,
                temperature=self.temperature
            ) if json_model else vllm_models.VllmModel(
                model=self.model,
                model_endpoint=self.model_endpoint,
                stop=self.stop,
                temperature=self.temperature
            )
        if self.server == 'groq':
            return groq_models.GroqJSONModel(
                model=self.model,
                temperature=self.temperature
            ) if json_model else groq_models.GroqModel(
                model=self.model,
                temperature=self.temperature
            )
        if self.server == 'claude':
            return claude_models.get_claude_ai_json(
                model=self.model,
                temperature=self.temperature
            ) if json_model else claude_models.get_claude_ai(
                model=self.model,
                temperature=self.temperature
            )
        if self.server == 'gemini':
            return gemini_models.GeminiJSONModel(
                model=self.model,
                temperature=self.temperature
            ) if json_model else gemini_models.GeminiModel(
                model=self.model,
                temperature=self.temperature
            )      

    def update_state(self, key, value):
        self.state = {**self.state, key: value}

    def get_state(self):
        return self.state