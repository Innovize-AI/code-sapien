import asyncio
import os
import sys

# Add the current directory to sys.path
sys.path.append(os.getcwd())

async def test_db():
    try:
        from db import save_report, get_history, get_report
        print("SUCCESS: Imports from db.py are working.")
        
        # Test save_report
        test_data = {
            "linkedin_url": "https://www.linkedin.com/in/test-user",
            "website": "https://example.com",
            "sales_research_report": "Test Report",
            "lead_score": 85,
            "project_urgency": 2
        }
        
        print("Testing save_report...")
        report = await save_report(test_data)
        if report and report.get("id"):
            print(f"SUCCESS: save_report created report with ID: {report['id']}")
            
            # Test get_report
            print(f"Testing get_report with ID: {report['id']}...")
            fetched_report = await get_report(report['id'])
            if fetched_report and fetched_report['id'] == report['id']:
                print("SUCCESS: get_report fetched the correct report.")
            else:
                print("FAILURE: get_report failed to fetch the correct report.")
        else:
            print("FAILURE: save_report failed to create a report.")
            
        # Test get_history
        print("Testing get_history...")
        history = await get_history()
        if history and len(history) > 0:
            print(f"SUCCESS: get_history returned {len(history)} items.")
        else:
            print("FAILURE: get_history returned no items or failed.")

    except ImportError as e:
        print(f"FAILURE: ImportError: {e}")
    except Exception as e:
        print(f"FAILURE: An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
