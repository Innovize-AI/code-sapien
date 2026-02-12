from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import WEBSITE_ANALYZER_PROMPT
from models.openai_models import get_open_ai
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from utils import add_https_if_missing

class WebsiteAnalysis(BaseModel):
    summary: str = Field(description="High-level synthesis of company's value proposition and mission.")
    industry: str = Field(description="Identified industry sector.")
    target_audience: str = Field(description="Description of target customer segments.")
    core_offerings: List[str] = Field(description="List of primary products or services.")
    existing_ai_solutions: Optional[str] = Field(None, description="Details of any AI they already use or offer.")
    competitor_summary: Optional[str] = Field(None, description="Summary of key competitors they are positioning against.")
    is_competitor: bool = Field(description="Strict boolean: Does this company offer products that compete with Innovize AI (Glial, IDP, or Agentic KB)?")
    lead_segment: str = Field(description="Categorization: 'DIRECT_COMPETITOR', 'ADJACENT_PARTNER', or 'POTENTIAL_CLIENT'.")
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
            return {"website_analysis": {}, "lead_segment": "POTENTIAL_CLIENT"}
            
        analysis_data = response.model_dump()
        return {
            "website_analysis": analysis_data,
            "lead_segment": analysis_data.get("lead_segment", "POTENTIAL_CLIENT")
        }
    except Exception as e:
        print(f"Error in website_analyzer: {e}")
        return {"website_analysis": {}}
