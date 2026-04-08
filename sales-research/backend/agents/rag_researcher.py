from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from skills.rag_skills import RAG_SKILLS
import json
import logging

logger = logging.getLogger(__name__)
from models.gemini_models import get_gemini_model
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from services.knowledge_service import KnowledgeService

# Global service instance (or instantiate within node)
knowledge_service = KnowledgeService(index_name="glial-index")

class PivotFitCheck(BaseModel):
    is_fit: bool = Field(description="True if the company is a strong fit for the strategic pivot product.")
    reasoning: str = Field(description="Explanation of why it fits or does not fit based on industry, size, and role.")

async def verify_strict_fit(state: Dict[str, Any], product_name: str, target_roles: List[str], target_industries: List[str]) -> PivotFitCheck:
    """
    Verifies if the lead is a strict fit for the strategic pivot.
    Utilizes semantic matching for roles and industry qualification.
    """
    logger.info(f"Verifying Strict Fit for {product_name}...")
    
    user_details = state.get("user_profile_details", {})
    headline = user_details.get("basic_info", {}).get("headline", "")
    
    website_analysis = state.get("website_analysis", {})
    industry = website_analysis.get("industry", "Unknown")
    company_desc = website_analysis.get("summary", "Unknown")
    
    extracted_data = state.get("lead_extracted_data", {})
    company_stats = state.get("company_stats", {})
    company_size = extracted_data.get("company_size") or \
                   company_stats.get("employee_count") or \
                   company_stats.get("staff_count") or \
                   "Unknown"

    # Fetch product-specific qualification context via RAG
    logger.info(f"Retrieving Qualification Context for {product_name}...")
    qualification_context = knowledge_service.retrieve_context(
        query=f"{product_name} ICP qualification criteria, target industries, and ideal roles",
        namespace="playbooks",
        k=3
    )

    prompt = f"""
    Analyze if this prospect is a high-potential fit for '{product_name}'.
    
    ### PRODUCT QUALIFICATION CONTEXT (INTERNAL):
    {qualification_context if qualification_context.strip() else f"Standard qualification for {product_name}."}
    
    ### TARGET CRITERIA:
    - Target Roles: {target_roles}
    - Target Industries: {target_industries}
    
    ### PROSPECT PROFILE:
    - Current Role/Headline: {headline}
    - Company Industry: {industry}
    - Company Size: {company_size}
    - Company Description: {company_desc}
    
    ### YOUR TASK (SEMANTIC ANALYSIS):
    1. **Role Match**: Does the prospect's headline semantically align with the target roles? (e.g., 'VP Sales' matches 'VP of Sales'). Use your intelligence to map seniority and departments.
    2. **Industry Match**: Does the company's industry or description align with the target industries or the qualification context? 
    3. **Final Verdict**: Approve only if there is a clear strategic fit.
    
    Return 'is_fit' as true only if BOTH role (semantically) and industry/company profile align.
    """
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(PivotFitCheck)
        messages = [
            SystemMessage(content="You are a strict qualification agent. You specialize in semantic role and industry mapping."),
            HumanMessage(content=prompt)
        ]
        result = await structured_llm.ainvoke(messages)
        return result
    except Exception as e:
        logger.info(f"Error in verification: {e}")
        return PivotFitCheck(is_fit=False, reasoning=f"Error verifying fit: {e}")

def create_strategic_rag_agent():
    """
    Creates an autonomous researcher agent with specialized sales intelligence skills.
    """
    llm = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Strategic Research Agent at {selling_company_name}. 
        Your mission is to find the MOST AUTHENTIC evidence and solutions for a given prospect's pain points.
        
        ### YOUR PORTFOLIO:
        {selling_products_list}
        
        ### YOUR WORKFLOW:
        1. **Analyze Pain**: Understand the prospect's industry and challenges.
        2. **Search Discovery**: Use `search_intelligence_base` to find relevant internal playbooks.
        3. **Verify Fit**: Use `verify_solution_feasibility` (passing the product's description from YOUR PORTFOLIO) to ensure it's a valid fit.
        4. **ROI Proofing**: Use `get_roi_proof_points` to find specific metrics.
        5. **Synthesize**: Combine all evidence into a definitive Strategic Briefing.
        
        Be precise. Never guess. Use only the information retrieved via your skills."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, RAG_SKILLS, prompt)
    return AgentExecutor(agent=agent, tools=RAG_SKILLS, verbose=True)

async def strategic_rag_researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node that performs agentic RAG to find the best solutions.
    """
    pain_points = state.get("target_pain_points", {})
    website_analysis = state.get("website_analysis", {})
    industry = website_analysis.get("industry", "Unknown")
    company_desc = website_analysis.get("summary", "Unknown")
    selling_profile = state.get("selling_company_profile")
    
    selling_company_name = getattr(selling_profile, "company_name", "Innovize AI") if selling_profile else "Innovize AI"
    
    # --- RAG Discovery Phase 1: General Industry Opportunities ---
    logger.info(f"Performing General Industry Opportunity Discovery for {industry}...")
    general_industry_context = knowledge_service.retrieve_context(
        query=f"Case studies and solutions for {industry} industry focusing on {json.dumps(pain_points)}",
        namespace="case-studies", # Search specifically in case studies first
        k=3
    )
    
    # --- RAG Discovery Phase 2: Explicit Product Qualification ---
    qualified_products = []
    combined_specific_context = ""
    pivot_fit_names = []
    
    if selling_profile and selling_profile.products:
        for product in selling_profile.products:
            # Check if product is a strategic pivot
            is_pivot = getattr(product, "is_strategic_pivot", False)
            
            if is_pivot:
                # Perform Smart Fit Check (Semantic)
                fit_check = await verify_strict_fit(
                    state, 
                    product.name, 
                    getattr(product, "target_roles", []), 
                    getattr(product, "target_industries", [])
                )
                
                if fit_check.is_fit:
                    logger.info(f"Confirmed Fit for Pivot: {product.name}. Reason: {fit_check.reasoning}")
                    qualified_products.append(product)
                    pivot_fit_names.append(product.name)
                    
                    # Retrieve product-specific content
                    relevant_files = getattr(product, "attached_playbooks", []) + getattr(product, "attached_case_studies", [])
                    if not relevant_files:
                        relevant_files = getattr(product, "relevant_files", [])
                    
                    if relevant_files:
                        specific_context = knowledge_service.retrieve_from_files(
                            relevant_files, 
                            f"{product.name} implementation and ROI for {industry}", 
                            k=4
                        )
                        combined_specific_context += f"\n\n### CONTEXT FOR {product.name}:\n{specific_context}"
                else:
                    logger.info(f"Rejected Pivot: {product.name}. Reason: {fit_check.reasoning}")
            else:
                # Non-pivot products are added to the general pool for the agent to consider
                qualified_products.append(product)

    # Re-build filtered product list for the agent
    filtered_products_list = "\n".join([f"- {p.name}: {p.description}" for p in qualified_products])
    
    # Final Refined Research Goal
    research_goal = f"""
    Find the best {selling_company_name} solutions for a prospect in the {industry} industry.
    Identified Prospect Pain Points: {json.dumps(pain_points)}
    
    === QUALIFIED INTERNAL ASSETS (USE THESE FIRST) ===
    {combined_specific_context if combined_specific_context else "No project-specific playbooks attached."}
    
    === INDUSTRY-SPECIFIC PROVEN SOLUTIONS (CASE STUDIES) ===
    {general_industry_context if general_industry_context.strip() else "No direct industry case studies found."}
    ===================================================
    
    Your mission:
    1. Synthesize the 'Qualified Internal Assets' with the 'Industry-Specific Case Studies'.
    2. Select the absolute best product(s) from the pool below to lead with.
    3. Return a definitive 'Strategic Solution Briefing' including ROI markers and proof points.
    
    AVAILABLE PRODUCT POOL:
    {filtered_products_list}
    """
    
    executor = create_strategic_rag_agent()
    
    result = await executor.ainvoke({
        "input": research_goal, 
        "chat_history": [],
        "selling_company_name": selling_company_name,
        "selling_products_list": filtered_products_list
    })
    
    return {
        "strategic_rag_briefing": result["output"],
        "is_strategic_pivot_fit": len(pivot_fit_names) > 0,
        "pivot_product_name": ", ".join(pivot_fit_names) if pivot_fit_names else ""
    }
