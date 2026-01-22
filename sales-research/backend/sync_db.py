
import asyncio
from sqlalchemy import text, inspect
from db.database import engine
from db.models import Base

async def sync_db():
    print("Starting database sync...")
    async with engine.connect() as conn:
        inspector = await asyncio.get_event_loop().run_in_executor(None, inspect, engine)
        
        # 1. Sync ResearchReport table
        print("Checking research_reports table...")
        cols = [c['name'] for c in await conn.run_sync(inspector.get_columns, "research_reports")]
        
        research_cols_to_add = {
            "extra_metadata": "TEXT",
            "post_engagements": "TEXT",
            "company_news": "TEXT",
            "hiring_data": "TEXT",
            "recent_posts": "TEXT",
            "viability_analysis": "TEXT",
            "target_pain_points": "TEXT",
            "strategic_solutions": "TEXT",
            "personalized_outreach": "TEXT"
        }

        for col, col_type in research_cols_to_add.items():
            if col not in cols:
                try:
                    await conn.execute(text(f"ALTER TABLE research_reports ADD COLUMN {col} {col_type}"))
                    print(f"Added {col} to research_reports")
                except Exception as e:
                    print(f"Failed to add {col} to research_reports: {e}")
        
        # 2. Sync OrganizationSettings table
        print("Checking organization_settings table...")
        cols = [c['name'] for c in await conn.run_sync(inspector.get_columns, "organization_settings")]
        
        to_add = {
            "user_linkedin_url": "TEXT",
            "company_linkedin_url": "TEXT",
            "email_config": "TEXT",
            "crm_config": "TEXT",
            "integrations_config": "TEXT",
            "onboarding_complete": "INTEGER DEFAULT 0",
            "kit_api_key": "VARCHAR",
            "kit_api_secret": "VARCHAR"
        }
        
        for col, col_type in to_add.items():
            if col not in cols:
                try:
                    await conn.execute(text(f"ALTER TABLE organization_settings ADD COLUMN {col} {col_type}"))
                    print(f"Added {col} to organization_settings")
                except Exception as e:
                    print(f"Failed to add {col}: {e}")

        # 3. Create LeadSubmission table if missing
        print("Checking lead_submissions table...")
        tables = await conn.run_sync(inspector.get_table_names)
        if "lead_submissions" not in tables:
            print("Creating lead_submissions table...")
            # We can use the model directly to create the table
            await conn.run_sync(Base.metadata.create_all, tables=[Base.metadata.tables['lead_submissions']])
            print("Created lead_submissions table")
        
        await conn.commit()
    print("Database sync complete.")

if __name__ == "__main__":
    asyncio.run(sync_db())
