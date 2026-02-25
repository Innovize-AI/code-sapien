import os
import json
import uuid
import re
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import SessionLocal
from db.crud import save_report, get_report_by_email_or_linkedin
from db.schemas import ResearchReportCreate
from utils.activity_helper import log_activity_and_notify
from workflow.state import IdealProfile, InputLeadData, AgentState
from workflow.graph import graph, NODE_STATUS_MAPPING
from utils.common import add_https_if_missing
from prompts.sales_prompts import COMPANY_CONTEXT

async def _get_organization_settings(user_id: str = None) -> dict:
    """Helper to fetch settings from database with per-user overrides."""
    async with SessionLocal() as db:
        from sqlalchemy import select
        from db.models import OrganizationSettings, UserSettings
        
        # 1. Fetch Global Settings
        result = await db.execute(select(OrganizationSettings).limit(1))
        global_settings = result.scalars().first()
        
        # 2. Fetch User Settings (if user_id provided)
        user_settings = None
        if user_id:
            result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            user_settings = result.scalars().first()
            
        # 3. Default ICP (Fallback if neither global nor user set)
        icp = IdealProfile(
            industry="Finance",
            company_size="10-50",
            revenue="$10M+",
            job_title="CTO, CEO"
        )
        
        # 4. Apply Global ICP if available
        if global_settings and global_settings.icp_json:
            try:
                icp = IdealProfile(**json.loads(global_settings.icp_json))
            except Exception as e:
                print(f"Error parsing global ICP settings: {e}")
                
        # 5. Apply User ICP Override if available
        if user_settings and user_settings.icp_json:
            try:
                user_icp_data = json.loads(user_settings.icp_json)
                if user_icp_data: # If not empty dict
                    icp = IdealProfile(**user_icp_data)
            except Exception as e:
                print(f"Error parsing user ICP settings: {e}")

        # 6. Resolve Identity (User-private URLs/Config)
        # Priority: User Settings > Global Settings > None
        user_linkedin = (user_settings.user_linkedin_url if user_settings and user_settings.user_linkedin_url else None) or \
                        (global_settings.user_linkedin_url if global_settings else None)
        
        email_config = (user_settings.email_config if user_settings and user_settings.email_config else None) or \
                       (global_settings.email_config if global_settings else None)
        
        company_linkedin = global_settings.company_linkedin_url if global_settings else None
        
        selling_profile = None
        if global_settings and global_settings.selling_profile_json:
            try:
                from db.schemas import SellingProfileConfig
                selling_profile = SellingProfileConfig(**json.loads(global_settings.selling_profile_json))
            except Exception as e:
                print(f"Error parsing Selling Profile: {e}")

        return {
            "icp": icp,
            "selling_profile": selling_profile,
            "user_linkedin_url": user_linkedin,
            "company_linkedin_url": company_linkedin,
            "email_config": email_config
        }

def _safe_serialize(val):
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val or ""

def _prepare_state_for_json(state):
    """Helper to convert Pydantic models in the state to dicts for JSON serialization."""
    if not state:
        return state
    
    cleaned = {}
    for k, v in state.items():
        if hasattr(v, 'model_dump'):
            cleaned[k] = v.model_dump()
        elif hasattr(v, 'dict'):
            cleaned[k] = v.dict()
        else:
            cleaned[k] = v
    return cleaned

async def _persist_results(db, linkedin_url, website, final_state, options, user_id=None):
    """Common logic to save research results to DB with multi-tenant support."""
    if not final_state.get("sales_research_report"):
        print("Skipping database save: No research report generated.")
        return None

    # Extract numeric lead score if possible
    lead_score = None
    score_analysis = final_state.get("lead_score_analysis")
    if score_analysis:
        if isinstance(score_analysis, dict):
            lead_score = score_analysis.get("total_score")
        elif isinstance(score_analysis, str):
            match = re.search(r"Score:\s*(\d+)", score_analysis)
            if match:
                try:
                    lead_score = int(match.group(1))
                except:
                    pass

    report_data = ResearchReportCreate(
        linkedin_url=linkedin_url or "",
        email_id=final_state.get("email_id") or "",
        website=website or "",
        sales_research_report=_safe_serialize(final_state.get("sales_research_report")),
        viability_analysis=_safe_serialize(final_state.get("viability_analysis")),
        lead_score_analysis=json.dumps(final_state.get("lead_score_analysis") or {}),
        user_profile_analysis=json.dumps(final_state.get("user_profile_analysis") or {}),
        website_analysis=json.dumps(final_state.get("website_analysis") or {}),
        fullname=final_state.get("fullname"),
        profile_picture_url=final_state.get("profile_picture_url"),
        company_name=final_state.get("company_name"),
        company_description=final_state.get("company_description"),
        company_industries=json.dumps(final_state.get("company_industries") or []),

        lead_score=lead_score,
        project_urgency=options.project_urgency if options else None,
        email_history=json.dumps(final_state.get("email_history") or []),
        intent_analysis=json.dumps(final_state.get("intent_analysis") or {}),
        extra_metadata=json.dumps({
            **(final_state.get("extra_research_context") or {}),
            "discovery_source": options.discovery_source if options else None,
            "discovery_context": options.discovery_context if options else None,
            "lead_extracted_data": final_state.get("lead_extracted_data").model_dump() if hasattr(final_state.get("lead_extracted_data"), 'model_dump') else (final_state.get("lead_extracted_data") or {})
        }),
        
        # Modular Nodules
        target_pain_points=json.dumps(final_state.get("target_pain_points") or {}),
        strategic_solutions=json.dumps(final_state.get("strategic_solutions") or {}),
        personalized_outreach=json.dumps(final_state.get("personalized_outreach") or {}),
        follow_up_strategy=_safe_serialize(final_state.get("follow_up_strategy")),
        cso_strategic_briefing=json.dumps(final_state.get("cso_strategic_briefing") or {}),
        buyer_journey_analysis=json.dumps(final_state.get("buyer_journey_analysis") or {}),
        meeting_notes=final_state.get("meeting_notes"),
        
        # LinkedIn Subgraph Data
        post_engagements=json.dumps(final_state.get("post_engagements") or []),
        company_news=json.dumps(final_state.get("company_news") or []),
        hiring_data=json.dumps(final_state.get("hiring_data") or []),
        company_stats=json.dumps(final_state.get("company_stats") or {}),
        icp_context=json.dumps(final_state.get("ideal_profile").model_dump() if hasattr(final_state.get("ideal_profile"), "model_dump") else (final_state.get("ideal_profile") or {}))
    )
    
    saved_report = await save_report(db, report_data, user_id=user_id)
    
    if saved_report:
        # Log Activity: Analysis Completed
        fullname = final_state.get("fullname") or linkedin_url or final_state.get("email_id") or "Unknown Lead"
        
        journey_analysis = final_state.get("buyer_journey_analysis") or {}
        pain_point_analysis = final_state.get("target_pain_points") or {}
        
        metadata = {
            "report_id": str(saved_report.id), 
            "lead_score": lead_score, 
            "name": fullname,
            "journey_stage": journey_analysis.get("journey_stage"),
            "heat_rating": journey_analysis.get("sentiment_score"),
            "urgency": journey_analysis.get("urgency_level"),
            "pain_points": pain_point_analysis.get("points", []) if isinstance(pain_point_analysis, dict) else []
        }
        
        await log_activity_and_notify(
            db,
            type="analysis",
            title=f"Analysis completed for {fullname}",
            description=f"Deep research finished with lead score: {lead_score}",
            metadata=metadata,
            user_id=user_id
            
        )
        
        # Log Activity: High Potential Lead
        if lead_score and lead_score >= 80:
            await log_activity_and_notify(
                db,
                type="high_potential",
                title=f"🔥 High Potential Lead Identified: {fullname}",
                description=f"Match score {lead_score}/100 exceeds threshold.",
                metadata={"report_id": str(saved_report.id), "lead_score": lead_score, "name": fullname, "is_fit": True},
                user_id=user_id
            )
            
        return saved_report
    else:
        return None

async def _run_research_gen(linkedin_url, website, options: InputLeadData, email, user_id=None):
    """Core generator that runs the research graph and yields updates."""
    website = add_https_if_missing(website)
    thread_id = f"{user_id}_{email or linkedin_url or uuid.uuid4()}"
    thread = {"configurable": {"thread_id": thread_id}}
    
    org_settings = await _get_organization_settings(user_id=user_id)
    ideal_profile = org_settings["icp"]

    if options is None:
        options = InputLeadData()

    # --- Context Injection: Load Discovery Data from DB ---
    # Only if not already provided in options/request
    if linkedin_url and not options.discovery_source:
        try:
            async with SessionLocal() as db:
                from sqlalchemy import select
                from db.models import IdentifiedProfile
                
                result = await db.execute(select(IdentifiedProfile).where(IdentifiedProfile.linkedin_url == linkedin_url))
                profile = result.scalars().first()
                
                if profile:
                    print(f"DEBUG: Found identified profile for {linkedin_url}. Injecting context.")
                    
                    try:
                        import json
                        comments = json.loads(profile.comment_history or "[]")
                        sources = json.loads(profile.source_posts or "[]")
                        interactions = json.loads(profile.interaction_history or "[]")
                    except Exception as e:
                        print(f"Error parsing profile data: {e}")
                        comments = []
                        sources = []
                        interactions = []
                    
                    # Deduplicate comments with normalization to avoid visible duplicates in UI
                    seen = set()
                    unique_comments = []
                    for c in (comments or []):
                        if not c: continue
                        normalized = c.strip()
                        if normalized not in seen:
                            unique_comments.append(c) # Keep original casing/spacing for display
                            seen.add(normalized)
                    
                    # Store for initial_state injection
                    discovery_history = interactions
                    
                    if sources:
                        # Intelligently detect if it's a keyword search even if sources exist
                        # (Because keyword discovered leads also save their source posts)
                        is_keyword = any(isinstance(s, dict) and str(s.get("competitor", "")).startswith("Keyword:") for s in sources)
                        
                        if is_keyword:
                            options.discovery_source = "keyword_search"
                            options.discovery_context = {
                                "fit_reasoning": profile.fit_reasoning,
                                "intent": profile.intent,
                                "profile_metadata": profile.profile_metadata,
                                "comments": unique_comments, # Include comments/posts for richness
                                "source_posts": sources
                            }
                        else:
                            options.discovery_source = "competitor_comment"
                            options.discovery_context = {
                                "comments": unique_comments,
                                "source_posts": sources,
                                # Removed redundant interaction_history here as it's passed at top level now
                                "fit_reasoning": profile.fit_reasoning,
                                "intent": profile.intent
                            }
                    else:
                        options.discovery_source = "keyword_search"
                        options.discovery_context = {
                            "fit_reasoning": profile.fit_reasoning,
                            "intent": profile.intent,
                            "profile_metadata": profile.profile_metadata
                        }

        except Exception as e:
            print(f"Error loading identified profile context in _run_research_gen: {e}")

    # --- Persistent Agentic Memory: Load existing data from DB ---
    existing_state = {}
    discovery_history = []

    options_refresh = options.refresh if options else False
    trigger_ctx = getattr(options, 'trigger_context', None) if options else None

    # Load existing state if NOT refreshing OR if this is a targeted update (which needs context)
    if not options_refresh or trigger_ctx:
        async with SessionLocal() as db:
            existing = await get_report_by_email_or_linkedin(db, email_id=email, linkedin_url=linkedin_url)
            if existing:
                print(f"Loading persistent memory for {email or linkedin_url}")
                # We need access to _report_to_dict which is in db.crud usually, importing here or duplicating
                # Ideally, reuse from crud
                from db.crud import _report_to_dict
                existing_state = _report_to_dict(existing)

    from workflow.state import SellingCompanyProfile, Product
    
    # Load Selling Profile from Settings OR Default
    selling_profile_data = org_settings.get("selling_profile")
    
    if selling_profile_data:
        # Convert Schema Schema to State Schema (if different, but they look compatible)
        # Using the loaded profile directly
        selling_company_profile = selling_profile_data
    else:
        # Fallback Default
        selling_company_profile = SellingCompanyProfile(
            name="Innovize AI",
            description="Specialized AI Transformation and Autonomous Agent Orchestration",
            products=[
                Product(name="Glial", description="Revenue Intelligence", target_pain_points=["Sales"]),
                Product(name="AI Consulting", description="Strategy", target_pain_points=["Strategy"])
            ]
        )

    initial_state = {
        "email_id": email,
        "linkedin_url": linkedin_url or existing_state.get("linkedin_url"),
        "website": website or existing_state.get("website"),
        "company_context": COMPANY_CONTEXT,
        "selling_company_profile": selling_company_profile, # dynamic context
        "ideal_profile": ideal_profile,
        "user_linkedin_url": org_settings["user_linkedin_url"],
        "company_linkedin_url": org_settings["company_linkedin_url"],
        "lead_company_linkedin_url": existing_state.get("lead_company_linkedin_url", ""),
        "input_lead_data": options,
        "extra_research_context": options.extra_metadata if options else existing_state.get("extra_metadata"),
        
        "user_profile_details": existing_state.get("user_profile_details", {}),
        "scraped_website_content": existing_state.get("scraped_website_content", ""),
        
        "user_profile_analysis": existing_state.get("user_profile_analysis", {}),
        "website_analysis": existing_state.get("website_analysis", {}),
        "lead_score_analysis": existing_state.get("lead_score_analysis", {}),
        "target_pain_points": existing_state.get("target_pain_points", {}),
        "strategic_solutions": existing_state.get("strategic_solutions", {}),
        "personalized_outreach": existing_state.get("personalized_outreach", {}),
        "follow_up_strategy": existing_state.get("follow_up_strategy", {}),
        "buyer_journey_analysis": existing_state.get("buyer_journey_analysis", {}),
        "cso_strategic_briefing": existing_state.get("cso_strategic_briefing", {}),
        "intent_analysis": existing_state.get("intent_analysis", {}),
        "email_history": existing_state.get("email_history", []),
        
        "post_engagements": existing_state.get("post_engagements", []),
        "company_news": existing_state.get("company_news", []),
        "hiring_data": existing_state.get("hiring_data", []),
        "company_stats": existing_state.get("company_stats", {}),
        
        "company_name": existing_state.get("company_name", ""),
        "company_description": existing_state.get("company_description", ""),
        "company_industries": existing_state.get("company_industries", []),
        "fullname": existing_state.get("fullname", ""),
        "profile_picture_url": existing_state.get("profile_picture_url", ""),
        
        "sales_research_report": existing_state.get("sales_research_report", {}),
        "meeting_notes": getattr(options, 'meeting_notes', '') if hasattr(options, 'meeting_notes') else options.get('meeting_notes', '') if isinstance(options, dict) else '',
        "discovery_interaction_history": discovery_history or existing_state.get("discovery_interaction_history", [])
    }


    final_state = initial_state.copy()
    
    try:
        async for update in graph.astream(initial_state, thread, stream_mode="updates"):
            for node_name, state_update in update.items():
                final_state.update(state_update)
                yield node_name, state_update, final_state
    except Exception as e:
        print(f"Error during graph execution: {e}")
        raise e

async def _push_to_hubspot_if_enabled(db, user_id, report, final_state):
    """
    Check if HubSpot sync is enabled and push research as a Note.
    """
    from db.crud import get_org_settings
    from services.hubspot_service import HubspotService
    
    settings = await get_org_settings(db)
    if settings and settings.hubspot_access_token and settings.hubspot_sync_enabled:
        try:
            hs = HubspotService(settings.hubspot_access_token)
            
            # Match contact first
            email = report.email_id
            li_url = report.linkedin_url
            
            # Find contact ID from CRM Context or search HubSpot
            from db.crud import match_crm_context
            crm_ctx = await match_crm_context(db, email=email, linkedin_url=li_url)
            
            target_id = None
            if crm_ctx and crm_ctx.hubspot_contact_id:
                target_id = crm_ctx.hubspot_contact_id
            
            if target_id:
                content = f"<h3>AI Research Report (Score: {report.lead_score})</h3>"
                content += f"<p><b>Viability:</b> {report.viability_analysis[:500]}...</p>"
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                content += f"<p><a href='{frontend_url}/reports/{report.id}'>View Full Report in Innovize AI</a></p>"
                
                await hs.push_note("contact", target_id, content)
                print(f"Successfully pushed research note to HubSpot for {email}")
        except Exception as e:
            print(f"Failed to push HubSpot note: {e}")

async def run_single_research(
    linkedin_url: Optional[str] = None,
    website: Optional[str] = None,
    options: InputLeadData = None,
    email: Optional[str] = None,
    user_id: Optional[str] = None,
    progress_callback=None
):
    """
    Runs a single research workflow.
    """
    if options is None:
        options = InputLeadData()

    final_state = {}
    try:
        async for node_name, state_update, current_state in _run_research_gen(linkedin_url, website, options, email, user_id=user_id):
            final_state = current_state
            if progress_callback:
                message = NODE_STATUS_MAPPING.get(node_name, f"Processing {node_name}...")
                await progress_callback(linkedin_url, message)

        # Persist results to DB
        async with SessionLocal() as db:
            saved_report = await _persist_results(db, linkedin_url, website, final_state, options, user_id=user_id)
            if saved_report:
                # HubSpot Bidirectional Sync
                await _push_to_hubspot_if_enabled(db, user_id, saved_report, final_state)
                
        return {"linkedin_url": linkedin_url, "result": _prepare_state_for_json(final_state)}
    except Exception as e:
        print(f"Error in run_single_research: {e}")
        # Return error/none but don't crash caller
