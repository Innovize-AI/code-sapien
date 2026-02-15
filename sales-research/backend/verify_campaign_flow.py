import asyncio
import os
import sys
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow.state import IdealProfile, InputLeadData, SellingCompanyProfile, Product
from agents.strategy_agent import outreach_node, solution_node

async def verify_campaign_flow():
    print("Starting Campaign Flow Verification...")
    
    # Mock Data
    pivot_product = "Glial"
    
    # Mock State
    start_state = {
        "company_name": "Acme Corp",
        "company_description": "A large logistics company facing efficiency issues.",
        "target_pain_points": "- High operational costs in document processing.\n- Slow sales cycles due to manual research.",
        "selling_company_profile": SellingCompanyProfile(
            name="Innovize AI",
            description="AI Automation Agency",
            products=[
                Product(name="Glial", description="Revenue Intelligence", target_pain_points=["Sales"], is_strategic_pivot=True, target_roles=["Sales"], rag_context="glial.md")
            ]
        ),
        "lead_segment": "POTENTIAL_CLIENT",
        "strategic_rag_briefing": "Glial helps sales teams automate research. Case study: 40% reduction in prep time for Logistics firms.",
        "is_strategic_pivot_fit": True,
        "pivot_product_name": pivot_product
    }
    
    print("\n--- Running Outreach Node with Pivot Fit = True ---")
    try:
        result = outreach_node(start_state)
        
        print("\n--- Result ---")
        variants = result.get("campaign_outreach_variants", [])
        print(f"Generated Variants Count: {len(variants)}")
        
        for i, v in enumerate(variants):
            print(f"\nVariant {i+1}: {v.get('variant_name')}")
            print(f"Hook: {v.get('hook')}")
            
        if len(variants) >= 2:
            print("\nSUCCESS: Multiple variants generated.")
        else:
            print("\nWARNING: Less than 2 variants generated.")
            
        print("\nLegacy Outreach (Backward Compat):")
        print(json.dumps(result.get("personalized_outreach"), indent=2))
        
    except Exception as e:
        print(f"\nError executing outreach_node: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(verify_campaign_flow())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nExecution failed: {e}")

