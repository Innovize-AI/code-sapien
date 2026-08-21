import json
import logging
import os

logger = logging.getLogger(__name__)
import datetime
import difflib
from typing import Iterable, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import select, update, delete, desc, func, and_, or_, Table, text
from sqlalchemy.dialects.postgresql import insert
from db.models import ResearchReport, LeadSubmission, OrganizationSettings, CRMContext, Competitor, IdentifiedProfile, Activity, Company, Profile, CompetitorAnalysis, UserSettings, AutopilotRule, ScheduledTask
from db.schemas import ResearchReportCreate, LeadSubmissionCreate, OrganizationSettingsCreate, CompetitorCreate, IdentifiedProfileCreate, ActivityCreate, CompanyCreate
from utils.url_normalize import normalize_linkedin_url
from uuid import UUID

async def get_active_icp(db: AsyncSession, user_id: UUID | str | None = None, org_id: UUID | str | None = None) -> dict | None:
    """
    Fetches the active ICP. 
    1. If user_id is provided, checks UserSettings for a personal override.
    2. Falls back to OrganizationSettings by org_id.
    """
    # 1. Check for User Override
    if user_id:
        try:
            u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
            result = await db.execute(select(UserSettings).where(UserSettings.user_id == u_id))
            u_settings = result.scalars().first()
            if u_settings and u_settings.icp_json:
                return json.loads(u_settings.icp_json)
        except Exception as e:
            logger.warning(f"Error fetching personal ICP override: {e}")

    # 2. Fallback to Organization Settings
    query = select(OrganizationSettings)
    conditions = []
    if org_id:
        o_id = UUID(str(org_id)) if isinstance(org_id, str) else org_id
        conditions.append(OrganizationSettings.organization_id == o_id)
    if user_id:
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        conditions.append(OrganizationSettings.owner_id == u_id)
    
    if conditions:
        query = query.where(or_(*conditions))
        # Prioritize Org-linked, then Owner-linked
        query = query.order_by(desc(OrganizationSettings.organization_id), desc(OrganizationSettings.owner_id))
    else:
        # Final fallback: orphaned settings
        query = query.where(and_(OrganizationSettings.organization_id == None, OrganizationSettings.owner_id == None))
    
    result = await db.execute(query.limit(1))
    settings = result.scalars().first()
    if settings and settings.icp_json:
        try:
            return json.loads(settings.icp_json)
        except:
            return None
    return None

async def upsert_company(
    db: AsyncSession,
    company_data: dict,
    linkedin_url: str | None = None,
    domain: str | None = None
) -> Company:
    """
    Creates or updates a Company record based on linkedin_url or domain.
    If a company exists, it updates its fields.
    """
    if not linkedin_url and not domain:
        raise ValueError("Either linkedin_url or domain must be provided for upsert_company.")

    # Normalize inputs
    normalized_linkedin_url = normalize_linkedin_url(linkedin_url) if linkedin_url else None
    normalized_domain = domain.lower().strip() if domain else None

    # Try to find existing company by LinkedIn URL first
    company = None
    if normalized_linkedin_url:
        result = await db.execute(select(Company).where(Company.linkedin_url == normalized_linkedin_url))
        company = result.scalar_one_or_none()
    
    # If not found, try by domain
    if not company and normalized_domain:
        result = await db.execute(select(Company).where(Company.domain == normalized_domain))
        company = result.scalar_one_or_none()

    # Prepare data for update/create
    relevant_data = {
        **company_data,
        "updated_at": datetime.datetime.now(datetime.timezone.utc)
    }
    
    # Normalize industries to standard categories if present
    raw_industries = relevant_data.get("industries")
    if raw_industries:
        try:
            from utils.industry_mapper import normalize_industry
            if isinstance(raw_industries, list):
                raw_str = ", ".join(raw_industries)
            else:
                raw_str = str(raw_industries)
            
            # Run async normalization
            normalized = await normalize_industry(raw_str)
            relevant_data["industries"] = [normalized]
        except Exception as e:
            logger.error(f"Error normalizing company industries in upsert_company: {e}")

    # Ensure ID and created_at are never overwritten

    relevant_data.pop("id", None)
    relevant_data.pop("created_at", None)
    
    # Explicitly set normalized values if they were provided
    if normalized_linkedin_url:
        relevant_data["linkedin_url"] = normalized_linkedin_url
    if normalized_domain:
        relevant_data["domain"] = normalized_domain

    # EXPLICIT GUARD: Never save prospect email to company table
    relevant_data.pop("email", None)
    relevant_data.pop("person_email", None)

    # Handle dictionary/list fields for Text columns (JSON storage)
    for key, value in relevant_data.items():
        if isinstance(value, (dict, list)):
            relevant_data[key] = json.dumps(value)

    # Filter to only valid columns
    valid_columns = Company.__table__.columns.keys()
    final_data = {k: v for k, v in relevant_data.items() if k in valid_columns}

    if company:
        # Update existing
        for key, value in final_data.items():
            setattr(company, key, value)
    else:
        # Create new
        company = Company(**final_data)
        db.add(company)
    
    # We execute flush to get the ID back if newly created, but let caller commit
    await db.flush()
    return company

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

def _calculate_text_modification_percentage(original: str, updated: str) -> int:
    """Calculates what percentage of the text has been modified."""
    if not original:
        return 0
    if not updated:
        return 100
    
    matcher = difflib.SequenceMatcher(None, original, updated)
    # total length of matching blocks / average length of strings
    # ratio() is 2.0 * M / T where M is matches and T is total length
    # Modification is 1 - match_ratio
    match_ratio = matcher.ratio()
    modification_pct = int((1.0 - match_ratio) * 100)
    return min(100, max(0, modification_pct))

def _calculate_json_modification_percentage(original: dict, updated: dict) -> int:
    """Calculates average modification across JSON fields."""
    if not original: return 0
    if not updated: return 100
    
    total_mod = 0
    count = 0
    
    # We only care about fields that are common to both or present in original
    keys = set(original.keys()) | set(updated.keys())
    for k in keys:
        v_orig = str(original.get(k, ""))
        v_upd = str(updated.get(k, ""))
        total_mod += _calculate_text_modification_percentage(v_orig, v_upd)
        count += 1
        
    return total_mod // count if count > 0 else 0

def _report_to_dict(report, email_fallback=None):
    """Helper to convert ResearchReport model to final_state dictionary."""
    extra = _safe_json_load(report.extra_metadata, {})
    return {
        "id": str(report.id),
        "linkedin_url": report.linkedin_url,
        "email_id": report.email_id or email_fallback,
        "email_verification_status": getattr(report, "email_verification_status", None),
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
        "extra_metadata": extra,
        "strategic_rag_briefing": extra.get("strategic_rag_briefing", ""),
        
        # Modular Nodules
        "viability_analysis": _safe_deserialize(report.viability_analysis),
        "target_pain_points": _safe_deserialize(report.target_pain_points),
        "strategic_solutions": _safe_deserialize(report.strategic_solutions),
        "personalized_outreach": _safe_json_load(report.personalized_outreach, []),
        "follow_up_strategy": _safe_deserialize(report.follow_up_strategy),
        "buyer_journey_analysis": _safe_json_load(report.buyer_journey_analysis, {}),
        "meeting_notes": report.meeting_notes,
        
        # LinkedIn Subgraph Results
        "post_engagements": _safe_json_load(report.post_engagements, []),
        "company_news": _safe_json_load(report.company_news, []),
        "hiring_data": _safe_json_load(report.hiring_data, []),
        "company_stats": _safe_json_load(report.company_stats, {}),
        "lead_li_urn": report.lead_li_urn,
        "lead_company_linkedin_url": report.lead_company_linkedin_url,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        
        # Outreach Tracking
        "outreach_status": report.outreach_status,
        "outreach_started_at": report.outreach_started_at.isoformat() if report.outreach_started_at else None,
        "is_outreach_edited": report.is_outreach_edited,
        "edit_depth_percentage": report.edit_depth_percentage
    }

async def batch_upsert(
    session: AsyncSession,
    table: Table,
    rows: Sequence[dict],
    conflict_cols: Sequence[str],
    update_cols: Sequence[str] | None = None,
    chunk_size: int = 100,
):
    if not rows:
        return []

    if update_cols is None:
        update_cols = [c.name for c in table.columns if c.name not in conflict_cols]

    # VERY IMPORTANT: Sort rows by conflict columns to prevent concurrent Postgres deadlocks.
    # When multiple concurrent workers try to ON CONFLICT UPDATE the same overlapping rows
    # in different orders, Postgres will trigger a transaction deadlock or statement timeout.
    try:
        if conflict_cols:
            primary_col = conflict_cols[0]
            rows = sorted(rows, key=lambda x: str(x.get(primary_col, "")))
    except Exception as e:
        logger.warning(f"Could not sort batch upsert rows: {e}")

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

async def batch_upsert_identified_profiles(db: AsyncSession, leads: list[dict], user_id: str = None, org_id: str = None):
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
        
        # Normalize URL: remove query params, trailing slashes, strip whitespace
        url = normalize_linkedin_url(url)
        
        if url not in batch_map:
            # Preserve explicit lead_source or derive from competitor field
            lead_source = l.get("lead_source")
            if not lead_source:
                competitor = l.get("competitor", "")
                if competitor == "Apollo":
                    lead_source = "apollo"
                elif competitor and (competitor == "Keyword Search" or competitor == "Keyword" or competitor.startswith("Keyword:")):
                    lead_source = "keyword"
                else:
                    lead_source = "competitor"

            batch_map[url] = {
                "name": l.get("name"),
                "headline": l.get("headline"),
                "is_fit": l.get("is_fit"),
                "is_competitor": l.get("is_competitor"),
                "is_decision_maker": l.get("is_decision_maker"),
                "fit_reasoning": l.get("fit_reasoning"),
                "intent": l.get("intent"),
                "sentiment": l.get("sentiment"),
                "email": l.get("email"),
                "email_verification_status": l.get("email_verification_status"),
                "company_id": l.get("company_id"),
                "website": l.get("website"), # Explicitly track website
                "profile_metadata": l.get("profile_metadata") or {},
                "lead_source": lead_source,
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
        if l.get("company_id") and not batch_map[url].get("company_id"):
            batch_map[url]["company_id"] = l.get("company_id")
        
        # Merge profile_metadata if provided
        if l.get("profile_metadata"):
            if not isinstance(batch_map[url]["profile_metadata"], dict):
                batch_map[url]["profile_metadata"] = {}
            batch_map[url]["profile_metadata"].update(l.get("profile_metadata"))
        
        # Helper for URL normalization (strip query and trailing slash)
        n_source_url = normalize_linkedin_url(l.get("source_post_url"))
        
        # Add interaction event
        batch_map[url]["interactions"].append({
            "comment": l.get("comment"),
            "source_post": l.get("source_post"),
            "source_post_url": l.get("source_post_url"), # Original URL
            "n_source_post_url": n_source_url,           # Normalized URL for matching
            "competitor": l.get("competitor"),
            "normalized_linkedin_url": normalize_linkedin_url(l.get("linkedin_url"))
        })

    # 2. RESOLUTION PHASE: Resolve Apollo placeholders and Auto-Link Companies
    # 2a. Apollo Placeholder Resolution
    apollo_id_map = {} # ID -> Real URL
    for url, data in batch_map.items():
        pm = data.get("profile_metadata") or {}
        a_id = pm.get("apollo_id")
        if a_id and not url.startswith("apollo_id:"):
            apollo_id_map[a_id] = url

    if apollo_id_map:
        # 1. Find existing placeholder profiles
        placeholder_query = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url.startswith("apollo_id:"))
        placeholder_res = await db.execute(placeholder_query)
        placeholders = placeholder_res.scalars().all()
        
        # 2. Pre-fetch existing "Real" profiles to check for conflicts
        real_urls = list(apollo_id_map.values())
        norm_real_urls = [normalize_linkedin_url(u) for u in real_urls]
        existing_real_query = select(IdentifiedProfile).where(IdentifiedProfile.normalized_linkedin_url.in_(norm_real_urls))
        existing_real_res = await db.execute(existing_real_query)
        # Map: normalized_url -> profile_object
        existing_real_map = {p.normalized_linkedin_url: p for p in existing_real_res.scalars().all()}

        for p in placeholders:
            try:
                # profile_metadata is a JSON string in a Text column
                pm_raw = p.profile_metadata
                p_pm = json.loads(pm_raw) if isinstance(pm_raw, str) and pm_raw.strip() else (pm_raw or {})
                pid = p_pm.get("apollo_id")
                
                if pid in apollo_id_map:
                    real_url = apollo_id_map[pid]
                    norm_url = normalize_linkedin_url(real_url)
                    
                    if norm_url in existing_real_map:
                        # CONFLICT: Real URL already exists as a full profile
                        # MERGE: Add apollo_id to the existing full profile and delete placeholder
                        target_p = existing_real_map[norm_url]
                        target_pm_raw = target_p.profile_metadata
                        target_pm = json.loads(target_pm_raw) if isinstance(target_pm_raw, str) and target_pm_raw.strip() else (target_pm_raw or {})
                        
                        target_pm["apollo_id"] = pid
                        target_p.profile_metadata = json.dumps(target_pm)
                        
                        await db.delete(p)
                        logger.info(f"MERGED Apollo placeholder {pid} into existing profile {norm_url}")
                    else:
                        # RESOLVE: Placeholder becomes the new real record
                        p.linkedin_url = real_url
                        p.normalized_linkedin_url = norm_url
                        
                        # Ensure apollo_id is in metadata after resolution
                        p_pm["apollo_id"] = pid
                        p.profile_metadata = json.dumps(p_pm)
                        
                        # Cache this as "existing" to avoid double-processing if another placeholder matches
                        existing_real_map[norm_url] = p
                        logger.info(f"RESOLVED Apollo placeholder: {pid} -> {real_url}")
            except Exception as e:
                logger.error(f"Error resolving placeholder for {p.linkedin_url}: {e}")

    # 2b. Company Auto-Linking
    domains_to_lookup = set()
    url_to_domain = {}
    for url, data in batch_map.items():
        if data.get("company_id"): continue
        
        # Check metadata or website field
        pm = data.get("profile_metadata") or {}
        website = pm.get("website") or data.get("website")
        if website:
            # Actually use a simple domain extractor
            domain = website.split("//")[-1].split("/")[0].replace("www.", "").lower().strip()
            if domain and "." in domain:
                domains_to_lookup.add(domain)
                url_to_domain[url] = domain

    if domains_to_lookup:
        comp_query = select(Company).where(Company.domain.in_(list(domains_to_lookup)))
        comp_res = await db.execute(comp_query)
        existing_companies = {c.domain: c for c in comp_res.scalars().all()}
        
        for url, domain in url_to_domain.items():
            if domain in existing_companies:
                batch_map[url]["company_id"] = existing_companies[domain].id
            else:
                # Optional: Create skeleton company if name is available?
                # For now, we only link existing or let classification handle creation.
                # Actually, let's create it if we have a name!
                comp_name = batch_map[url].get("profile_metadata", {}).get("company_name")
                if comp_name:
                    try:
                        new_comp = Company(
                            name=comp_name,
                            domain=domain,
                            website=f"https://{domain}"
                        )
                        db.add(new_comp)
                        await db.flush() # Get ID
                        batch_map[url]["company_id"] = new_comp.id
                        existing_companies[domain] = new_comp # Cache for this batch
                        logger.info(f"Created skeleton Company for {comp_name} ({domain})")
                    except Exception as e:
                        logger.error(f"Failed to create skeleton company {comp_name}: {e}")

    # 3. Fetch all existing profiles in one query (including newly resolved ones)
    urls = [normalize_linkedin_url(u) for u in batch_map.keys()]
    query = select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url.in_(urls))
    result = await db.execute(query)
    existing_profiles = {normalize_linkedin_url(p.linkedin_url): p for p in result.scalars().all()}
    
    # 3b. Trial Mode Threshold Check
    from utils.trial_utils import check_trial_lead_limit
    can_add_new = not (await check_trial_lead_limit(db, org_id, user_id))

    # 3. Prepare data for native batch upsert
    upsert_rows = []
    now = datetime.datetime.now(datetime.timezone.utc)
    
    logger.info(f"DEBUG: Preparing upsert for {len(batch_map)} unique profiles")
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
                if not any(normalize_linkedin_url(ds.get("url")) == n_s_url for ds in db_sources):
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
                post_entry = next((p for p in comp_entry["posts"] if normalize_linkedin_url(p["url"]) == n_lead_url), None)
                if not post_entry:
                    post_entry = {"url": interaction["source_post_url"], "title": interaction["source_post"], "comments": []}
                    comp_entry["posts"].append(post_entry)
                
                # 3. Add ONLY the specific comment for this interaction
                if interaction["comment"] and interaction["comment"] not in post_entry["comments"]:
                    post_entry["comments"].append(interaction["comment"])
            
            # Calculate touchpoint_count
            tp_count = sum(len(comp.get("posts", [])) for comp in db_history)
            
            upsert_rows.append({
                "linkedin_url": url,
                "name": data["name"] or p.name,
                "headline": data.get("headline") or p.headline,
                "is_fit": data.get("is_fit") or p.is_fit,
                "is_competitor": data.get("is_competitor") or p.is_competitor,
                "is_decision_maker": data.get("is_decision_maker") or p.is_decision_maker,
                "fit_reasoning": data.get("fit_reasoning") if data.get("fit_reasoning") not in [None, ""] else p.fit_reasoning,
                "intent": data.get("intent") or p.intent,
                "sentiment": data.get("sentiment") or p.sentiment,
                "email": data.get("email") or p.email,
                "email_verification_status": data.get("email_verification_status") or p.email_verification_status,
                "lead_source": p.lead_source or data.get("lead_source"),  # never overwrite existing source
                "comment_history": json.dumps(db_comments),
                "source_posts": json.dumps(db_sources),
                "interaction_history": json.dumps(db_history),
                "touchpoint_count": tp_count,
                "last_interaction_at": now,
                "company_id": data.get("company_id") or p.company_id,
                "organization_id": p.organization_id or org_id,
                "created_by_id": p.created_by_id or user_id,
                "profile_metadata": json.dumps({
                    **(json.loads(p.profile_metadata or "{}") if isinstance(p.profile_metadata, str) else (p.profile_metadata or {})),
                    **(data.get("profile_metadata") or {})
                }),
                "normalized_linkedin_url": url
            })
        else:
            # Create new row
            if not can_add_new:
                continue
            
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
                post_entry = next((p for p in comp_entry["posts"] if normalize_linkedin_url(p["url"]) == n_lead_url), None)
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

            # Calculate touchpoint_count
            tp_count = sum(len(comp.get("posts", [])) for comp in new_history)

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
                "email": data.get("email"),
                "email_verification_status": data.get("email_verification_status"),
                "lead_source": data.get("lead_source"),
                "comment_history": json.dumps(legacy_comments),
                "source_posts": json.dumps(legacy_sources),
                "interaction_history": json.dumps(new_history),
                "touchpoint_count": tp_count,
                "last_interaction_at": now,
                "company_id": data.get("company_id"),
                "profile_metadata": json.dumps(data.get("profile_metadata") or {}),
                "normalized_linkedin_url": url,
                "created_by_id": user_id,
                "organization_id": org_id
            })

    if upsert_rows:
        logger.info(f"DEBUG: Executing batch_upsert with {len(upsert_rows)} rows")
        results = await batch_upsert(
            db,
            IdentifiedProfile.__table__,
            upsert_rows,
            conflict_cols=["linkedin_url"],
            update_cols=["name", "headline", "is_fit", "is_competitor", "is_decision_maker", "fit_reasoning", "intent", "sentiment", "post_topic_depth", "lead_source", "comment_history", "source_posts", "interaction_history", "touchpoint_count", "last_interaction_at", "company_id", "email", "email_verification_status", "profile_metadata", "normalized_linkedin_url", "organization_id", "created_by_id"],
            chunk_size=100
        )
        logger.info(f"DEBUG: Batch upsert executed. Results count: {len(results)}")
        return results
    
    return []

async def upsert_identified_profile(db: AsyncSession, profile_data: dict, company_id: UUID | None = None, user_id: str = None, org_id: str = None):
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
        db_profile.touchpoint_count = len(sources)
        
        db_profile.last_interaction_at = datetime.datetime.now(datetime.timezone.utc)
        if profile_data.get("name") and not db_profile.name:
            db_profile.name = profile_data["name"]
        
        if profile_data.get("email"):
            db_profile.email = profile_data["email"]
        
        if profile_data.get("email_verification_status"):
            db_profile.email_verification_status = profile_data["email_verification_status"]

        if profile_data.get("profile_metadata"):
            md = profile_data["profile_metadata"]
            db_profile.profile_metadata = json.dumps(md) if isinstance(md, dict) else md

        if company_id:
            db_profile.company_id = company_id
            
        # Ensure URL is normalized even for existing profiles if they have mismatches
        db_profile.linkedin_url = normalize_linkedin_url(db_profile.linkedin_url)
        db_profile.normalized_linkedin_url = normalize_linkedin_url(db_profile.linkedin_url)
    else:
        # Trial Mode Threshold Check
        from utils.trial_utils import check_trial_lead_limit
        if await check_trial_lead_limit(db, org_id, user_id):
            return None

        # Calculate touchpoint_count
        tp_count = len(new_sources)
        
        db_profile = IdentifiedProfile(
            linkedin_url=normalize_linkedin_url(profile_data["linkedin_url"]),
            name=profile_data.get("name"),
            email=profile_data.get("email"),
            email_verification_status=profile_data.get("email_verification_status"),
            profile_metadata=json.dumps(profile_data.get("profile_metadata")) if isinstance(profile_data.get("profile_metadata"), dict) else profile_data.get("profile_metadata"),
            comment_history=json.dumps([new_comment]) if new_comment else "[]",
            source_posts=json.dumps(new_sources),
            touchpoint_count=tp_count,
            last_interaction_at=datetime.datetime.now(datetime.timezone.utc),
            company_id=company_id,
            normalized_linkedin_url=normalize_linkedin_url(profile_data["linkedin_url"]),
            created_by_id=user_id,
            organization_id=org_id
        )
        db.add(db_profile)
    
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

async def get_identified_profiles(db: AsyncSession, skip: int = 0, limit: int = 100, search_query: str = None, user_id: str = None, org_id: str = None):
    # Sort by number of touchpoints (length of source_posts array)
    from sqlalchemy.dialects.postgresql import JSONB
    
    # Fuzzy join to handle trailing slashes and parameter mismatches (e.g. "linkedin.com/in/user/" matches "linkedin.com/in/user")
    join_condition = func.trim(func.split_part(IdentifiedProfile.linkedin_url, '?', 1), '/') == \
                     func.trim(func.split_part(ResearchReport.linkedin_url, '?', 1), '/')

    query = select(IdentifiedProfile, ResearchReport.id.label("report_id"), Company).outerjoin(
        ResearchReport, join_condition
    ).outerjoin(
        Company, IdentifiedProfile.company_id == Company.id
    )
    
    if org_id:
        query = query.where(IdentifiedProfile.organization_id == org_id)
    elif user_id:
        query = query.where(or_(IdentifiedProfile.created_by_id == user_id, IdentifiedProfile.created_by_id.is_(None)))
    
    if search_query:
        search = f"%{search_query}%"
        query = query.where(
            or_(
                IdentifiedProfile.name.ilike(search),
                IdentifiedProfile.headline.ilike(search),
                IdentifiedProfile.fit_reasoning.ilike(search),
                IdentifiedProfile.intent.ilike(search),
                Company.name.ilike(search)
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

async def count_identified_profiles(db: AsyncSession, search_query: str = None, user_id: str = None, org_id: str = None):
    query = select(func.count()).select_from(IdentifiedProfile)
    
    if org_id:
        query = query.where(IdentifiedProfile.organization_id == org_id)
    elif user_id:
        query = query.where(or_(IdentifiedProfile.created_by_id == user_id, IdentifiedProfile.created_by_id.is_(None)))
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

async def save_report(db: AsyncSession, report_data: ResearchReportCreate, user_id: str = None, org_id: str = None):
    data = report_data.model_dump()
    if 'linkedin_url' in data and data['linkedin_url']:
        data['normalized_linkedin_url'] = normalize_linkedin_url(data['linkedin_url'])
    db_report = ResearchReport(**data)
    if org_id:
        import uuid
        db_report.organization_id = uuid.UUID(str(org_id)) if isinstance(org_id, str) else org_id
    if user_id:
        import uuid
        db_report.created_by_id = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
    db.add(db_report)
    await db.commit()
    await db.refresh(db_report)
    return db_report

async def get_user_settings(db: AsyncSession, user_id: str):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    return result.scalars().first()

async def upsert_user_settings(db: AsyncSession, user_id: str, settings_data: dict):
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    db_settings = result.scalars().first()
    
    if db_settings:
        for key, value in settings_data.items():
            if hasattr(db_settings, key):
                setattr(db_settings, key, value)
    else:
        db_settings = UserSettings(user_id=user_id, **settings_data)
        db.add(db_settings)
    
    await db.commit()
    await db.refresh(db_settings)
    return db_settings

async def delete_user_icp_override(db: AsyncSession, user_id: str):
    """Clears ONLY the icp_json field from UserSettings to allow fallback to global."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    db_settings = result.scalars().first()
    if db_settings:
        db_settings.icp_json = None
        await db.commit()
        return True
    return False

async def get_report_by_email_or_linkedin(db: AsyncSession, email_id: str = None, linkedin_url: str = None, user_id: str = None, org_id: str = None):
    if not email_id and not linkedin_url:
        return None
    
    conditions = []
    if email_id:
        conditions.append(ResearchReport.email_id == email_id)
    if linkedin_url:
        normalized_li = normalize_linkedin_url(linkedin_url)
        # Match both exact and normalized just in case
        conditions.append(or_(
            ResearchReport.linkedin_url == linkedin_url,
            ResearchReport.linkedin_url == normalized_li,
            func.trim(func.split_part(ResearchReport.linkedin_url, '?', 1), '/') == func.trim(func.split_part(normalized_li, '?', 1), '/')
        ))
        
    query = select(ResearchReport).where(or_(*conditions))
    if org_id:
        query = query.where(ResearchReport.organization_id == org_id)
    elif user_id:
        query = query.where(ResearchReport.created_by_id == user_id)
        
    query = query.order_by(desc(ResearchReport.created_at)).limit(1)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_history(db: AsyncSession, skip: int = 0, limit: int = 100, user_id: str = None, org_id: str = None):
    query = select(ResearchReport)
    if org_id:
        query = query.where(ResearchReport.organization_id == org_id)
    elif user_id:
        query = query.where(ResearchReport.created_by_id == user_id)
    query = query.order_by(desc(ResearchReport.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def get_report(db: AsyncSession, report_id: str):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def update_report_outreach(db: AsyncSession, report_id: str, outreach_data: dict, is_manual: bool = False):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        variant_index = outreach_data.pop("variant_index", None)
        edit_depths = {}
        
        if is_manual:
            # Calculate modification amount
            mod_pct = 0
            if variant_index is not None:
                report_data = _safe_deserialize(db_report.sales_research_report) or {}
                if "campaign_variants" in report_data and len(report_data["campaign_variants"]) > variant_index:
                    orig_data = report_data["campaign_variants"][variant_index]
                    mod_pct = _calculate_json_modification_percentage(orig_data, outreach_data)
                    existing_depths = orig_data.get("_edit_depths", {})
                    for key, val in outreach_data.items():
                        if isinstance(val, str) and key != "_edit_depths":
                            field_mod = _calculate_text_modification_percentage(str(orig_data.get(key, "")), val)
                            edit_depths[key] = max(existing_depths.get(key, 0), field_mod)
                        elif key == "steps" and isinstance(val, list):
                            # Special handling for sequence steps
                            orig_steps = orig_data.get("steps", [])
                            if isinstance(orig_steps, list):
                                for idx, step in enumerate(val):
                                    if idx < len(orig_steps):
                                        orig_content = str(orig_steps[idx].get("content", "") or orig_steps[idx].get("draft", ""))
                                        upd_content = str(step.get("draft", "") or step.get("content", ""))
                                        step_mod = _calculate_text_modification_percentage(orig_content, upd_content)
                                        step["_edit_depth"] = max(orig_steps[idx].get("_edit_depth", 0), step_mod)
                                        if step_mod > 5: # Threshold for "edited"
                                            edit_depths["steps"] = max(edit_depths.get("steps", 0), step_mod)
            else:
                orig_data = _safe_deserialize(db_report.personalized_outreach) or {}
                if isinstance(orig_data, dict):
                    mod_pct = _calculate_json_modification_percentage(orig_data, outreach_data)
                    existing_depths = orig_data.get("_edit_depths", {})
                    outreach_data["_edit_depth"] = max(orig_data.get("_edit_depth", 0), mod_pct)
                    for key, val in outreach_data.items():
                        if isinstance(val, str) and key != "_edit_depths" and key != "_edit_depth":
                            field_mod = _calculate_text_modification_percentage(str(orig_data.get(key, "")), val)
                            edit_depths[key] = max(existing_depths.get(key, 0), field_mod)
                        elif key == "steps" and isinstance(val, list):
                             # Special handling for single-touch sequence
                            orig_steps = orig_data.get("steps", [])
                            if isinstance(orig_steps, list):
                                for idx, step in enumerate(val):
                                    if idx < len(orig_steps):
                                        orig_content = str(orig_steps[idx].get("content", "") or orig_steps[idx].get("draft", ""))
                                        upd_content = str(step.get("draft", "") or step.get("content", ""))
                                        step_mod = _calculate_text_modification_percentage(orig_content, upd_content)
                                        step["_edit_depth"] = max(orig_steps[idx].get("_edit_depth", 0), step_mod)
                                        if step_mod > 5:
                                            edit_depths["steps"] = max(edit_depths.get("steps", 0), step_mod)
                else:
                    mod_pct = _calculate_text_modification_percentage(str(orig_data), str(outreach_data))
            
            db_report.is_outreach_edited = True
            db_report.edit_depth_percentage = max(db_report.edit_depth_percentage or 0, mod_pct)
            if edit_depths:
                db_report.edit_depth_percentage = max(db_report.edit_depth_percentage, max(edit_depths.values()))
            
            # If manually editing, consider outreach "in_progress" or "completed"
            if db_report.outreach_status == 'not_started':
                db_report.outreach_status = 'in_progress'
                db_report.outreach_started_at = datetime.datetime.now(datetime.timezone.utc)

        if edit_depths:
            outreach_data["_edit_depths"] = edit_depths

        if variant_index is not None:
            # Load list from personalized_outreach
            variants = _safe_json_load(db_report.personalized_outreach, [])
            if not isinstance(variants, list):
                variants = [variants] if variants else []
            
            if len(variants) > variant_index:
                # Merge existing _edit_depths if we only updated some fields
                if "_edit_depths" in variants[variant_index] and edit_depths:
                    merged_depths = {**variants[variant_index]["_edit_depths"], **edit_depths}
                    outreach_data["_edit_depths"] = merged_depths
                
                variants[variant_index].update(outreach_data)
                db_report.personalized_outreach = json.dumps(variants)
        else:
            # If no index, either replace entire list or it's a single update (assume replace for now)
            if isinstance(outreach_data, list):
                db_report.personalized_outreach = json.dumps(outreach_data)
            else:
                db_report.personalized_outreach = json.dumps([outreach_data])

        
        await db.commit()
        await db.refresh(db_report)
        return db_report
    return None

async def update_report_cso_outreach(db: AsyncSession, report_id: str, cso_data: dict, is_manual: bool = False):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        try:
            current_cso = json.loads(db_report.cso_strategic_briefing) if db_report.cso_strategic_briefing else {}
            
            if is_manual:
                # Calculate modification for specific fields
                mod_pct_li = _calculate_text_modification_percentage(
                    current_cso.get('refined_linkedin_message', ''), 
                    cso_data.get('refined_linkedin_message', '')
                )
                mod_pct_email = _calculate_text_modification_percentage(
                    current_cso.get('refined_email_body', ''), 
                    cso_data.get('refined_email_body', '')
                )
                avg_mod = (mod_pct_li + mod_pct_email) // 2
                
                db_report.is_outreach_edited = True
                db_report.edit_depth_percentage = max(db_report.edit_depth_percentage or 0, avg_mod)
                
                existing_depths = current_cso.get("_edit_depths", {})
                current_cso["_edit_depths"] = {
                    "refined_linkedin_message": max(existing_depths.get("refined_linkedin_message", 0), mod_pct_li),
                    "refined_email_body": max(existing_depths.get("refined_email_body", 0), mod_pct_email)
                }
                current_cso["_edit_depth"] = max(current_cso.get("_edit_depth", 0), avg_mod)
                
                if db_report.outreach_status == 'not_started':
                    db_report.outreach_status = 'in_progress'
                    db_report.outreach_started_at = datetime.datetime.now(datetime.timezone.utc)

            if 'refined_linkedin_message' in cso_data:
                current_cso['refined_linkedin_message'] = cso_data['refined_linkedin_message']
            if 'refined_email_body' in cso_data:
                current_cso['refined_email_body'] = cso_data['refined_email_body']
            
            db_report.cso_strategic_briefing = json.dumps(current_cso)
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            logger.info(f"Error updating CSO outreach: {e}")
            return None
    return None

async def update_report_outreach_status(db: AsyncSession, report_id: str, status: str):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        db_report.outreach_status = status
        if status != 'not_started' and not db_report.outreach_started_at:
            db_report.outreach_started_at = datetime.datetime.now(datetime.timezone.utc)
        await db.commit()
        await db.refresh(db_report)
        return db_report
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
            db_report.is_outreach_edited = True
            # For intent email, we assume a decent amount of modification if they are saving it
            db_report.edit_depth_percentage = max(db_report.edit_depth_percentage or 0, 5) 
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            logger.info(f"Error updating intent email: {e}")
            return None
    return None

async def update_report_sales_research(db: AsyncSession, report_id: str, blueprint_data: dict, is_manual: bool = True):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        try:
            current_report = json.loads(db_report.sales_research_report) if db_report.sales_research_report else {}
            # Update specific keys from blueprint_data
            for key, value in blueprint_data.items():
                current_report[key] = value
                
            db_report.sales_research_report = json.dumps(current_report)
            
            if is_manual:
                db_report.is_outreach_edited = True
                if db_report.outreach_status == 'not_started':
                    db_report.outreach_status = 'in_progress'
                    db_report.outreach_started_at = datetime.datetime.now(datetime.timezone.utc)
            
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            logger.info(f"Error updating sales research: {e}")
            return None
    return None

async def update_report_intent_analysis(db: AsyncSession, report_id: str, intent_data_update: dict, is_manual: bool = True):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        try:
            current_intent = json.loads(db_report.intent_analysis) if db_report.intent_analysis else {}
            for key, value in intent_data_update.items():
                current_intent[key] = value
                
            db_report.intent_analysis = json.dumps(current_intent)
            
            if is_manual:
                db_report.is_outreach_edited = True
                if db_report.outreach_status == 'not_started':
                    db_report.outreach_status = 'in_progress'
                    db_report.outreach_started_at = datetime.datetime.now(datetime.timezone.utc)
            
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            logger.info(f"Error updating intent analysis: {e}")
            return None
    return None

async def update_report_buyer_journey(db: AsyncSession, report_id: str, journey_data_update: dict, is_manual: bool = True):
    query = select(ResearchReport).where(ResearchReport.id == report_id)
    result = await db.execute(query)
    db_report = result.scalar_one_or_none()
    if db_report:
        try:
            current_journey = json.loads(db_report.buyer_journey_analysis) if db_report.buyer_journey_analysis else {}
            for key, value in journey_data_update.items():
                current_journey[key] = value
                
            db_report.buyer_journey_analysis = json.dumps(current_journey)
            
            if is_manual:
                db_report.is_outreach_edited = True
                if db_report.outreach_status == 'not_started':
                    db_report.outreach_status = 'in_progress'
                    db_report.outreach_started_at = datetime.datetime.now(datetime.timezone.utc)
            
            await db.commit()
            await db.refresh(db_report)
            return db_report
        except Exception as e:
            logger.info(f"Error updating buyer journey: {e}")
            return None
    return None

async def save_lead_submission(db: AsyncSession, submission: ResearchReportCreate, rep_id: str = None):
    from db.models import LeadSubmission
    db_item = LeadSubmission(**submission.dict())
    if rep_id:
        db_item.rep_id = rep_id
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

async def create_competitor(db: AsyncSession, competitor_data: dict, user_id: str = None, org_id: str = None):
    db_competitor = Competitor(**competitor_data)
    if org_id:
        db_competitor.organization_id = org_id
    if user_id:
        db_competitor.created_by_id = user_id
    db.add(db_competitor)
    await db.commit()
    await db.refresh(db_competitor)
    
    # Set transient creator_name for Pydantic response
    if user_id:
        result = await db.execute(select(Profile).where(Profile.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            setattr(db_competitor, "creator_name", user.full_name or user.email)
            
    return db_competitor

async def get_competitors(db: AsyncSession, user_id: str = None, org_id: str = None):
    query = select(Competitor, func.coalesce(Profile.full_name, Profile.email).label("creator_name")).outerjoin(
        Profile, Competitor.created_by_id == Profile.id
    )
    if org_id:
        query = query.where(Competitor.organization_id == org_id)
    elif user_id:
        query = query.where(Competitor.created_by_id == user_id)
    query = query.order_by(desc(Competitor.created_at))
    result = await db.execute(query)
    
    competitors = []
    for comp, creator_name in result.all():
        # Set a transient attribute for Pydantic to pick up
        setattr(comp, "creator_name", creator_name)
        competitors.append(comp)
    return competitors

async def delete_competitor(db: AsyncSession, competitor_id: str):
    query = select(Competitor).where(Competitor.id == competitor_id)
    result = await db.execute(query)
    competitor = result.scalar_one_or_none()
    if competitor:
        await db.delete(competitor)
        await db.commit()
        return True
    return False

async def create_activity(db: AsyncSession, type: str, title: str, description: str = None, metadata_json: str = None, intent: str = None, sentiment: str = None, user_id: str = None, org_id: str = None, idempotency_key: str = None):
    from sqlalchemy.dialects.postgresql import insert
    
    stmt = insert(Activity).values(
        type=type,
        title=title,
        description=description,
        metadata_json=metadata_json,
        intent=intent,
        sentiment=sentiment,
        idempotency_key=idempotency_key,
        created_by_id=user_id,
        organization_id=org_id
    )
    
    # If idempotency_key exists and conflicts, do nothing (prevents duplicates)
    if idempotency_key:
        stmt = stmt.on_conflict_do_nothing(index_elements=["idempotency_key"])
    
    stmt = stmt.returning(Activity)
    result = await db.execute(stmt)
    await db.commit()
    
    # scalars().first() will be None if conflict occurred
    return result.scalars().first()

async def delete_activity_by_key(db: AsyncSession, idempotency_key: str):
    from sqlalchemy import delete
    stmt = delete(Activity).where(Activity.idempotency_key == idempotency_key)
    await db.execute(stmt)
    await db.commit()
    return True

async def get_activities(db: AsyncSession, limit: int = 50, user_id: str = None, org_id: str = None):
    query = select(Activity, func.coalesce(Profile.full_name, Profile.email).label("creator_name")).outerjoin(
        Profile, Activity.created_by_id == Profile.id
    )
    if org_id:
        query = query.where(Activity.organization_id == org_id)
    elif user_id:
        query = query.where(Activity.created_by_id == user_id)
    query = query.order_by(desc(Activity.created_at)).limit(limit)
    result = await db.execute(query)
    
    activities = []
    for activity, creator_name in result.all():
        setattr(activity, "creator_name", creator_name)
        activities.append(activity)
    return activities

# Autopilot Rules CRUD
async def create_autopilot_rule(db: AsyncSession, rule_data: dict, user_id: str = None, org_id: str = None):
    db_rule = AutopilotRule(**rule_data)
    if org_id:
        db_rule.organization_id = org_id
    if user_id:
        db_rule.created_by_id = user_id
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    
    # Set transient creator_name for Pydantic response
    if user_id:
        result = await db.execute(select(Profile).where(Profile.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            setattr(db_rule, "creator_name", user.full_name or user.email)
            
    return db_rule

async def get_autopilot_rules(db: AsyncSession, rule_type: str = None, user_id: str = None, org_id: str = None):
    query = select(AutopilotRule, func.coalesce(Profile.full_name, Profile.email).label("creator_name")).outerjoin(
        Profile, AutopilotRule.created_by_id == Profile.id
    )
    if org_id:
        query = query.where(AutopilotRule.organization_id == org_id)
    elif user_id:
        query = query.where(AutopilotRule.created_by_id == user_id)
        
    if rule_type:
        query = query.where(AutopilotRule.type == rule_type)
    query = query.where(AutopilotRule.is_active == True).order_by(desc(AutopilotRule.created_at))
    result = await db.execute(query)
    
    rules = []
    for rule, creator_name in result.all():
        setattr(rule, "creator_name", creator_name)
        rules.append(rule)
    return rules

async def delete_autopilot_rule(db: AsyncSession, rule_id: str):
    query = select(AutopilotRule).where(AutopilotRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()
    if rule:
        # Soft delete
        rule.is_active = False
        await db.commit()
        return True
    return False

async def get_org_settings(db: AsyncSession, user_id: UUID | str | None = None, org_id: UUID | str | None = None):
    query = select(OrganizationSettings)
    conditions = []
    if org_id:
        o_id = UUID(str(org_id)) if isinstance(org_id, str) else org_id
        conditions.append(OrganizationSettings.organization_id == o_id)
    if user_id:
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        conditions.append(OrganizationSettings.owner_id == u_id)
    
    if conditions:
        query = query.where(or_(*conditions))
        # Prioritize Org-linked, then Owner-linked
        query = query.order_by(desc(OrganizationSettings.organization_id), desc(OrganizationSettings.owner_id))
    else:
        # Final fallback: orphaned settings
        query = query.where(and_(OrganizationSettings.organization_id == None, OrganizationSettings.owner_id == None))
    
    result = await db.execute(query.limit(1))
    return result.scalars().first()

# CRM Context CRUD
async def upsert_crm_context(db: AsyncSession, data: dict):
    from db.models import CRMContext
    from sqlalchemy.dialects.postgresql import insert
    
    stmt = insert(CRMContext).values(**data)
    # Upsert on email or linkedin_url if provided
    index_elements = []
    if data.get("email"):
        index_elements.append(CRMContext.email)
    elif data.get("linkedin_url"):
        index_elements.append(CRMContext.linkedin_url)
        
    if index_elements:
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_={k: v for k, v in data.items() if k not in ["email", "linkedin_url"]}
        )
    
    await db.execute(stmt)
    await db.commit()

async def match_crm_context(db: AsyncSession, email: str = None, linkedin_url: str = None):
    from db.models import CRMContext
    query = select(CRMContext)
    if email:
        query = query.where(CRMContext.email == email)
    elif linkedin_url:
        query = query.where(CRMContext.linkedin_url == linkedin_url)
    else:
        return None
        
    result = await db.execute(query)
    return result.scalars().first()
