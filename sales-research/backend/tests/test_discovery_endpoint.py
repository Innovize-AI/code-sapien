import requests
import json

url = "http://localhost:8001/sales-research/discover"
payload = {
    "industry": "Artificial Intelligence",
    "job_title": "Founder",
    "location": "San Francisco"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
