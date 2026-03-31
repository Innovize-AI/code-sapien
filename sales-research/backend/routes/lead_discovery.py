from typing import List, Optional
from pydantic import BaseModel, Field
import os
from sqlalchemy import select
from db.models import OrganizationSettings
from db.database import SessionLocal  # Need a synchronous way or run async
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

# --- Construction logic remains same ---

class LeadDiscoveryInput(BaseModel):
    industry: str = Field(..., description="Target industry, e.g., 'FinTech', 'Healthcare'")
    job_title: str = Field(..., description="Target job title, e.g., 'CTO', 'VP of Sales'")
    location: Optional[str] = Field(None, description="Target location, e.g., 'San Francisco', 'New York'")
    company_size: Optional[str] = Field(None, description="Target company size")
    provider: Optional[str] = Field("tavily", description="Search provider: 'tavily', 'apollo', or 'linkedin_keyword'")
    keywords: Optional[List[str]] = Field(None, description="Keywords for LinkedIn post search")

def generate_search_query(input_data: LeadDiscoveryInput) -> str:
    """
    Constructs a Google Dork / X-Ray search query for Tavily.
    Target: site:linkedin.com/in 
    """
    query_parts = ["site:linkedin.com/in"]
    
    # Add negative keywords to avoid job postings, company pages, etc.
    query_parts.append('-intitle:"jobs"')
    query_parts.append('-intitle:"hiring"')
    
    # Add specific constraints
    if input_data.job_title:
        query_parts.append(f'"{input_data.job_title}"')
    
    if input_data.industry:
        query_parts.append(f'"{input_data.industry}"')
        
    if input_data.location:
        query_parts.append(f'"{input_data.location}"')

    return " ".join(query_parts)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def find_leads_tavily(input_data: LeadDiscoveryInput, api_key: str = None) -> List[dict]:
    """
    Uses Tavily to search for LinkedIn profiles matching the criteria.
    Returns a list of dicts: {"url": str, "website": str}
    """
    # Set the key in env for LangChain tool
    if api_key:
        os.environ["TAVILY_API_KEY"] = api_key
    elif not os.environ.get("TAVILY_API_KEY"):
         logger.warning("TAVILY_API_KEY not found.")
         return []

    query = generate_search_query(input_data)
    logger.info(f"Executing Search Query: {query}")
    
    # Deferred heavy import
    from langchain_community.tools.tavily_search import TavilySearchResults
    
    # max_results can be adjusted. 5-10 is usually good for a first pass.
    tavily_tool = TavilySearchResults(max_results=5)
    
    try:
        results = tavily_tool.invoke({"query": query})
        
        leads = []
        for res in results:
            url = res.get("url")
            # Basic validation to ensure it's a profile URL
            if url and "linkedin.com/in/" in url:
                # Tavily doesn't usually return the company website directly in this dork
                # We return an empty string, allowing the enrichment logic or user to fill it
                leads.append({"url": url, "website": ""})
                
        return leads
        
    except Exception as e:
        logger.error(f"Error during Tavily search: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def find_leads_apollo(input_data: LeadDiscoveryInput, api_key: str = None) -> List[dict]:
    """
    Uses Apollo.io API to search for people.
    Returns a list of dicts: {"url": str, "website": str}
    """
    import requests
    
    # Use passed key, or fallback to env
    final_api_key = api_key or os.environ.get("APOLLO_API_KEY")
    
    if not final_api_key:
        logger.warning("APOLLO_API_KEY not found.")
        return []

    url = "https://api.apollo.io/v1/mixed_people/search"
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": final_api_key
    }
    
    # Construct filters
    payload = {
        "page": 1,
        "per_page": 10,
        "person_titles": [input_data.job_title],
    }
    
    if input_data.location:
        payload["person_locations"] = [input_data.location]
        
    if input_data.industry:
        payload["q_organization_keyword_tags"] = [input_data.industry]

    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 422 or response.status_code == 403:
            error_msg = response.text.lower()
            if "paid plan" in error_msg or "upgrade" in error_msg:
                raise Exception("Apollo API requires a paid plan. Please upgrade or use Tavily.")
            else:
                raise Exception(f"Apollo API Error: {response.text}")
                
        response.raise_for_status()
        data = response.json()
        
        leads = []
        for person in data.get("people", []):
            if person.get("linkedin_url"):
                # Apollo often includes organization domain
                website = ""
                if person.get("organization") and person["organization"].get("website_url"):
                    website = person["organization"]["website_url"]
                elif person.get("organization") and person["organization"].get("primary_domain"):
                    website = f"https://{person['organization']['primary_domain']}"
                
                leads.append({
                    "url": person["linkedin_url"],
                    "website": website
                })
                
        return leads

    except Exception as e:
        logger.error(f"Error during Apollo search: {e}")
        # Re-raise user-friendly exceptions so they bubble up to the UI
        if "requires a paid plan" in str(e):
            raise e
        return []

if __name__ == "__main__":
    # Test block
    test_input = LeadDiscoveryInput(
        industry="Artificial Intelligence",
        job_title="Founder",
        location="San Francisco",
        provider="tavily"
    )
    urls = find_leads_tavily(test_input)
    logger.info("Found URLs (Tavily):", urls)
