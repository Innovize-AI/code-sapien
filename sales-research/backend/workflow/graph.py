import re
import json
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from workflow.state import AgentState
from agents.linkedin_agent import get_linkedin_profile, get_linkedin_posts, get_linkedin_engagement, get_linkedin_company_data, linkedin_profile_analyzer
from agents.website_agent import scrape_webpages, website_analyzer
from agents.lead_scoring_agent import lead_data_extractor, lead_scorer
from agents.report_agent import sales_research_report_generator
from agents.intent_agent import email_history_fetcher_node, email_intent_analyzer_node
from agents.strategy_agent import pain_point_node, solution_node, outreach_node
from agents.recommender_agent import strategic_recommender_node
from agents.follow_up_agent import follow_up_strategy_node
from agents.cso_agent import narrative_arbitrator_node
from agents.waterfall_agent import signal_waterfall_node
from agents.rag_researcher import strategic_rag_researcher_node
from agents.crm_agent import crm_lookup_node


def discovery_router(state: AgentState):
    """
    Decides whether to re-run deep discovery (pain points/solutions).
    Skips if target_pain_points exist and refresh is False.
    """
    input_data = state.get("input_lead_data")
    refresh = getattr(input_data, 'refresh', False) if hasattr(input_data, 'refresh') else input_data.get('refresh', False) if isinstance(input_data, dict) else False
    
    trigger = getattr(input_data, 'trigger_context', None) if hasattr(input_data, 'trigger_context') else input_data.get('trigger_context') if isinstance(input_data, dict) else None
    
    # If this is a targeted update (email/crm), we skip deep pain point discovery
    # because the company profile likely hasn't changed.
    if trigger in ["email_update", "crm_update"]:
        print(f"Skipping deep discovery for trigger: {trigger}")
        return "strategic_merger"
    
    if not refresh and state.get("target_pain_points"):
        print("Skipping discovery/solution mapping - analysis already exists.")
        return "strategic_merger"
        
    return "pain_point_discovery"

def strategy_router(state: AgentState):
    """
    Decides between first-touch outreach and context-aware follow-up.
    """
    email_history = state.get("email_history", [])
    meeting_notes = state.get("meeting_notes", "")
    
    # If there's any history/notes, it's a follow-up
    if email_history or (meeting_notes and meeting_notes.strip()):
        print("Routing to Follow-up Strategy Agent")
        return "follow_up_strategy"
    
    print("Routing to First-touch Outreach Designer")
    return "outreach_designer"

def strategic_merger(state: AgentState):
    """Synchronization node for parallel strategic branches."""
    return state

def collector(state: AgentState):
    print("WEBSITE COLLECTOR ", state["website"])
    return {"linkedin_url": state["linkedin_url"], "website": state["website"]}

def research_router(state: AgentState):
    """
    Decides which parallel research branches to trigger.
    Skips if analysis exists and refresh is False.
    """
    next_nodes = []
    input_data = state.get("input_lead_data")
    refresh = getattr(input_data, 'refresh', False) if hasattr(input_data, 'refresh') else input_data.get('refresh', False) if isinstance(input_data, dict) else False

    trigger_ctx = getattr(input_data, 'trigger_context', None) if hasattr(input_data, 'trigger_context') else input_data.get('trigger_context') if isinstance(input_data, dict) else None

    # Branch 1: LinkedIn
    if not trigger_ctx or trigger_ctx == "full":
        if refresh or not state.get("user_profile_analysis"):
            if not state.get("linkedin_url"):
                next_nodes.append("enrich_linkedin")
            else:
                next_nodes.append("linkedin_profile_fetcher")
            
    # Branch 2: Website
    if not trigger_ctx or trigger_ctx == "full":
        if refresh or not state.get("website_analysis"):
            if not state.get("website"):
                next_nodes.append("enrich_website")
            else:
                next_nodes.append("website_scraper")
            
    # Branch 3: Email History - Run if triggered OR if standard run
    if (trigger_ctx == "email_update") or (not trigger_ctx and state.get("email_id")):
        next_nodes.append("email_history_fetcher")

    # Branch 4: CRM Lookup - Run if triggered OR if standard run
    if (trigger_ctx == "crm_update") or (not trigger_ctx):
        next_nodes.append("crm_lookup")
        
    return next_nodes

def enrich_linkedin(state: AgentState):
    # Placeholder for LinkedIn enrichment logic
    return {"linkedin_url": ""}

def enrich_website(state: AgentState):
    """enrich website from email_id or cached LinkedIn company profile"""
    
    # 1. Try Email Domain (Fastest)
    email_id = state.get("email_id")
    validate_email_regex = r"^(?!.*@(gmail\.com|hotmail\.com|yahoo\.com|outlook\.com|aol\.com|icloud\.com|mail\.com|zoho\.com|protonmail\.com|yandex\.com)).*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$"

    if email_id:
        match = re.match(validate_email_regex, email_id)
        if match:
            domain = match.group(2)
            url = f"https://{domain}"
            print(f"Work domain found from email: {domain}")
            return {"website": url}
    
    # 2. LinkedIn Enrichment Fallback
    linkedin_url = state.get("linkedin_url")
    if linkedin_url:
        from agents.linkedin_agent import get_linkedin_profile, get_company_details
        
        if len(state.get("lead_company_linkedin_url", "")) > 0:
            company_url = state.get("lead_company_linkedin_url")
        else:
            # 1. Ensure we have the profile (and thus the lead company URL)
            profile_res = get_linkedin_profile(state)
            company_url = profile_res.get("lead_company_linkedin_url") or state.get("lead_company_linkedin_url")
        
        if company_url:
            print(f"Enriching company info for: {company_url}")
            company_details = get_company_details(company_url)
            if company_details:
                basic_info = company_details.get("basic_info", {})
                # 2. Return ONLY website and company intelligence
                return {
                    "website": basic_info.get("website"),
                    "company_name": basic_info.get("name"),
                    "company_description": basic_info.get("description"),
                    "company_industries": basic_info.get("industries", []),
                    "company_stats": company_details.get("stats", {}),
                    
                    "lead_company_linkedin_url": company_url,
                    "user_profile_details": profile_res.get("user_profile_details")
                }
    
    return {"website": ""}


# nodes moved or integrated into router


# Define the graph
builder = StateGraph(AgentState)

builder.add_node("collector", collector)

# LinkedIn Subgraph Nodes
builder.add_node("linkedin_profile_fetcher", get_linkedin_profile)
builder.add_node("linkedin_posts_fetcher", get_linkedin_posts)
builder.add_node("linkedin_engagement_fetcher", get_linkedin_engagement)
builder.add_node("linkedin_company_fetcher", get_linkedin_company_data)
builder.add_node("linkedin_profile_analyzer", linkedin_profile_analyzer)

# Website Nodes
builder.add_node("website_scraper", scrape_webpages)
builder.add_node("website_analyzer", website_analyzer)

# Logic/Bridge Nodes
builder.add_node("lead_data_extractor", lead_data_extractor, defer=True)
builder.add_node("lead_scorer", lead_scorer)

# Strategic Nodules
builder.add_node("pain_point_discovery", pain_point_node)
builder.add_node("strategic_rag_researcher", strategic_rag_researcher_node)
builder.add_node("solution_mapping", solution_node)
builder.add_node("outreach_designer", outreach_node)
builder.add_node("follow_up_designer", follow_up_strategy_node)
builder.add_node("strategic_recommender", strategic_recommender_node)
builder.add_node("strategic_merger", strategic_merger, defer=True)

builder.add_node("report_generator", sales_research_report_generator, defer=True)
builder.add_node("enrich_linkedin", enrich_linkedin)
builder.add_node("enrich_website", enrich_website)
builder.add_node("email_history_fetcher", email_history_fetcher_node)
builder.add_node("email_intent_analyzer", email_intent_analyzer_node)
builder.add_node("signal_waterfall", signal_waterfall_node)
builder.add_node("narrative_arbitrator", narrative_arbitrator_node)
builder.add_node("crm_lookup", crm_lookup_node)

# Set entry point
builder.set_entry_point("collector")

# Add edges

# LinkedIn Subgraph flow
builder.add_edge("linkedin_profile_fetcher", "linkedin_posts_fetcher")
builder.add_edge("linkedin_posts_fetcher", "linkedin_engagement_fetcher")
builder.add_edge("linkedin_engagement_fetcher", "linkedin_company_fetcher")
builder.add_edge("linkedin_company_fetcher", "linkedin_profile_analyzer")

# Enrichment flow
builder.add_edge("enrich_linkedin", "linkedin_profile_fetcher")
builder.add_edge("enrich_website", "website_scraper")

# Cross-functional flows
builder.add_edge("website_scraper", "website_analyzer")

# Convergence to Data Extraction
builder.add_edge("linkedin_profile_analyzer", "lead_data_extractor")
builder.add_edge("website_analyzer", "lead_data_extractor")
builder.add_edge("email_history_fetcher", "lead_data_extractor")
builder.add_edge("crm_lookup", "lead_data_extractor")

# Sequential Logic
builder.add_edge("lead_data_extractor", "lead_scorer")
builder.add_edge("lead_scorer", "signal_waterfall")

# Strategic Discovery Branch
builder.add_conditional_edges("signal_waterfall", discovery_router, {
    "pain_point_discovery": "pain_point_discovery",
    "strategic_merger": "strategic_merger"
})
builder.add_edge("pain_point_discovery", "strategic_rag_researcher")
builder.add_edge("strategic_rag_researcher", "solution_mapping")
builder.add_edge("solution_mapping", "strategic_merger")

# Narrative Arbitrator (CSO) runs BEFORE sub-agents
builder.add_edge("strategic_merger", "narrative_arbitrator")

# Guided Parallel Execution
builder.add_edge("narrative_arbitrator", "strategic_recommender")
builder.add_edge("narrative_arbitrator", "email_intent_analyzer")
builder.add_conditional_edges("narrative_arbitrator", strategy_router, {
    "outreach_designer": "outreach_designer",
    "follow_up_strategy": "follow_up_designer"
})

# Convergence to Report
builder.add_edge("outreach_designer", "report_generator")
builder.add_edge("follow_up_designer", "report_generator")
builder.add_edge("strategic_recommender", "report_generator")
builder.add_edge("email_intent_analyzer", "report_generator")

builder.add_edge("report_generator", END)

builder.add_conditional_edges("collector", research_router, {
    "enrich_linkedin": "enrich_linkedin",
    "linkedin_profile_fetcher": "linkedin_profile_fetcher",
    "enrich_website": "enrich_website",
    "website_scraper": "website_scraper",
    "email_history_fetcher": "email_history_fetcher",
    "crm_lookup": "crm_lookup"
})


memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

NODE_STATUS_MAPPING = {
    "lead_data_extractor": "Extracting combined lead intelligence...",
    "collector": "Intelligent gathering started...",
    "lead_scorer": "Calculating lead score and intent...",
    "report_generator": "Synthesizing research into final report...",
    "linkedin_profile_fetcher": "Fetching LinkedIn profile details...",
    "linkedin_posts_fetcher": "Retrieving recent posts and activity...",
    "linkedin_engagement_fetcher": "Analyzing reactions and audience engagement...",
    "linkedin_company_fetcher": "Gathering company news and hiring status...",
    "website_scraper": "Scraping company website footprint...",
    "linkedin_profile_analyzer": "Conducting deep social persona analysis...",
    "website_analyzer": "Analyzing company operations and market position...",
    "email_history_fetcher": "Reviewing past email interactions...",
    "pain_point_discovery": "Identifying specific business pain points...",
    "strategic_rag_researcher": "Agentic RAG: Retrieving & verifying strategic playbooks...",
    "solution_mapping": "Mapping verified solutions to lead profile...",
    "outreach_designer": "Designing personalized outreach strategy...",
    "follow_up_designer": "Crafting context-aware follow-up strategy...",
    "strategic_recommender": "Determining buyer journey stage & strategy...",
    "crm_lookup": "Matching lead with HubSpot CRM context...",
}

