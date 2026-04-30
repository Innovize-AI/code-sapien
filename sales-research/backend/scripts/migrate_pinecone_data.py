import os
import sys
import asyncio
from typing import List, Optional
from pinecone import Pinecone

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "sales-research", "backend"))

def migrate_index(source_index_name: str, target_index_name: str, batch_size: int = 100):
    """
    Migrates all vectors from source_index to target_index across all namespaces.
    """
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("Error: PINECONE_API_KEY not found in environment.")
        return

    pc = Pinecone(api_key=api_key)
    
    # 1. Connect to indices
    try:
        source_index = pc.Index(source_index_name)
        target_index = pc.Index(target_index_name)
    except Exception as e:
        print(f"Error connecting to indices: {e}")
        return

    # 2. Get all namespaces from source
    source_stats = source_index.describe_index_stats()
    namespaces = list(source_stats.namespaces.keys())
    
    print(f"Found {len(namespaces)} namespaces in {source_index_name}: {namespaces}")

    for ns in namespaces:
        print(f"\n--- Migrating Namespace: '{ns}' ---")
        
        # 3. List all IDs in the namespace
        # For Serverless indices, we use list_paginated
        all_ids = []
        try:
            for ids_batch in source_index.list_paginated(namespace=ns):
                all_ids.extend(ids_batch)
        except Exception as e:
            print(f"Error listing IDs in namespace {ns}: {e}")
            # Fallback for pod-based indices if needed (though we use serverless)
            continue

        print(f"Found {len(all_ids)} vectors to migrate.")

        # 4. Fetch and Upsert in batches
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i : i + batch_size]
            
            try:
                # Fetch full vector data (including metadata and values)
                fetch_response = source_index.fetch(ids=batch_ids, namespace=ns)
                
                vectors_to_upsert = []
                for vid, vector_data in fetch_response.vectors.items():
                    vectors_to_upsert.append({
                        "id": vid,
                        "values": vector_data.values,
                        "metadata": vector_data.metadata
                    })
                
                if vectors_to_upsert:
                    target_index.upsert(vectors=vectors_to_upsert, namespace=ns)
                    print(f"  Upserted batch {i//batch_size + 1}/{(len(all_ids)-1)//batch_size + 1}")
            
            except Exception as e:
                print(f"  Error migrating batch starting at {i}: {e}")

    print("\nMigration complete!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate Pinecone data between indices.")
    parser.add_argument("--source", default="glial-index", help="Source index name")
    parser.add_argument("--target", required=True, help="Target index name (e.g. tr-org-id)")
    
    args = parser.parse_args()
    
    migrate_index(args.source, args.target)
