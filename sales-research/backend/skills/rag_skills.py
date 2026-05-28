from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from services.knowledge_service import KnowledgeService
import json

# Initialize the core service with NO default index
# In a real app, this might be injected or retrieved from a singleton
# We use a deferred initialization to ensure current_user's org index is used
def get_ks(index_name: Optional[str] = None):
    return KnowledgeService(index_name=index_name)

@tool
def search_intelligence_base(query: str, namespace: str, **kwargs) -> str:
    """
    Search the internal knowledge base within a specific namespace.
    Available namespaces:
    - 'playbooks': Strategic sales frameworks and messaging.
    - 'solutions': Technical product details and implementation guides.
    - 'case-studies': ROI proofs and success stories.
    Use this when you need specific, validated evidence.
    """
    user_id = kwargs.get("user_id")
    index_name = kwargs.get("index_name")
    return get_ks(index_name).retrieve_context(query, namespace, k=5, top_n=3, score_threshold=0.6, user_id=user_id, index_name=index_name)

@tool
def verify_solution_feasibility(product_name: str, industry: str, use_case: str, product_context: str) -> str:
    """
    Verify if a proposed product is a valid fit for a target industry and use case based on its provided description.
    Returns a verification status and any known constraints.
    """
    from models.gemini_models import get_gemini_model
    from langchain_core.messages import SystemMessage, HumanMessage

    prompt = f"""
    COMPLETELY ANALYZE the feasibility of '{product_name}' for the following scenario:
    
    INDUSTRY: {industry}
    USE CASE: {use_case}
    
    TECHNICAL/BUSINESS CONTEXT (INTERNAL):
    {product_context}
    
    YOUR GOAL:
    Determine if this is a credible, high-impact fit. Identify any "gotchas" or constraints mentioned in the context that might make this a bad or risky recommendation.
    
    Provide a concise (2-3 paragraph) verdict.
    """
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        messages = [
            SystemMessage(content="You are a strict Solution Architect. Your job is to verify product fit based on internal evidence."),
            HumanMessage(content=prompt)
        ]
        response = model.invoke(messages)
        return response.content
    except Exception as e:
        return f"FEASIBILITY ERROR: Could not verify fit due to technical issue: {e}"

@tool
def get_roi_proof_points(product_name: str, pain_point: str, **kwargs) -> str:
    """
    Retrieve specific ROI metrics and proof points for a product given a pain point.
    Use this to ground outreach in hard numbers.
    """
    user_id = kwargs.get("user_id")
    index_name = kwargs.get("index_name")
    query = f"ROI impact for {product_name} solving {pain_point}"
    return get_ks(index_name).retrieve_context(query, "case-studies", k=5, top_n=3, score_threshold=0.6, user_id=user_id, index_name=index_name)

# Export the skills
RAG_SKILLS = [search_intelligence_base, verify_solution_feasibility, get_roi_proof_points]
