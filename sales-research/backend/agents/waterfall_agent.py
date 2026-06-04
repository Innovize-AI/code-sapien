from workflow.state import AgentState

def signal_waterfall_node(state: AgentState):
    """
    Calculates the 'Signal Leverage Score' to prioritize high-intent leads.
    Tier 1: Direct Inbound/Interaction (Score 90-100)
    Tier 2: Competitor Intercept (Score 70-89)
    Tier 3: Thematic Pain (Score 40-69)
    Tier 4: ICP Fit (Score 0-39)
    """
    input_data = state.get("input_lead_data")
    if not input_data:
        return {"signal_leverage_score": 0}

    # Handle both dict and Pydantic model for robustness
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    discovery_source = get_val(input_data, "discovery_source")
    lead_source = get_val(input_data, "lead_source")
    
    # Priority 1: Direct Marketing Signals
    if get_val(input_data, "demo_requested"):
        return {"signal_leverage_score": 100}
    
    if get_val(input_data, "download_marketing_material"):
        return {"signal_leverage_score": 90}

    # Priority 2: Hiring Signals (linkedin_job discovery or active hiring data)
    hiring_data = state.get("hiring_data") or get_val(input_data, "hiring_data") or get_val(input_data, "profile_metadata", {}).get("hiring_jobs")
    if discovery_source == 'linkedin_job' or lead_source == 'linkedin_job' or hiring_data:
        return {"signal_leverage_score": 85}

    # Priority 3: Interaction Sources (Competitor Comment / Keyword Search scaled to 75)
    if discovery_source in ['competitor_comment', 'keyword_search'] or lead_source in ['competitor_comment', 'keyword_search', 'keyword']:
        return {"signal_leverage_score": 75}
    
    # Priority 4: ICP Fit
    return {"signal_leverage_score": 30}
