import asyncio
import os
from dotenv import load_dotenv
from agents.linkedin_agent import discover_leads_from_competitor

load_dotenv()

async def test_lead_discovery():
    # This is a manual test script to verify the logic
    # In a real environment, you would mock the API calls
    competitor_url = "https://www.linkedin.com/in/williamhgates" # Example
    print(f"Testing lead discovery for: {competitor_url}")
    
    leads = discover_leads_from_competitor(competitor_url)
    
    print(f"Found {len(leads)} potential leads.")
    for lead in leads[:5]:
        print(f"Name: {lead['name']}")
        print(f"Comment: {lead['comment_text']}")
        print(f"LinkedIn: {lead['linkedin_url']}")
        print("-" * 20)

if __name__ == "__main__":
    if not os.getenv("RAPID_API_KEY"):
        print("RAPID_API_KEY not found in .env")
    else:
        asyncio.run(test_lead_discovery())
