import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

url = "http://localhost:8001/sales-research/discover"

# Ensure API key is present for the test to be meaningful (or just test the endpoint logic handling missing key)
api_key = os.getenv("APOLLO_API_KEY")
if not api_key:
    print("WARNING: APOLLO_API_KEY not set. Test might fail or return empty.")

payload = {
    "industry": "Artificial Intelligence",
    "job_title": "Founder",
    "location": "San Francisco",
    "provider": "apollo"
}

try:
    print(f"Testing Apollo Discovery on {url}...")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
