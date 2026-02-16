import os
import sys
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge_service import KnowledgeService

def main():
    # Load environment variables (ensure keys are present)
    load_dotenv()
    
    pinecone_key = os.getenv("PINECONE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not pinecone_key or not openai_key:
        print("❌ Error: PINECONE_API_KEY or OPENAI_API_KEY not found in environment.")
        return

    # Initialize Service
    # Index name should match your Pinecone index
    service = KnowledgeService(index_name="glial-index")
    
    # Define files and their corresponding namespaces
    assets_to_ingest = [
        {
            "path": "../../market_validation/innovize-ai/innovize-ai-gtm.md",
            "namespace": "transformation",
            "metadata": {"type": "gtm", "offering": "innovize-ai"}
        },
        {
            "path": "../../market_validation/innovize-ai/our-offerings.md",
            "namespace": "transformation",
            "metadata": {"type": "offerings", "offering": "innovize-ai"}
        }
    ]

    print("🚀 Starting Knowledge Ingestion...")

    for asset in assets_to_ingest:
        abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), asset["path"]))
        if os.path.exists(abs_path):
            print(f"📄 Ingesting: {asset['path']} -> Namespace: {asset['namespace']}")
            try:
                chunks = service.ingest_markdown_file(abs_path, asset["namespace"], asset["metadata"])
                print(f"✅ Success: {chunks} chunks ingested.")
            except Exception as e:
                print(f"❌ Failed to ingest {asset['path']}: {e}")
        else:
            print(f"⚠️ Warning: File not found at {abs_path}")

    print("\n🎉 Knowledge Ingestion Complete.")

if __name__ == "__main__":
    main()
