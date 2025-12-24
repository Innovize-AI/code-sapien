import re
import json
from langgraph.graph import StateGraph, START, END
from workflow.state import AgentState
from agents.linkedin_agent import get_linkedin_data, linkedin_profile_analyzer
from agents.website_agent import scrape_webpages, website_analyzer
from agents.lead_scoring_agent import lead_data_extractor, lead_scorer
from agents.report_agent import sales_research_report_generator

def collector(state: AgentState):
    print("WEBSITE COLLECTOR ", state["website"])
    return {"linkedin_url": state["linkedin_url"], "website": state["website"]}

def should_enrich_linkedin(state: AgentState):
    linkedin_profile = state["linkedin_url"]
    print("should enrich called", linkedin_profile)
    if not linkedin_profile:
        return "enrich_linkedin"
    else:
        return "profile_fetcher"

def should_enrich_website(state: AgentState):
    website = state["website"]
    if not website:
        return "enrich_website"
    else:
        return "website_scraper"

def enrich_linkedin(state: AgentState):
    # Placeholder for LinkedIn enrichment logic
    return {"linkedin_url": "https://www.linkedin.com/in/pavankumar34/"}

def enrich_website(state: AgentState):
    email_id = state["email_id"]
    validate_email_regex = r"^(?!.*@(gmail\.com|hotmail\.com|yahoo\.com|outlook\.com|aol\.com|icloud\.com|mail\.com|zoho\.com|protonmail\.com|yandex\.com)).*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$"

    if not email_id:
        return {"website": ""}
    
    match = re.match(validate_email_regex, email_id)
    if match:
        domain = match.group(2) # Group 2 is the domain
        url = f"https://{domain}"
        print(f"Work domain: {domain}")
        return {"website": url}
    else:
        return {"website": ""}

# Define the graph
builder = StateGraph(AgentState)

builder.add_node("collector", collector)
builder.add_node("profile_fetcher", get_linkedin_data)
builder.add_node("website_scraper", scrape_webpages)
builder.add_node("linkedin_profile_analyzer", linkedin_profile_analyzer)
builder.add_node("website_analyzer", website_analyzer)
builder.add_node("lead_data_extractor", lead_data_extractor)
builder.add_node("lead_scorer", lead_scorer)
builder.add_node("report_generator", sales_research_report_generator)
builder.add_node("enrich_linkedin", enrich_linkedin)
builder.add_node("enrich_website", enrich_website)

# Set entry point
builder.set_entry_point("collector")

# Add edges
builder.add_edge("profile_fetcher", "linkedin_profile_analyzer")
builder.add_edge("website_scraper", "website_analyzer")
builder.add_edge("enrich_linkedin", "profile_fetcher")
builder.add_edge("enrich_website", "website_scraper")
builder.add_edge("linkedin_profile_analyzer", "lead_data_extractor")
builder.add_edge("website_analyzer", "lead_data_extractor")
builder.add_edge("lead_data_extractor", "lead_scorer")
builder.add_edge("lead_scorer", "report_generator")
builder.add_edge("report_generator", END)

builder.add_conditional_edges("collector", should_enrich_linkedin)
builder.add_conditional_edges("collector", should_enrich_website)

graph = builder.compile()

NODE_STATUS_MAPPING = {
    "lead_data_extractor": "Extracting lead data...",
    "collector": "Gathering research data...",
    "lead_scorer": "Calculating lead score...",
    "report_generator": "Generating final report...",
    "profile_fetcher": "Fetching LinkedIn profile...",
    "website_scraper": "Scraping company website...",
    "linkedin_profile_analyzer": "Analyzing social activity...",
    "website_analyzer": "Analyzing company footprint...",
}
