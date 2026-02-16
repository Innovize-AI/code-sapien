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
    
    # Priority 1: Direct Marketing Signals
    if get_val(input_data, "demo_requested"):
        return {"signal_leverage_score": 100}
    
    if get_val(input_data, "download_marketing_material"):
        return {"signal_leverage_score": 90}

    # Priority 2: Interaction Sources
    if discovery_source == 'competitor_comment':
        return {"signal_leverage_score": 85}
    
    if discovery_source == 'keyword_search':
        return {"signal_leverage_score": 60}
    
    # Priority 3: ICP Fit
    return {"signal_leverage_score": 30}
