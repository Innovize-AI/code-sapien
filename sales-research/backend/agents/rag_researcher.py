from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from skills.rag_skills import RAG_SKILLS
import json

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
    
    selling_company_name = selling_profile.name if selling_profile else "Innovize AI"
    selling_products_list = "\n".join([f"- {p.name}: {p.description}" for p in selling_profile.products]) if selling_profile else "Glial, IDP, Agentic KB"

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
    
    result = await executor.ainvoke({
        "input": research_goal, 
        "chat_history": [],
        "selling_company_name": selling_company_name,
        "selling_products_list": selling_products_list
    })
    
    return {"strategic_rag_briefing": result["output"]}
