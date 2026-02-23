import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "sales-research/backend"))

from agents.linkedin_agent import batch_classify_profiles_async

load_dotenv()

async def verify_classification():
    profiles = [
        {
            "id": "https://www.linkedin.com/in/test-interested",
            "headline": "Founder at Stealth Startup",
            "comment": "This looks amazing, how can I get a demo?",
            "source_post": "Introducing our new AI Sales Agent."
        },
        {
            "id": "https://www.linkedin.com/in/test-pain",
            "headline": "VP of Sales at GrowthCo",
            "comment": "We are struggling so much with manual research right now. Our SDRs spend hours on LinkedIn.",
            "source_post": "Why manual sales research is dead."
        },
        {
            "id": "https://www.linkedin.com/in/test-competitor",
            "headline": "CEO at RivalAI",
            "comment": "Nice post, we have a similar solution.",
            "source_post": "How Innovize AI is transforming lead discovery."
        },
        {
            "id": "https://www.linkedin.com/in/test-poster",
            "headline": "GTM Leader at ScaleUp",
            "comment": "Posted about keywords: Why our sales team is moving to agentic workflows to handle research...",
            "source_post": "Why our sales team is moving to agentic workflows to handle research..."
        }
    ]
    
    print("Starting batch classification verification...")
    results = await batch_classify_profiles_async(profiles)
    
    print("\nResults:")
    for profile_id, data in results.items():
        print(f"\nProfile: {profile_id}")
        print(f"  Intent: {data.get('intent')}")
        print(f"  Sentiment: {data.get('sentiment')}")
        print(f"  Is Fit: {data.get('is_fit')}")
        print(f"  Reasoning: {data.get('reasoning')}")

if __name__ == "__main__":
    if not os.getenv("RAPID_API_KEY"):
        print("Error: RAPID_API_KEY not found in .env")
        sys.exit(1)
    
    asyncio.run(verify_classification())
