import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge_service import KnowledgeService

async def main():
    # Load environment variables (ensure keys are present)
    load_dotenv()
    
    pinecone_key = os.getenv("PINECONE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not pinecone_key or not openai_key:
        print("❌ Error: PINECONE_API_KEY or OPENAI_API_KEY not found in environment.")
        return

    # Initialize Service
    service = KnowledgeService(index_name="glial-index")
    
    # Define files and their corresponding namespaces
    assets_to_ingest = [
        # ── Playbooks ──────────────────────────────────────────────────────────
        {
            "path": "../knowledge_base/playbooks/glial-sales-playbook.md",
            "namespace": "playbooks",
            "metadata": {"type": "sales-playbook", "product": "glial"}
        },
        {
            "path": "../knowledge_base/playbooks/outreach-templates.md",
            "namespace": "playbooks",
            "metadata": {"type": "outreach-templates", "product": "glial"}
        },
        {
            "path": "../knowledge_base/playbooks/ai-strategy-session-sop.md",
            "namespace": "playbooks",
            "metadata": {"type": "sop", "offering": "ai-transformation"}
        },
        {
            "path": "../knowledge_base/playbooks/cross-sell-playbook.md",
            "namespace": "playbooks",
            "metadata": {"type": "cross-sell-playbook", "offering": "innovize-ai"}
        },
        # ── Solutions ──────────────────────────────────────────────────────────
        {
            "path": "../knowledge_base/solutions/glial-product-overview.md",
            "namespace": "solutions",
            "metadata": {"type": "product-overview", "product": "glial"}
        },
        {
            "path": "../knowledge_base/solutions/ai-transformation-services.md",
            "namespace": "solutions",
            "metadata": {"type": "services-overview", "offering": "ai-transformation"}
        },
        # ── Case Studies ───────────────────────────────────────────────────────
        {
            "path": "../knowledge_base/case-studies/ai-transformation-results.md",
            "namespace": "case-studies",
            "metadata": {"type": "case-study", "offering": "ai-transformation"}
        },
        {
            "path": "../knowledge_base/case-studies/glial-platform-results.md",
            "namespace": "case-studies",
            "metadata": {"type": "case-study", "product": "glial"}
        },
        # ── Legacy market validation files (kept for backwards compatibility) ──
        {
            "path": "../../market_validation/innovize-ai/innovize-ai-gtm.md",
            "namespace": "solutions",
            "metadata": {"type": "gtm", "offering": "innovize-ai"}
        },
        {
            "path": "../../market_validation/innovize-ai/our-offerings.md",
            "namespace": "solutions",
            "metadata": {"type": "offerings", "offering": "innovize-ai"}
        },
    ]

    print("🚀 Starting Knowledge Ingestion...")

    for asset in assets_to_ingest:
        abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), asset["path"]))
        if os.path.exists(abs_path):
            print(f"📄 Ingesting: {asset['path']} -> Namespace: {asset['namespace']}")
            try:
                result = await service.ingest_markdown_file(abs_path, asset["namespace"], asset["metadata"])
                print(f"✅ Success: {result['chunks']} chunks ingested into {result['namespace']}.")
            except Exception as e:
                print(f"❌ Failed to ingest {asset['path']}: {e}")
        else:
            print(f"⚠️ Warning: File not found at {abs_path}")

    print("\n🎉 Knowledge Ingestion Complete.")

if __name__ == "__main__":
    asyncio.run(main())
