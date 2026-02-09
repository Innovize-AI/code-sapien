
import asyncio
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import text, inspect
from db.database import engine
from db.models import Base

async def sync_db():
    print("Starting database sync...")
    async with engine.connect() as conn:
        # 1. Sync ResearchReport table
        print("Checking research_reports table...")
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'research_reports'"))
        cols = [r[0] for r in res.fetchall()]
        
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
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'organization_settings'"))
        cols = [r[0] for r in res.fetchall()]
        
        to_add = {
            "user_linkedin_url": "TEXT",
            "company_linkedin_url": "TEXT",
            "email_config": "TEXT",
            "crm_config": "TEXT",
            "integrations_config": "TEXT",
            "onboarding_complete": "INTEGER DEFAULT 0",
            "kit_api_key": "VARCHAR",
            "kit_api_secret": "VARCHAR",
            "slack_webhook_url": "TEXT"
        }
        
        for col, col_type in to_add.items():
            if col not in cols:
                try:
                    await conn.execute(text(f"ALTER TABLE organization_settings ADD COLUMN {col} {col_type}"))
                    print(f"Added {col} to organization_settings")
                except Exception as e:
                    print(f"Failed to add {col}: {e}")

        # 3. Sync Activities table
        print("Checking activities table...")
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'activities'"))
        cols = [r[0] for r in res.fetchall()]
        for col in ["intent", "sentiment"]:
            if col not in cols:
                await conn.execute(text(f"ALTER TABLE activities ADD COLUMN {col} TEXT"))
                print(f"Added {col} to activities")

        # 4. Sync IdentifiedProfile table
        print("Checking identified_profiles table...")
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'identified_profiles'"))
        cols = [r[0] for r in res.fetchall()]
        for col in ["intent", "sentiment"]:
            if col not in cols:
                await conn.execute(text(f"ALTER TABLE identified_profiles ADD COLUMN {col} TEXT"))
                print(f"Added {col} to identified_profiles")

        # 5. Create tables if missing
        print("Checking tables...")
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        existing_tables = [r[0] for r in res.fetchall()]
        
        for table_name in ["lead_submissions", "activities", "identified_profiles"]:
            if table_name not in existing_tables:
                print(f"Creating {table_name} table...")
                # Use synchronous-looking Base.metadata.create_all via run_sync
                def create_table(sync_conn):
                    Base.metadata.create_all(sync_conn, tables=[Base.metadata.tables[table_name]])
                await conn.run_sync(create_table)
                print(f"Created {table_name} table")
        
        await conn.commit()
    print("Database sync complete.")

if __name__ == "__main__":
    asyncio.run(sync_db())
