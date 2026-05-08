from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import WEBSITE_ANALYZER_PROMPT
from models.gemini_models import get_gemini_model
from pydantic import BaseModel, Field
from typing import List, Optional
import json
from utils import add_https_if_missing

import logging

logger = logging.getLogger(__name__)

class WebsiteAnalysis(BaseModel):
    summary: str = Field(description="High-level synthesis of company's value proposition and mission.")
    industry: str = Field(description="Identified industry sector.")
    target_audience: str = Field(description="Description of target customer segments.")
    core_offerings: List[str] = Field(description="List of primary products or services.")
    existing_ai_solutions: Optional[str] = Field(None, description="Details of any AI they already use or offer.")
    competitor_summary: Optional[str] = Field(None, description="Summary of key competitors they are positioning against.")
    is_competitor: bool = Field(description="Strict boolean: Does this company offer products that compete with Innovize AI (Glial, IDP, or Agentic KB)?")
    lead_segment: str = Field(description="Categorization: 'DIRECT_COMPETITOR', 'ADJACENT_PARTNER','POTENTIAL_CLIENT' or 'UNKNOWN'.")
    industry_pain_points: List[str] = Field(description="Generic or specific industry problems they solve.")
    competitive_advantage: str = Field(description="Unique selling points or competitive edges identified.")

def scrape_webpages(state: AgentState) -> dict:
    """Use requests and bs4 to scrape the provided web pages for detailed information."""
    website = add_https_if_missing(state["website"])
    
    if not website:
        return {"scraped_website_content": "Could not scrape empty website"}

    try:
        loader = WebBaseLoader(website)
        docs = loader.load()
        scraped_content = "\n\n".join([doc.page_content for doc in docs])
        return {"scraped_website_content": scraped_content}
    except Exception as e:
        logger.warning(f"Failed to scrape website {website}: {e}")
        return {"scraped_website_content": "Website could not be reached or scraped."}

async def website_analyzer(state: AgentState):
    """Analyzes scraped website content using Structured Output and normalizes industry."""
    from utils.industry_mapper import normalize_industry

    selling_profile = state.get("selling_company_profile")
    if selling_profile:
        products_summary = "\n".join([f"- {p.name}: {p.description}" for p in selling_profile.products])
        products_keywords = ", ".join([p.name for p in selling_profile.products])
    else:
        products_summary = "Glial (Revenue Intelligence), IDP (Document Automation), Agentic KB (Internal RAG)"
        products_keywords = "Glial, IDP, Knowledge Base, RAG"

    messages = [
        SystemMessage(content=WEBSITE_ANALYZER_PROMPT.format(
            selling_products_summary=products_summary,
            selling_products_keywords=products_keywords
        )), 
        HumanMessage(content=state['scraped_website_content'])
    ]
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(WebsiteAnalysis)
        response = await structured_llm.ainvoke(messages)
        
        if not response:
            return {"website_analysis": {}, "lead_segment": "UNKNOWN"}
            
        analysis_data = response.model_dump()
        
        # Normalize the extracted industry using our standard categories
        raw_industry = analysis_data.get("industry")
        if raw_industry:
            normalized_industry = await normalize_industry(raw_industry)
            analysis_data["industry"] = normalized_industry
            
        return {
            "website_analysis": analysis_data,
            "lead_segment": analysis_data.get("lead_segment", "UNKNOWN")
        }
    except Exception as e:
        logger.error(f"Error in website_analyzer: {e}")
        return {"website_analysis": {}}

