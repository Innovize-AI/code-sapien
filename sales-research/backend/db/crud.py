import json
import datetime
from typing import Iterable, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_, func, text
from sqlalchemy.dialects.postgresql import insert, JSONB
from sqlalchemy import Table
from db.models import ResearchReport, CompetitorAnalysis, Competitor, IdentifiedProfile, Activity, OrganizationSettings
from db.schemas import ResearchReportCreate

def _safe_deserialize(val):
    if val and isinstance(val, str) and val.strip().startswith(('{', '[')):
        try:
            return json.loads(val)
        except:
            return val
    return val

def _safe_json_load(val, default):
    if not val:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except:
        return default

def _report_to_dict(report):
    """Helper to convert ResearchReport model to final_state dictionary."""
    return {
        "id": str(report.id),
        "linkedin_url": report.linkedin_url,
        "email_id": report.email_id,
        "website": report.website,
        "sales_research_report": _safe_deserialize(report.sales_research_report),
        "lead_score_analysis": _safe_deserialize(report.lead_score_analysis),
        "user_profile_analysis": _safe_deserialize(report.user_profile_analysis),
        "website_analysis": _safe_deserialize(report.website_analysis),
        "cso_strategic_briefing": _safe_deserialize(report.cso_strategic_briefing),
        "fullname": report.fullname,
        "profile_picture_url": report.profile_picture_url,
        "company_name": report.company_name,
        "company_description": report.company_description,
        "company_industries": _safe_json_load(report.company_industries, []),

        "lead_score": report.lead_score,
        "email_history": _safe_json_load(report.email_history, []),
        "intent_analysis": _safe_json_load(report.intent_analysis, {}),
        "extra_metadata": _safe_json_load(report.extra_metadata, {}),
        
        # Modular Nodules
        "viability_analysis": _safe_deserialize(report.viability_analysis),
        "target_pain_points": _safe_deserialize(report.target_pain_points),
        "strategic_solutions": _safe_deserialize(report.strategic_solutions),
        "personalized_outreach": _safe_json_load(report.personalized_outreach, {}),
        "follow_up_strategy": _safe_deserialize(report.follow_up_strategy),
        "buyer_journey_analysis": _safe_json_load(report.buyer_journey_analysis, {}),
        "meeting_notes": report.meeting_notes,
        
        # LinkedIn Subgraph Results
        "post_engagements": _safe_json_load(report.post_engagements, []),
        "company_news": _safe_json_load(report.company_news, []),
        "hiring_data": _safe_json_load(report.hiring_data, []),
        "company_stats": _safe_json_load(report.company_stats, {}),
        "lead_li_urn": report.lead_li_urn,
        "lead_company_linkedin_url": report.lead_company_linkedin_url
    }

async def batch_upsert(
    session: AsyncSession,
    table: Table,
    rows: Sequence[dict],
    conflict_cols: Sequence[str],
    update_cols: Sequence[str] | None = None,
    chunk_size: int = 1000,
):
    if not rows:
        return []

    if update_cols is None:
        update_cols = [c.name for c in table.columns if c.name not in conflict_cols]

    results = []
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]

        stmt = insert(table).values(chunk)

        update_map = {col: getattr(stmt.excluded, col) for col in update_cols}

        stmt = (
            stmt.on_conflict_do_update(
                index_elements=list(conflict_cols),
                set_=update_map,
            )
            .returning(*table.columns)
        )

        res = await session.execute(stmt)
        results.extend(res.mappings().all())

    return results

async def batch_upsert_identified_profiles(db: AsyncSession, leads: list[dict]):
    """
    leads: List of dicts with keys: linkedin_url, name, comment, source_post, source_post_url, competitor
    """
    if not leads:
        return []

    # 1. Aggregate the incoming batch in memory by LinkedIn URL
    batch_map = {}
    for l in leads:
        url = l.get("linkedin_url")
        if not url: continue
        
        # Helper for URL normalization (strip query and trailing slash)
        def normalize(u):
            return u.split("?")[0].strip().strip("/") if u else ""

        # Normalize URL: remove query params, trailing slashes, strip whitespace
        url = normalize(url)
        
        if url not in batch_map:
            batch_map[url] = {
                "name": l.get("name"),
                "headline": l.get("headline"),
                "is_fit": l.get("is_fit"),
                "is_competitor": l.get("is_competitor"),
                "is_decision_maker": l.get("is_decision_maker"),
                "fit_reasoning": l.get("fit_reasoning"),
                "intent": l.get("intent"),
                "sentiment": l.get("sentiment"),
                "interactions": []
            }
        elif l.get("headline") and not batch_map[url].get("headline"):
            batch_map[url]["headline"] = l.get("headline")
            
        # Update classification if missing/False
        if l.get("is_fit"): batch_map[url]["is_fit"] = True
        if l.get("is_competitor"): batch_map[url]["is_competitor"] = True
        if l.get("is_decision_maker"): batch_map[url]["is_decision_maker"] = True
        if l.get("fit_reasoning") and not batch_map[url].get("fit_reasoning"):
            batch_map[url]["fit_reasoning"] = l.get("fit_reasoning")
        if l.get("intent"): batch_map[url]["intent"] = l.get("intent")
        if l.get("sentiment"): batch_map[url]["sentiment"] = l.get("sentiment")
        
        # Helper for URL normalization (strip query and trailing slash)
        n_source_url = normalize(l.get("source_post_url"))
        
        # Add interaction event
        batch_map[url]["interactions"].append({
            "comment": l.get("comment"),
            "source_post": l.get("source_post"),
            "source_post_url": l.get("source_post_url"), # Original URL
            "n_source_post_url": n_source_url,           # Normalized URL for matching
            "competitor": l.get("competitor")
        })

    # 2. Fetch all existing profiles in one query
    # Normalize all URLs in batch_map keys (should already be normalized, but to be sure)
    urls = [u.split("?")[0].strip().strip("/") for u in batch_map.keys()]
    query = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url.in_(urls))
    result = await db.execute(query)
    existing_profiles = {p.linkedin_url.split("?")[0].strip().strip("/"): p for p in result.scalars().all()}

    # 3. Prepare data for native batch upsert
    upsert_rows = []
    now = datetime.datetime.now(datetime.timezone.utc)
    
    print(f"DEBUG: Preparing upsert for {len(batch_map)} unique profiles")
    for url, data in batch_map.items():
        if url in existing_profiles:
            # Prepare merged data for update
            p = existing_profiles[url]
            try:
                db_comments = json.loads(p.comment_history or "[]")
            except:
                db_comments = []
            
            # Flatten comments from interactions for legacy support
            new_comments = [i["comment"] for i in data["interactions"] if i["comment"]]
            db_comments_normalized = [c.strip() for c in db_comments]
            for c in new_comments:
                if c.strip() not in db_comments_normalized:
                    db_comments.append(c)
                    db_comments_normalized.append(c.strip())

            try:
                db_sources = json.loads(p.source_posts or "[]")
            except:
                db_sources = []
            
            # Flatten sources from interactions for legacy support
            for i in data["interactions"]:
                if not i["source_post_url"]: continue
                n_s_url = i["n_source_post_url"]
                if not any(normalize(ds.get("url")) == n_s_url for ds in db_sources):
                    db_sources.append({
                        "title": i["source_post"],
                        "url": i["source_post_url"],
                        "competitor": i["competitor"]
                    })

            # Hierarchical History Merge
            try:
                db_history = json.loads(p.interaction_history or "[]")
            except:
                db_history = []

            for interaction in data["interactions"]:
                if not interaction["source_post_url"]: continue
                
                # 1. Find or create competitor entry
                comp_entry = next((item for item in db_history if item["competitor"] == interaction["competitor"]), None)
                if not comp_entry:
                    comp_entry = {"competitor": interaction["competitor"], "posts": []}
                    db_history.append(comp_entry)
                
                # 2. Find or create post entry
                n_lead_url = interaction["n_source_post_url"]
                post_entry = next((p for p in comp_entry["posts"] if normalize(p["url"]) == n_lead_url), None)
                if not post_entry:
                    post_entry = {"url": interaction["source_post_url"], "title": interaction["source_post"], "comments": []}
                    comp_entry["posts"].append(post_entry)
                
                # 3. Add ONLY the specific comment for this interaction
                if interaction["comment"] and interaction["comment"] not in post_entry["comments"]:
                    post_entry["comments"].append(interaction["comment"])
            
            upsert_rows.append({
                "id": p.id,
                "linkedin_url": url,
                "name": data["name"] or p.name,
                "headline": data.get("headline") or p.headline,
                "is_fit": data.get("is_fit") or p.is_fit,
                "is_competitor": data.get("is_competitor") or p.is_competitor,
                "is_decision_maker": data.get("is_decision_maker") or p.is_decision_maker,
                "fit_reasoning": data.get("fit_reasoning") or p.fit_reasoning,
                "intent": data.get("intent") or p.intent,
                "sentiment": data.get("sentiment") or p.sentiment,
                "comment_history": json.dumps(db_comments),
                "source_posts": json.dumps(db_sources),
                "interaction_history": json.dumps(db_history),
                "last_interaction_at": now
            })
        else:
            # Create new row
            new_history = []
            # Create new row logic mirrors update logic
            new_history = []
            for interaction in data["interactions"]:
                if not interaction["source_post_url"]: continue

                comp_entry = next((item for item in new_history if item["competitor"] == interaction["competitor"]), None)
                if not comp_entry:
                    comp_entry = {"competitor": interaction["competitor"], "posts": []}
                    new_history.append(comp_entry)
                
                n_lead_url = interaction["n_source_post_url"]
                post_entry = next((p for p in comp_entry["posts"] if normalize(p["url"]) == n_lead_url), None)
                if not post_entry:
                    post_entry = {"url": interaction["source_post_url"], "title": interaction["source_post"], "comments": []}
                    comp_entry["posts"].append(post_entry)
                
                if interaction["comment"] and interaction["comment"] not in post_entry["comments"]:
                    post_entry["comments"].append(interaction["comment"])

            # Reconstruct legacy fields
            legacy_comments = [i["comment"] for i in data["interactions"] if i["comment"]]
            legacy_sources = []
            seen_source_urls = set()
            for i in data["interactions"]:
                if i["source_post_url"] and i["n_source_post_url"] not in seen_source_urls:
                    seen_source_urls.add(i["n_source_post_url"])
                    legacy_sources.append({
                        "title": i["source_post"],
                        "url": i["source_post_url"],
                        "competitor": i["competitor"]
                    })

            upsert_rows.append({
                "linkedin_url": url,
                "name": data["name"],
                "headline": data.get("headline"),
                "is_fit": data.get("is_fit"),
                "is_competitor": data.get("is_competitor"),
                "is_decision_maker": data.get("is_decision_maker"),
                "fit_reasoning": data.get("fit_reasoning"),
                "intent": data.get("intent"),
                "sentiment": data.get("sentiment"),
                "comment_history": json.dumps(legacy_comments),
                "source_posts": json.dumps(legacy_sources),
                "interaction_history": json.dumps(new_history),
                "last_interaction_at": now
            })

    if upsert_rows:
        print(f"DEBUG: Executing batch_upsert with {len(upsert_rows)} rows")
        results = await batch_upsert(
            db,
            IdentifiedProfile.__table__,
            upsert_rows,
            conflict_cols=["linkedin_url"],
            update_cols=["name", "headline", "is_fit", "is_competitor", "is_decision_maker", "fit_reasoning", "comment_history", "source_posts", "interaction_history", "last_interaction_at"]
        )
        await db.commit()
        print(f"DEBUG: Batch upsert committed successfully. Results count: {len(results)}")
        return results
    
    return []

async def upsert_identified_profile(db: AsyncSession, profile_data: dict):
    """
    profile_data: {
        "linkedin_url": str,
        "name": str,
        "comment": str,
        "source_post": str,
        "source_post_url": str,
        "competitor": str
    }
    """
    query = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == profile_data["linkedin_url"])
    result = await db.execute(query)
    db_profile = result.scalar_one_or_none()
    
    new_comment = profile_data.get("comment")
    # Handle multiple post URLs if separated by comma (from previous backend aggregation)
    source_urls = profile_data.get("source_post_url", "").split(",") if profile_data.get("source_post_url") else []
    
    new_sources = []
    for url in source_urls:
        if url:
            new_sources.append({
                "title": profile_data.get("source_post"),
                "url": url,
                "competitor": profile_data.get("competitor")
            })

    if db_profile:
        # Update existing
        try:
            comments = json.loads(db_profile.comment_history or "[]")
        except:
            comments = []
            
        if new_comment:
            if new_comment not in comments:
                comments.append(new_comment)
        db_profile.comment_history = json.dumps(comments)
        
        try:
            sources = json.loads(db_profile.source_posts or "[]")
        except:
            sources = []
            
        for ns in new_sources:
            if not any(s.get("url") == ns["url"] for s in sources):
                sources.append(ns)
        db_profile.source_posts = json.dumps(sources)
        
        db_profile.last_interaction_at = datetime.datetime.now(datetime.timezone.utc)
        if profile_data.get("name") and not db_profile.name:
            db_profile.name = profile_data["name"]
    else:
        # Create new
        db_profile = IdentifiedProfile(
            linkedin_url=profile_data["linkedin_url"],
            name=profile_data.get("name"),
            comment_history=json.dumps([new_comment]) if new_comment else "[]",
            source_posts=json.dumps(new_sources),
            last_interaction_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(db_profile)
    
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

async def get_identified_profiles(db: AsyncSession, skip: int = 0, limit: int = 100, search_query: str = None):
    # Sort by number of touchpoints (length of source_posts array)
    # Join with ResearchReport to check if report exists
    query = select(IdentifiedProfile, ResearchReport.id.label("report_id")).outerjoin(
        ResearchReport, IdentifiedProfile.linkedin_url == ResearchReport.linkedin_url
    )
    
    if search_query:
        search = f"%{search_query}%"
        query = query.where(
            or_(
                IdentifiedProfile.name.ilike(search),
                IdentifiedProfile.headline.ilike(search),
                IdentifiedProfile.fit_reasoning.ilike(search),
                IdentifiedProfile.intent.ilike(search)
            )
        )
        
    query = query.order_by(
        desc(func.jsonb_array_length(func.cast(func.coalesce(IdentifiedProfile.source_posts, '[]'), JSONB))),
        desc(IdentifiedProfile.last_interaction_at)
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Process results to attach latest_report_id
    profiles = []
    for profile, report_id in rows:
        # profile is an IdentifiedProfile ORM object
        # We can dynamically attach the attribute or convert to dict if using Pydantic from_attributes
        profile_data = profile
        # Use setattr to attach the transient attribute for Pydantic to pick up
        setattr(profile_data, "latest_report_id", report_id)
        profiles.append(profile_data)
        
    return profiles

async def count_identified_profiles(db: AsyncSession, search_query: str = None):
    query = select(func.count()).select_from(IdentifiedProfile)
    if search_query:
        search = f"%{search_query}%"
        query = query.where(
            or_(
                IdentifiedProfile.name.ilike(search),
                IdentifiedProfile.headline.ilike(search),
                IdentifiedProfile.fit_reasoning.ilike(search),
                IdentifiedProfile.intent.ilike(search)
            )
        )
    result = await db.execute(query)
    return result.scalar()

async def save_report(db: AsyncSession, report_data: ResearchReportCreate):
    db_report = ResearchReport(**report_data.model_dump())
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report

async def get_report_by_email_or_linkedin(db: AsyncSession, email_id: str = None, linkedin_url: str = None):
    if not email_id and not linkedin_url:
        return None
    
    conditions = []
    if email_id:
        conditions.append(ResearchReport.email_id == email_id)
    if linkedin_url:
        conditions.append(ResearchReport.linkedin_url == linkedin_url)
        
    query = select(ResearchReport).where(or_(*conditions)).order_by(desc(ResearchReport.created_at)).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_history(db: AsyncSession, skip: int = 0, limit: int = 100):
    query = select(ResearchReport).order_by(desc(ResearchReport.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_report(db: AsyncSession, report_id: str):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def update_report_outreach(db: AsyncSession, report_id: str, outreach_data: dict):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        db_report.personalized_outreach = json.dumps(outreach_data)
        await db.commit()
        await db.refresh(db_report)
        return db_report
    return None

async def update_report_cso_outreach(db: AsyncSession, report_id: str, cso_data: dict):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        try:
            current_cso = json.loads(db_report.cso_strategic_briefing) if db_report.cso_strategic_briefing else {}
            if 'refined_linkedin_message' in cso_data:
                current_cso['refined_linkedin_message'] = cso_data['refined_linkedin_message']
            if 'refined_email_body' in cso_data:
                current_cso['refined_email_body'] = cso_data['refined_email_body']
            
            db_report.cso_strategic_briefing = json.dumps(current_cso)
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            print(f"Error updating CSO outreach: {e}")
            return None
    return None

async def update_report_intent_email(db: AsyncSession, report_id: str, email_text: str):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        try:
            intent_data = json.loads(db_report.intent_analysis) if db_report.intent_analysis else {}
            intent_data['recommended_email'] = email_text
            db_report.intent_analysis = json.dumps(intent_data)
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            print(f"Error updating intent email: {e}")
            return None
    return None

async def save_lead_submission(db: AsyncSession, submission: ResearchReportCreate):
    from db.models import LeadSubmission
    db_item = LeadSubmission(**submission.dict())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item
async def save_competitor_analysis(db: AsyncSession, competitor_urls: str, analysis_report: str):
    db_analysis = CompetitorAnalysis(competitor_urls=competitor_urls, analysis_report=analysis_report)
    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_analysis)
    return db_analysis

async def get_competitor_analyses(db: AsyncSession, skip: int = 0, limit: int = 100):
    query = select(CompetitorAnalysis).order_by(desc(CompetitorAnalysis.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def create_competitor(db: AsyncSession, competitor_data: dict):
    db_competitor = Competitor(**competitor_data)
    db.add(db_competitor)
    await db.commit()
    await db.refresh(db_competitor)
    return db_competitor

async def get_competitors(db: AsyncSession):
    query = select(Competitor).order_by(desc(Competitor.created_at))
    result = await db.execute(query)
    return result.scalars().all()

async def delete_competitor(db: AsyncSession, competitor_id: str):
    query = select(Competitor).where(Competitor.id == competitor_id)
    result = await db.execute(query)
    competitor = result.scalar_one_or_none()
    if competitor:
        await db.delete(competitor)
        await db.commit()
        return True
    return False

async def create_activity(db: AsyncSession, type: str, title: str, description: str = None, metadata_json: str = None, intent: str = None, sentiment: str = None):
    activity = Activity(
        type=type,
        title=title,
        description=description,
        metadata_json=metadata_json,
        intent=intent,
        sentiment=sentiment
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity

async def get_activities(db: AsyncSession, limit: int = 50):
    result = await db.execute(select(Activity).order_by(desc(Activity.created_at)).limit(limit))
    return result.scalars().all()

async def get_org_settings(db: AsyncSession):
    result = await db.execute(select(OrganizationSettings).limit(1))
    return result.scalars().first()
