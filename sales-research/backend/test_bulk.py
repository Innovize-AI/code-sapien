import requests
import json

def test_bulk():
    url = "http://localhost:8000/sales-research/bulk"
    payload = {
        "leads": [
            {
                "url": "https://www.linkedin.com/in/williamhgates/",
                "website": "https://gatesnotes.com"
            },
            {
                "url": "https://www.linkedin.com/in/satyanadella/",
                "website": "https://microsoft.com"
            }
        ],
        "options": {
            "project_urgency": 2,
            "lead_source": "Test"
        }
    }
    
    print(f"Testing bulk analysis with {len(payload['leads'])} leads...")
    
    try:
        response = requests.post(url, json=payload, stream=True)
        if response.status_code != 200:
            print(f"Error: Status code {response.status_code}")
            print(response.text)
            return

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data = json.loads(decoded_line[6:])
                    print(f"Received: {data}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_bulk()
