from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from services.knowledge_service import KnowledgeService
import json

# Initialize the core service
# In a real app, this might be injected or retrieved from a singleton
knowledge_service = KnowledgeService(index_name="glial-index")

@tool
def search_intelligence_base(query: str, namespace: str) -> str:
    """
    Search the Innovize AI knowledge base within a specific namespace.
    Available namespaces: 
    - 'playbooks': Strategic sales frameworks and messaging.
    - 'solutions': Technical product details and implementation guides.
    - 'case_studies': ROI proofs and success stories.
    Use this when you need specific, validated evidence.
    """
    return knowledge_service.retrieve_context(query, namespace, k=3)

@tool
def verify_solution_feasibility(product_name: str, industry: str, use_case: str, product_context: str) -> str:
    """
    Verify if a proposed product is a valid fit for a target industry and use case based on its provided description.
    Returns a verification status and any known constraints.
    """
    # This tool now relies on the agent providing the 'product_context' from the selling company profile
    return f"ANALYSIS REQUESTED: Verifying {product_name} for {industry} ({use_case}) against context: {product_context[:100]}..."

@tool
def get_roi_proof_points(product_name: str, pain_point: str) -> str:
    """
    Retrieve specific ROI metrics and proof points for a product given a pain point.
    Use this to ground outreach in hard numbers.
    """
    query = f"ROI impact for {product_name} solving {pain_point}"
    return knowledge_service.retrieve_context(query, "case_studies", k=2)

# Export the skills
RAG_SKILLS = [search_intelligence_base, verify_solution_feasibility, get_roi_proof_points]
