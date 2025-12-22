from typing import List, Optional
from langchain_community.tools.tavily_search import TavilySearchResults
from pydantic import BaseModel, Field
import os

# Ensure TAVILY_API_KEY is set in environment variables
# os.environ["TAVILY_API_KEY"] = "..." 

class LeadDiscoveryInput(BaseModel):
    industry: str = Field(..., description="Target industry, e.g., 'FinTech', 'Healthcare'")
    job_title: str = Field(..., description="Target job title, e.g., 'CTO', 'VP of Sales'")
    location: Optional[str] = Field(None, description="Target location, e.g., 'San Francisco', 'New York'")
    company_size: Optional[str] = Field(None, description="Target company size")
    provider: Optional[str] = Field("tavily", description="Search provider: 'tavily' or 'apollo'")

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

def find_leads_tavily(input_data: LeadDiscoveryInput) -> List[str]:
    """
    Uses Tavily to search for LinkedIn profiles matching the criteria.
    Returns a list of LinkedIn URLs.
    """
    query = generate_search_query(input_data)
    print(f"Executing Search Query: {query}")
    
    # max_results can be adjusted. 5-10 is usually good for a first pass.
    tavily_tool = TavilySearchResults(max_results=5)
    
    try:
        results = tavily_tool.invoke({"query": query})
        
        linkedin_urls = []
        for res in results:
            url = res.get("url")
            # Basic validation to ensure it's a profile URL
            if url and "linkedin.com/in/" in url:
                linkedin_urls.append(url)
                
        return linkedin_urls
        
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        return []

def find_leads_apollo(input_data: LeadDiscoveryInput) -> List[str]:
    """
    Uses Apollo.io API to search for people.
    """
    import requests
    
    api_key = os.environ.get("APOLLO_API_KEY")
    if not api_key:
        print("APOLLO_API_KEY not found in environment variables.")
        return []

    url = "https://api.apollo.io/v1/mixed_people/search"
    
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key
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
        # Apollo uses strict industry IDs or tags usually, but keyword search often works in organization content
        # For simplicity in this 'mixed_people/search', we can try adding it to 'q_organization_domains' or simply as a generic keyword query if supported?
        # A safer bet for broad scraping without IDs is often just not being too specific or using 'q_keywords'
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
        
        linkedin_urls = []
        for person in data.get("people", []):
            if person.get("linkedin_url"):
                linkedin_urls.append(person["linkedin_url"])
                
        return linkedin_urls

    except Exception as e:
        print(f"Error during Apollo search: {e}")
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
    print("Found URLs (Tavily):", urls)
