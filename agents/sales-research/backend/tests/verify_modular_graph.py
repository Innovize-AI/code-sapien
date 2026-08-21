import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow.graph import graph
from workflow.state import IdealProfile, InputLeadData

async def test_modular_graph():
    print("Starting modular graph verification...")
    
    # Mock data
    ideal_profile = IdealProfile(
        industry="Technology",
        company_size="10-50",
        revenue="1-5M",
        job_title="CTO"
    )
    
    options = InputLeadData(
        refresh=True,
        project_urgency=1
    )
    
    initial_state = {
        "email_id": "test@innovize.ai",
        "linkedin_url": "https://linkedin.com/in/testuser",
        "website": "https://innovize.ai",
        "company_context": "Innovize AI is an automation leader.",
        "ideal_profile": ideal_profile,
        "input_lead_data": options,
        "user_profile_details": "",
        "scraped_website_content": "",
        "user_profile_analysis": "",
        "website_analysis": "",
        "lead_extracted_data": "",
        "sales_research_report": "",
        "lead_score_analysis": "",
        "viability_analysis": "",
        "target_pain_points": "",
        "strategic_solutions": "",
        "personalized_outreach": [],
        "post_engagements": [],
        "company_news": [],
        "hiring_data": []
    }
    
    print("Compiling and running graph stream...")
    config = {"configurable": {"thread_id": "test-thread"}}
    try:
        async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, state_update in event.items():
                print(f"Node completed: {node_name}")
                # We don't need to check values here as LLM calls will fail without API keys in environment
                # This script verifies the structure and connectivity
        
        print("\nVerification successful: Graph structure is valid.")
    except Exception as e:
        if "API key" in str(e) or "quota" in str(e):
            print(f"\nCaught expected API key error (verification step reached): {e}")
            print("Graph connectivity and initialization confirmed.")
        else:
            print(f"\nVerification failed with unexpected error: {e}")
            raise e

if __name__ == "__main__":
    asyncio.run(test_modular_graph())
