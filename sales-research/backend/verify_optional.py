import asyncio
from routes.sales_research import run_single_research
from workflow.state import InputLeadData

async def verify_optional_fields():
    options = InputLeadData(
        project_urgency=2,
        lead_source="Test"
    )

    print("--- Test 1: Only Website ---")
    res1 = await run_single_research(
        linkedin_url=None,
        website="https://www.example.com",
        options=options
    )
    print(f"Result 1 keys: {res1['result'].keys()}")
    
    print("\n--- Test 2: Only LinkedIn ---")
    # Using a dummy URL that won't actually work with scraper but tests flow entry
    res2 = await run_single_research(
        linkedin_url="https://www.linkedin.com/in/dummy-user-123",
        website=None,
        options=options
    )
    print(f"Result 2 keys: {res2['result'].keys()}")

    print("\n--- Test 3: Both Missing (Should probably fail validation or return empty) ---")
    res3 = await run_single_research(
        linkedin_url=None,
        website=None,
        options=options
    )
    print(f"Result 3 keys: {res3['result'].keys()}")

if __name__ == "__main__":
    asyncio.run(verify_optional_fields())
