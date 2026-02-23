
import requests
import sys

try:
    response = requests.get("http://localhost:8000/api/dashboard/stats")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 200:
        print("SUCCESS: Endpoint is working.")
    else:
        print("FAILURE: Endpoint returned non-200 status.")
except Exception as e:
    print(f"ERROR: Could not connect to backend. {e}")
