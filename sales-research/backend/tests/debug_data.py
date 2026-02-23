import asyncio
import json
from db import SessionLocal, get_history

async def debug_data():
    async with SessionLocal() as db:
        reports = await get_history(db, limit=5)
        for r in reports:
            print(f"Report ID: {r.id}")
            print(f"  Field: user_profile_analysis")
            print(f"    Type: {type(r.user_profile_analysis)}")
            print(f"    Value Start: {str(r.user_profile_analysis)[:100]}")
            
            print(f"  Field: strategic_solutions")
            print(f"    Type: {type(r.strategic_solutions)}")
            print(f"    Value Start: {str(r.strategic_solutions)[:100]}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(debug_data())
