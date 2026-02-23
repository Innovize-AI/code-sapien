import os
from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

def test_pinecone():
    api_key = os.getenv("PINECONE_API_KEY")
    print(f"API Key Length: {len(api_key) if api_key else 0}")
    print(f"API Key First 5: {api_key[:5] if api_key else 'None'}")
    
    try:
        pc = Pinecone(api_key=api_key)
        indexes = pc.list_indexes()
        print("Successfully connected to Pinecone.")
        print(f"Indexes: {[i.name for i in indexes]}")
    except Exception as e:
        print(f"Failed to connect to Pinecone: {e}")

if __name__ == "__main__":
    test_pinecone()
