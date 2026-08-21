import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("APOLLO_API_KEY")

if not api_key:
    print("No API Key found")
    exit()

url = "https://api.apollo.io/v1/mixed_people/search"
    
headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache"
}

payload = {
    "api_key": api_key,
    "page": 1,
    "per_page": 2,
    "person_titles": ["Founder"],
    "q_organization_keyword_tags": ["Software"]
}

print(f"Testing URL: {url}")
try:
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
except Exception as e:
    print(f"Exception: {e}")
