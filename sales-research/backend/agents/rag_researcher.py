from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from skills.rag_skills import RAG_SKILLS
import json
from models.gemini_models import get_gemini_model
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from services.knowledge_service import KnowledgeService

# Global service instance (or instantiate within node)
knowledge_service = KnowledgeService(index_name="glial-index")

class PivotFitCheck(BaseModel):
    is_fit: bool = Field(description="True if the company is a strong fit for the strategic pivot product.")
    reasoning: str = Field(description="Explanation of why it fits or does not fit based on industry, size, and role.")

async def verify_strict_fit(state: Dict[str, Any], product_name: str, target_roles: List[str]) -> PivotFitCheck:
    """
    Verifies if the lead is a strict fit for the strategic pivot.
    1. Hard Filter: Role Match
    2. Soft Filter: Agentic Analysis of Company Fit
    """
    print(f"Verifying Strict Fit for {product_name}...")
    
    # 1. Hard Filter: Role Match
    user_details = state.get("user_profile_details", {})
    job_title = user_details.get("headline", "") or state.get("ideal_profile", {}).job_title or ""
    
    role_match = False
    if not target_roles:
        role_match = True # No specific roles defined, assume fit
    else:
        for role in target_roles:
            if role.lower() in job_title.lower():
                role_match = True
                break
    
    if not role_match:
        print(f"Role Mismatch: {job_title} not in {target_roles}")
        return PivotFitCheck(is_fit=False, reasoning=f"Lead role '{job_title}' does not match target roles for {product_name}: {target_roles}")

    # 2. Agentic Analysis (Soft Filter)
    website_analysis = state.get("website_analysis", {})
    industry = website_analysis.get("industry", "Unknown")
    company_desc = website_analysis.get("summary", "Unknown")
    company_size = website_analysis.get("company_size", "Unknown") # derived from somewhere?

    prompt = f"""
    Analyze if this company is a good fit for the product '{product_name}'.
    
    Product Context: {product_name} matches companies in specific industries (tech, logistics, finance) or sizes.
    
    Company Profile:
    - Industry: {industry}
    - Description: {company_desc}
    - Size: {company_size}
    
    Target Roles: {target_roles} (Role matched: {job_title})
    
    Is this a high-potential fit? Return boolean.
    """
    
    try:
        model = get_gemini_model(model="gemini-2.0-flash", temperature=0)
        structured_llm = model.with_structured_output(PivotFitCheck)
        messages = [
            SystemMessage(content="You are a strict qualification agent. You only approve leads that are a clear fit."),
            HumanMessage(content=prompt)
        ]
        result = await structured_llm.ainvoke(messages)
        return result
    except Exception as e:
        print(f"Error in verification: {e}")
        return PivotFitCheck(is_fit=False, reasoning=f"Error verifying fit: {e}")

def create_strategic_rag_agent():
    """
    Creates an autonomous researcher agent with specialized sales intelligence skills.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
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
    
    agent = create_openai_functions_agent(llm, RAG_SKILLS, prompt)
    return AgentExecutor(agent=agent, tools=RAG_SKILLS, verbose=True)

async def strategic_rag_researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node that performs agentic RAG to find the best solutions.
    """
    pain_points = state.get("target_pain_points", {})
    industry = state.get("website_analysis", {}).get("industry", "Unknown")
    selling_profile = state.get("selling_company_profile")
    
    selling_company_name = getattr(selling_profile, "company_name", "Innovize AI") if selling_profile else "Innovize AI"
    selling_products_list = "\n".join([f"- {p.name}: {getattr(p, 'description', '')}" for p in selling_profile.products]) if selling_profile else "Glial, IDP, Agentic KB"

    research_goal = f"""
    Find the best {selling_company_name} solutions for a prospect in the {industry} industry.
    Identified Pain Points: {json.dumps(pain_points)}
    
    Your goal is to return a 'Strategic Solution Briefing' that includes:
    1. The core product to lead with.
    2. Specific playbook snippets or case studies you found.
    3. Verified feasibility and ROI metrics.
    """
    
    executor = create_strategic_rag_agent()
    # Fill in the prompt variables via the input or by partially formatting the prompt
    # Since prompt is inside create_strategic_rag_agent, I'll update that helper.
    
    pivot_fit_result = False
    pivot_name = ""
    
    # --- Check for Strategic Pivot ---
    strategic_pivot = None
    if selling_profile:
        for p in selling_profile.products:
            if getattr(p, "is_strategic_pivot", False):
                strategic_pivot = p
                break
    
    if strategic_pivot:
        print(f"Found Strategic Pivot: {strategic_pivot.name}")
        # Perform Strict Fit Check
        fit_check = await verify_strict_fit(state, strategic_pivot.name, getattr(strategic_pivot, "target_roles", []))
        
        if fit_check.is_fit:
            print(f"Pivot Fit CONFIRMED: {fit_check.reasoning}")
            pivot_fit_result = True
            pivot_name = strategic_pivot.name
            
            # Retrieve specific context from relevant files
            relevant_files = getattr(strategic_pivot, "relevant_files", [])
            specific_context = ""
            if relevant_files:
                print(f"Retrieving context from {len(relevant_files)} relevant files: {relevant_files}")
                specific_context = knowledge_service.retrieve_from_files(relevant_files, strategic_pivot.name + " " + " ".join(pain_points.keys() if isinstance(pain_points, dict) else []), k=10)
            
            # Fallback to legacy rag_context if no specific files or empty result
            if not specific_context and getattr(strategic_pivot, "rag_context", None):
                 specific_context = f"Legacy Context Reference: {strategic_pivot.rag_context}"

            # Update Research Goal to focus on Pivot
            research_goal = f"""
            PRIMARY OBJECTIVE: Find evidence to pitch '{strategic_pivot.name}' to this prospect.
            
            Context: {strategic_pivot.description}
            Identified Pain Points: {json.dumps(pain_points)}
            
            === VERIFIED INTERNAL KNOWLEDGE (MUST USE) ===
            {specific_context}
            ==============================================
            
            Task:
            1. Synthesize the 'Verified Internal Knowledge' above to create a compelling case.
            2. Find specific case studies or ROI metrics for {strategic_pivot.name} within this context.
            3. Return a briefing specifically supporting a pitch for {strategic_pivot.name}.
            """
        else:
            print(f"Pivot Fit REJECTED: {fit_check.reasoning}")

    executor = create_strategic_rag_agent()
    # Fill in the prompt variables via the input or by partially formatting the prompt
    # Since prompt is inside create_strategic_rag_agent, I'll update that helper.
    
    result = await executor.ainvoke({
        "input": research_goal, 
        "chat_history": [],
        "selling_company_name": selling_company_name,
        "selling_products_list": selling_products_list
    })
    
    return {
        "strategic_rag_briefing": result["output"],
        "is_strategic_pivot_fit": pivot_fit_result,
        "pivot_product_name": pivot_name
    }
