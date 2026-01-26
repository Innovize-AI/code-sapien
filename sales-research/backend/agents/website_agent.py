from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import WEBSITE_ANALYZER_PROMPT
from models.openai_models import get_open_ai
from pydantic import BaseModel, Field
from typing import List
import json
from utils import add_https_if_missing

class WebsiteAnalysis(BaseModel):
    summary: str = Field(description="High-level synthesis of company's value proposition and mission.")
    industry: str = Field(description="Identified industry sector.")
    target_audience: str = Field(description="Description of target customer segments.")
    core_offerings: List[str] = Field(description="List of primary products or services.")
    industry_pain_points: List[str] = Field(description="Generic or specific industry problems they solve.")
    competitive_advantage: str = Field(description="Unique selling points or competitive edges identified.")

def scrape_webpages(state: AgentState) -> dict:
    """Use requests and bs4 to scrape the provided web pages for detailed information."""
    website = add_https_if_missing(state["website"])
    
    if not website:
        return {"scraped_website_content": "Could not scrape empty website"}

    loader = WebBaseLoader(website)
    docs = loader.load()
    scraped_content = "\n\n".join([doc.page_content for doc in docs])
    
    return {"scraped_website_content": scraped_content}

def website_analyzer(state: AgentState):
    """Analyzes scraped website content using Structured Output."""
    messages = [
        SystemMessage(content=WEBSITE_ANALYZER_PROMPT), 
        HumanMessage(content=state['scraped_website_content'])
    ]
    try:
        model = get_open_ai(model="gpt-4o-mini", temperature=0)
        structured_llm = model.with_structured_output(WebsiteAnalysis)
        response = structured_llm.invoke(messages)
        
        if not response:
            return {"website_analysis": {}}
            
        return {"website_analysis": response.dict()}
    except Exception as e:
        print(f"Error in website_analyzer: {e}")
        return {"website_analysis": {}}

