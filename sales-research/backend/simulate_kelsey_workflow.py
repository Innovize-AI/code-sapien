import asyncio
import json
from sqlalchemy import select, delete
from db.database import SessionLocal
from db.models import IdentifiedProfile, ResearchReport, Company, Activity
from db.crud import batch_upsert_identified_profiles
from services.classification_service import run_classification_and_update

# CONFIGURATION
TARGET_NAME_PATTERN = "%Kelsey%"

async def simulate_kelsey_workflow():
    print(f"🚀 Starting Kelsey Workflow Simulation (Pattern: {TARGET_NAME_PATTERN})")
    
    async with SessionLocal() as db:
        # 1. EXTRACT existing discovery data
        print("🔍 Extracting existing discovery data from Supabase...")
        stmt = select(IdentifiedProfile).where(IdentifiedProfile.name.ilike(TARGET_NAME_PATTERN))
        result = await db.execute(stmt)
        profiles = result.scalars().all()
        
        if not profiles:
            print("⚠️ No existing profiles found. Injecting mock Kelsey lead for simulation.")
            target_url = "https://www.linkedin.com/in/kelsey-witt-2908a489/"
            raw_leads = [{
                "linkedin_url": target_url,
                "name": "Kelsey Witt",
                "headline": "Director of Project Management at Smartsheet",
                "comment": "Searching for a new AI partner for project management automation. We need a demo ASAP and want to discuss pricing for a team of 50. This is a high priority for our Q3 planning.",
                "source_post": "Solving Project Complexity with AI",
                "source_post_url": "https://www.linkedin.com/posts/innovize-ai_project-mgmt",
                "competitor": "Smartsheet"
            }]
        else:
            p = profiles[0] # Take the first match
            target_url = p.linkedin_url
            print(f"  Found Profile: {p.name} ({target_url})")

            # Reconstruct raw leads from interaction history or comment history
            try:
                # Try to get the latest comment and source post
                history = json.loads(p.interaction_history or "[]")
                raw_leads = []
                if history:
                    for comp in history:
                        for post in comp.get("posts", []):
                            for comment in post.get("comments", []):
                                raw_leads.append({
                                    "linkedin_url": target_url,
                                    "name": p.name,
                                    "headline": p.headline,
                                    "comment": comment,
                                    "source_post": post.get("title"),
                                    "source_post_url": post.get("url"),
                                    "competitor": comp.get("competitor")
                                })
                
                # Fallback to legacy fields if history is empty
                if not raw_leads:
                    comments = json.loads(p.comment_history or "[]")
                    sources = json.loads(p.source_posts or "[]")
                    latest_comment = comments[0] if comments else "No comment found"
                    latest_source = sources[0] if sources else {"title": "Unknown", "url": None, "competitor": "Unknown"}
                    
                    raw_leads.append({
                        "linkedin_url": target_url,
                        "name": p.name,
                        "headline": p.headline,
                        "comment": latest_comment,
                        "source_post": latest_source.get("title"),
                        "source_post_url": latest_source.get("url"),
                        "competitor": latest_source.get("competitor")
                    })
            except Exception as e:
                print(f"  ⚠️ Error parsing existing data: {e}")
                return

        print(f"  Extracted {len(raw_leads)} interaction(s) for simulation.")

        # --- CORRECT DELETION ORDER FOR FK CONSTRAINTS ---
        
        # 1. Delete Research Reports (uses linkedin_url, not profile_id)
        await db.execute(delete(ResearchReport).where(ResearchReport.linkedin_url == target_url))
        
        # 2. Delete Profile (referenced to company)
        await db.execute(delete(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == target_url))
        
        # 3. Delete Company (only after profiles are gone)
        await db.execute(delete(Company).where(Company.linkedin_url == "https://www.linkedin.com/company/smartsheet/"))
        
        # 4. Delete Activities
        await db.execute(delete(Activity).where(Activity.metadata_json.like(f"%{target_url}%")))
        
        await db.commit()
        print("  Cleanup complete (Reports -> Profiles -> Companies -> Activities).")

        # 3. STEP 1: UPSERT PROFILES (Simulating task_service.py discovery save)
        print("💾 Step 1: Upserting raw discovered profiles...")
        # Force classification signals to be empty to ensure background task picks them up
        for l in raw_leads:
            l["fit_reasoning"] = None
            l["is_fit"] = False
            l["intent"] = "curious"
        
        await batch_upsert_identified_profiles(db, raw_leads)
        await db.commit() 
        print(f"  Raw profiles saved for {len(raw_leads)} interactions.")

        # 4. STEP 2: CLASSIFY & ENRICH (Simulating background AI task)
        print("🤖 Step 2: Triggering AI Classification & Apollo Enrichment...")
        # This function handles its own session management internally
        try:
            await run_classification_and_update(raw_leads)
            print("  ✅ Classification response received from pipeline.")
        except Exception as ce:
            print(f"  ❌ ERROR in classification pipeline: {ce}")

    print("\n✅ Simulation cycle finished!")
    async with SessionLocal() as check_db:
        from db.crud import normalize_linkedin_url
        norm_url = normalize_linkedin_url(target_url)
        final_stmt = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == norm_url)
        final_res = await check_db.execute(final_stmt)
        final_p = final_res.scalar_one_or_none()
        if final_p:
            print(f"  Final Profile Registry: {final_p.name}")
            print(f"  Final Fit: {final_p.is_fit}")
            print(f"  Final Reasoning: {final_p.fit_reasoning[:100]}...")
            print(f"  Final Intent: {final_p.intent}")
        else:
            print("  ❌ ERROR: Profile missing after simulation.")

    print("\n🏁 Check Slack for the final 'Hot Lead' alert.")

if __name__ == "__main__":
    asyncio.run(simulate_kelsey_workflow())
