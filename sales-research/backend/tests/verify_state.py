import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()

from workflow.state import AgentState, InputLeadData, IdealProfile
from agents.report_agent import sales_research_report_generator
from routes.sales_research import _prepare_state_for_json

async def main():
    # Mock lead data
    options = InputLeadData(refresh=True)
    ideal_profile = IdealProfile(industry="Tech", company_size="10-100", job_title="CTO")
    
    state = {
        "linkedin_url": "https://linkedin.com/in/test",
        "website": "https://test.com",
        "email_id": "test@test.com",
        "input_lead_data": options,
        "ideal_profile": ideal_profile,
        "company_name": "Tech Corp",
        "company_description": "A leading AI company.",
        "company_industries": ["Software", "AI"],
        "company_stats": {"employee_count": 500},
        "user_profile_analysis": {
            "profile_summary": "John is a senior engineer interested in AI scalability.",
            "strategic_role_fit": "High fit for technical advisory.",
            "company_signals": "Growing AI focus.",
            "engagement_persona": "Thought leader.",
            "pain_point_hypothesis": "Scaling infra bottlenecks.",
            "posts_analysis": []
        },
        "website_analysis": {},
        "lead_score_analysis": {},
        "target_pain_points": {},
        "strategic_solutions": {},
        "personalized_outreach": [],
        "buyer_journey_analysis": {},
        "sales_research_report": {}
    }
    
    print("Verifying initial state types...")
    for k, v in state.items():
        if k in ["user_profile_analysis", "sales_research_report"]:
            print(f"DEBUG: {k} type: {type(v)}")
            if not isinstance(v, dict):
                print(f"ERROR: {k} should be a dict, got {type(v)}")

    print("\nRunning sales_research_report_generator...")
    result = sales_research_report_generator(state)
    
    print("\nVerifying final state after generator...")
    # Generator returns an update dict
    updated_report = result.get("sales_research_report", {})
    print(f"DEBUG: sales_research_report type in result: {type(updated_report)}")
    
    # Merge result into state to simulate graph behavior
    state.update(result)
    
    print("\nPreparing state for JSON (serialization check)...")
    json_state = _prepare_state_for_json(state)
    
    print("\nVerifying serialized output...")
    # Check if user_profile_analysis is still a dict after preparation
    upa = json_state.get("user_profile_analysis")
    print(f"DEBUG: user_profile_analysis in json_state type: {type(upa)}")
    if isinstance(upa, dict):
        print("SUCCESS: user_profile_analysis is a dict.")
    else:
        print(f"FAILURE: user_profile_analysis should be a dict, got {type(upa)}")

    print("\nFinal State Snapshot (relevant fields):")
    print(json.dumps({
        "user_profile_analysis": json_state.get("user_profile_analysis"),
        "sales_research_report": json_state.get("sales_research_report")
    }, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
