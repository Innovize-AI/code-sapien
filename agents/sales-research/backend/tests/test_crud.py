import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

async def test_crud():
    try:
        from db.crud import save_report, get_history, get_report
        from db.database import SessionLocal
        from db.schemas import ResearchReportCreate
        
        print("SUCCESS: Imports are working.")
        
        async with SessionLocal() as db:
            # Test save_report
            test_data = ResearchReportCreate(
                linkedin_url="https://www.linkedin.com/in/test-new-structure",
                website="https://example.com/new",
                sales_research_report="Test Report New Structure",
                lead_score=90,
                project_urgency=1
            )
            
            print("Testing save_report...")
            report = await save_report(db, test_data)
            if report and report.id:
                print(f"SUCCESS: save_report created report with ID: {report.id}")
                
                # Test get_report
                print(f"Testing get_report with ID: {report.id}...")
                fetched_report = await get_report(db, str(report.id))
                if fetched_report and fetched_report.id == report.id:
                    print("SUCCESS: get_report fetched the correct report.")
                else:
                    print("FAILURE: get_report failed.")
            else:
                print("FAILURE: save_report failed.")
                
            # Test get_history
            print("Testing get_history...")
            history = await get_history(db)
            if history and len(history) > 0:
                print(f"SUCCESS: get_history returned {len(history)} items.")
            else:
                print("FAILURE: get_history failed.")

    except Exception as e:
        print(f"FAILURE: An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_crud())
