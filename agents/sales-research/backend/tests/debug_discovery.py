import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add current dir to path to find modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.lead_discovery import find_leads_tavily, LeadDiscoveryInput

def test_tavily():
    print("Testing Tavily Discovery...")
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("ERROR: TAVILY_API_KEY not set in .env")
        return

    input_data = LeadDiscoveryInput(
        industry="SaaS",
        job_title="CEO",
        location="Austin",
        provider="tavily"
    )
    
    try:
        leads = find_leads_tavily(input_data)
        print(f"Found {len(leads)} leads")
        for lead in leads:
            print(lead)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_tavily()
