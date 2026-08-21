import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge_service import KnowledgeService

async def sync_knowledge_base():
    load_dotenv()

    # Initialize Service
    service = KnowledgeService(index_name="glial-index")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(script_dir, ".."))

    # Directories to auto-classify and ingest (namespace resolved by classifier)
    scan_dirs = [
        os.path.join(backend_dir, "knowledge_base", "playbooks"),
        os.path.join(backend_dir, "knowledge_base", "solutions"),
        os.path.join(backend_dir, "knowledge_base", "case-studies"),
    ]

    # Also include legacy market_validation directory if present
    legacy_dir = os.path.abspath(os.path.join(backend_dir, "..", "..", "market_validation", "innovize-ai"))
    if os.path.exists(legacy_dir):
        scan_dirs.append(legacy_dir)

    all_files: list[tuple[str, str]] = []
    for d in scan_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".md"):
                    all_files.append((os.path.join(d, f), d))
        else:
            print(f"⚠️ Directory not found, skipping: {d}")

    print(f"🚀 Starting Metadata-Driven Sync — {len(all_files)} files found.")

    for i, (path, parent_dir) in enumerate(all_files):
        filename = os.path.basename(path)
        print(f"[{i+1}/{len(all_files)}] ⚖️ Classifying and Ingesting: {filename}...")

        try:
            # Let the classifier determine namespace + metadata automatically
            result = await service.ingest_markdown_file(path)
            print(f"   ✅ Success: {result['chunks']} chunks -> [{result['namespace']}]")
            print(f"   📊 Metadata: Industry={result['metadata'].get('industry')}, Product={result['metadata'].get('product')}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    print("\n🎉 Knowledge Base Metadata Sync Complete.")

if __name__ == "__main__":
    asyncio.run(sync_knowledge_base())
