import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("DATABASE_URL")

if not url:
    print("Error: DATABASE_URL is not set in .env")
else:
    print(f"Attempting to connect to: {url.split('@')[-1]}") # Print only host part for privacy/safety
    try:
        conn = psycopg2.connect(url)
        print("Success! Connection established.")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
