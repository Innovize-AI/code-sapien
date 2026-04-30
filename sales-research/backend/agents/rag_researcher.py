import os
from typing import List, Dict, Any, Optional
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
from db.database import SessionLocal
from db.crud import get_org_settings

# No global knowledge_service - must be instantiated with correct index per-request

class PivotFitCheck(BaseModel):
    is_fit: bool = Field(description="True if the company is a strong fit for the strategic pivot product.")
    reasoning: str = Field(description="Explanation of why it fits or does not fit based on industry, size, and role.")

async def _resolve_rag_isolation(state: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """Helper to resolve index_name and user_id for the current request."""
    index_name = state.get("pinecone_index_name")
    user_linkedin = state.get("user_linkedin_url")
    user_id = state.get("user_id")
    
    is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"
    
    # If we have index_name and user_id already, we are golden
    if index_name and user_id:
        return index_name, user_id
    
    # Otherwise, try to resolve from database
    async with SessionLocal() as db:
        from db.models import OrganizationSettings, Profile
        from sqlalchemy import select, or_
        from uuid import UUID
        
        # 1. Resolve via user_linkedin_url
        if user_linkedin and (not index_name or not user_id):
            result = await db.execute(select(OrganizationSettings).where(OrganizationSettings.user_linkedin_url == user_linkedin))
            settings = result.scalars().first()
            if settings:
                index_name = index_name or settings.pinecone_index_name
                user_id = user_id or (str(settings.owner_id) if settings.owner_id else None)
                if not index_name and is_trial and settings.organization_id:
                    index_name = f"tr-{settings.organization_id}"
        
        # 2. Resolve via user_id
        if user_id and (not index_name or not user_linkedin):
            u_id = UUID(str(user_id)) if isinstance(user_id, str) and "-" in str(user_id) else user_id
            if isinstance(u_id, (UUID, str)):
                 # Try OrganizationSettings first (owner_id)
                 result = await db.execute(select(OrganizationSettings).where(OrganizationSettings.owner_id == u_id))
                 settings = result.scalars().first()
                 if settings:
                     index_name = index_name or settings.pinecone_index_name
                     if not index_name and is_trial and settings.organization_id:
                         index_name = f"tr-{settings.organization_id}"
                         
                 # Try Profile to find organization_id (for trial derivation)
                 if not index_name and is_trial:
                     res_prof = await db.execute(select(Profile.organization_id).where(Profile.id == u_id))
                     org_id = res_prof.scalar_one_or_none()
                     if org_id:
                         index_name = f"tr-{org_id}"
    
    if is_trial and not index_name:
        logger.error(f"CRITICAL RAG ISOLATION FAILURE: Could not resolve index_name. State: user_id={user_id}, user_linkedin={user_linkedin}, state_index={state.get('pinecone_index_name')}")
    else:
        logger.info(f"RAG Isolation Resolved: index_name={index_name}, user_id={user_id}")

    return index_name, user_id

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
    
    # Resolve isolation context
    index_name, user_id = await _resolve_rag_isolation(state)
    is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"
    
    if not index_name and is_trial:
        logger.error(f"RAG Isolation Debug: FAILED to resolve index_name in TRIAL_MODE for user_linkedin: {state.get('user_linkedin_url')}")

    ks = KnowledgeService(index_name=index_name)
    qualification_context = ks.retrieve_context(
        query=f"{product_name} ICP qualification criteria, target industries, and ideal roles",
        namespace="playbooks",
        k=3,
        user_id=user_id,
        index_name=index_name
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

def create_strategic_rag_agent(tools: List[Any]):
    """
    Creates an autonomous researcher agent with specialized sales intelligence skills.
    """
    llm = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a Senior Strategic Research Agent at {selling_company_name}. 
        Your mission is to find the MOST AUTHENTIC evidence and solutions for a given prospect's pain points.
        
        ### YOUR PORTFOLIO:
        {selling_products_list}
        
        ### BUSINESS MODEL: {business_model}
        
        ### YOUR WORKFLOW:
        1. **Analyze Pain**: Understand the prospect's industry and challenges.
        2. **Search Discovery**: Use `search_intelligence_base` to find relevant internal playbooks.
        3. **Verify Fit**: Use `verify_solution_feasibility` (passing the product's description from YOUR PORTFOLIO) to ensure it's a valid fit for a {business_model} firm.
        4. **ROI Proofing**: Use `get_roi_proof_points` to find specific metrics or "Proof of Expertise."
        5. **Synthesize**: Combine all evidence into a definitive Strategic Briefing categorized by your model.
        
        Be precise. Never guess. Use only the information retrieved via your skills."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

async def strategic_rag_researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node that performs agentic RAG to find the best solutions.
    """
    pain_points = state.get("target_pain_points", {})
    website_analysis = state.get("website_analysis", {})
    lead_data = state.get("lead_extracted_data", {})
    
    # Core Metadata for RAG
    lead_persona = lead_data.get("job_title") or state.get("job_title") or "Stakeholder"
    website_industry = website_analysis.get("industry")
    enriched_industry = state.get("company_metadata", {}).get("industry")
    lead_industry = state.get("industry") or website_industry or enriched_industry or "Technology"
    
    company_desc = website_analysis.get("summary", "Unknown")
    selling_profile = state.get("selling_company_profile")
    
    selling_company_name = getattr(selling_profile, "company_name", "Innovize AI") if selling_profile else "Innovize AI"
    business_model = getattr(selling_profile, 'business_model', 'product') if selling_profile else 'product'
    
    # Resolve isolation context
    index_name, user_id = await _resolve_rag_isolation(state)
    is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"

    ks = KnowledgeService(index_name=index_name)
    
    # --- RAG Discovery: Broad Semantic Anchoring ---
    # We focus on retrieving the CORE of the primary playbooks first.
    # This "anchors" the agent's knowledge in the product's actual capabilities,
    # solving the "missing detail" issue by providing the source of truth directly.
    
    qualified_products = []
    combined_anchor_context = ""
    pivot_fit_names = []
    
    if selling_profile and selling_profile.products:
        # Step 1: Strategic Selection (Pivot Priority)
        # We first check for a "Hero Product" (Pivot). If one fits, we FOCUS entirely on it.
        # Helper to get effective targets with ICP fallback
        def get_effective_targets(product):
            roles = getattr(product, "target_roles", [])
            industries = getattr(product, "target_industries", [])
            
            # Get Ideal Profile from state
            ip = state.get("ideal_profile")
            if not ip:
                return roles, industries
                
            # Helper for safe access (dict or object)
            def safe_get(obj, key, default=None):
                if hasattr(obj, key):
                    return getattr(obj, key)
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return default

            # Fallback to Global ICP if product-specific filters are missing
            if not roles:
                icp_roles = safe_get(ip, "job_title", [])
                roles = [icp_roles] if isinstance(icp_roles, str) else icp_roles
            
            if not industries:
                icp_industries = safe_get(ip, "industry", [])
                industries = [icp_industries] if isinstance(icp_industries, str) else icp_industries
                
            return roles, industries

        # Pass 1: Check Pivots
        fitting_pivots = []
        for product in [p for p in selling_profile.products if getattr(p, "is_strategic_pivot", False)]:
            target_roles, target_industries = get_effective_targets(product)
            
            # Strict Fit Check for Pivot
            fit_check = await verify_strict_fit(
                state, 
                product.name, 
                target_roles, 
                target_industries
            )
            
            if fit_check.is_fit:
                logger.info(f"Confirmed Fit for Pivot: {product.name}. Reason: {fit_check.reasoning}")
                fitting_pivots.append(product)
                pivot_fit_names.append(product.name)
        
        # Pass 2: Qualified Product Collection
        if fitting_pivots:
            # If we have pivot winners, ONLY research those products.
            qualified_products = fitting_pivots
        else:
            # Fallback: Check all other products
            for product in [p for p in selling_profile.products if not getattr(p, "is_strategic_pivot", False)]:
                target_roles, target_industries = get_effective_targets(product)
                
                # We only check fit if there are ANY roles/industries to check against
                if target_roles or target_industries:
                    fit_check = await verify_strict_fit(
                        state, 
                        product.name, 
                        target_roles, 
                        target_industries
                    )
                    
                    if not fit_check.is_fit:
                        logger.info(f"Rejected Product: {product.name}. Reason: {fit_check.reasoning}")
                        continue
                    
                    logger.info(f"Confirmed Fit for Product: {product.name}. Reason: {fit_check.reasoning}")
                
                qualified_products.append(product)

        # Step 2: Multi-Vector Retrieval for Qualified Products
        research_solution_pool = []
        
        for product in qualified_products:
            logger.info(f"Surgically researching product: {product.name}")
            
            # Extract Industry and Persona context for the query (Better alignment with Knowledge Base)
            context_string = f"in the {lead_industry} industry for a {lead_persona} role"
            
            # Sub-Anchor 1: Technical & ROI (The "What")
            tech_query = f"Core value proposition, key features, and ROI metrics of {product.name}"
            
            # Sub-Anchor 2: Narrative & Outreach (The "How")
            narrative_query = f"Outreach examples, messaging templates, and strategic hooks for {product.name}"
            
            # Sub-Anchor 3: Collateral & Proof (The "Evidence")
            collateral_query = f"Case studies, success stories, and proof points of {product.name}"
            
            # Sub-Anchor 4: Objections & Friction (The "Challenges")
            objections_query = f"Common objections, competitive friction, and risks for {product.name}"
            
            relevant_files = getattr(product, "attached_playbooks", []) + getattr(product, "attached_case_studies", [])
            if not relevant_files:
                relevant_files = getattr(product, "relevant_files", [])
            
            tech_intel = ""
            narrative_intel = ""
            collateral_intel = ""
            objections_intel = ""
            
            if relevant_files:
                index_name = state.get("pinecone_index_name")
                user_id = state.get("user_id")
                # Prepare selective filters for metadata-driven retrieval (Scoped to Case Studies)
                selective_filters = {"case-studies": {"industry": lead_industry}}
                
                # Tech/ROI Fetch (Broad query, selective filter)
                tech_intel = ks.retrieve_from_files(relevant_files, tech_query, k=5, user_id=user_id, index_name=index_name, selective_filters=selective_filters)
                
                # Narrative Fetch
                narrative_intel = ks.retrieve_from_files(relevant_files, narrative_query, k=6, user_id=user_id, index_name=index_name, selective_filters=selective_filters)
 
                # Collateral/Proof Fetch
                collateral_intel = ks.retrieve_from_files(relevant_files, collateral_query, k=5, user_id=user_id, index_name=index_name, selective_filters=selective_filters)
                
                # Objections Fetch
                objections_intel = ks.retrieve_from_files(relevant_files, objections_query, k=4, user_id=user_id, index_name=index_name, selective_filters=selective_filters)

            product_entry = {
                "product_name": product.name,
                "technical_intel": tech_intel,
                "narrative_intel": narrative_intel,
                "collateral_intel": collateral_intel,
                "objections": objections_intel,
                "attached_playbooks": getattr(product, "attached_playbooks", []),
                "attached_case_studies": getattr(product, "attached_case_studies", [])
            }
            research_solution_pool.append(product_entry)

    return {
        "research_solution_pool": research_solution_pool,
        "is_strategic_pivot_fit": len(pivot_fit_names) > 0,
        "pivot_product_names": pivot_fit_names
    }
