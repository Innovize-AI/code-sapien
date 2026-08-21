import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_generic_webhook():
    payload = {
        "email": "test-lead@example.com",
        "linkedin_url": "https://www.linkedin.com/in/williamhgates",
        "job_title": "Co-founder",
        "use_case": "Interested in sales automation"
    }
    
    print(f"Sending mock lead to {BASE_URL}/api/webhooks/generic...")
    try:
        response = requests.post(f"{BASE_URL}/api/webhooks/generic", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Success! Submission ID: {data.get('submission_id')}")
        return data.get('submission_id')
    except Exception as e:
        print(f"Failed to send webhook: {e}")
        return None

if __name__ == "__main__":
    # Ensure backend is running before this
    submission_id = test_generic_webhook()
    if submission_id:
        print("Webhook processed. Check your Dashboard to see the new report generating.")
