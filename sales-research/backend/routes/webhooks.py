import json
from fastapi import APIRouter, Depends, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_lead_submission, get_db_session
from db.schemas import LeadSubmissionCreate
# run_single_research moved inside process_webhook_lead
from workflow.state import InputLeadData
from utils.activity_helper import log_activity_and_notify
import asyncio
from pydantic import BaseModel
from typing import Optional
from fastapi import BackgroundTasks

webhooks_router = APIRouter(tags=['Webhooks'], prefix="/webhooks")

class EmailWebhookPayload(BaseModel):
    email_id: str
    subject: Optional[str] = None
    snippet: Optional[str] = None

class CRMWebhookPayload(BaseModel):
    contact_email: str
    deal_id: Optional[str] = None
    change_type: str # e.g., "stage_change", "new_note"

async def run_targeted_research_background(email: str, trigger: str):
    """
    Background task to run the research graph with a specific trigger.
    Consumes the generator to ensure the graph executes fully.
    """
    print(f"WEBHOOK: Starting targeted research for {email} (Trigger: {trigger})")
    
    # We need a user_id context. For webhooks, we might need a system user or 
    # try to find the owner. For now, we'll try to find an owner or use None (system).
    user_id = None
    
    try:
        from services.research_service import _run_research_gen
        
        # Create Input with Trigger Context
        input_data = InputLeadData(
            refresh=True, # We want to re-run relevant nodes
            trigger_context=trigger
        )
        
        async for _ in _run_research_gen(
            linkedin_url=None, 
            website=None, 
            options=input_data, 
            email=email, 
            user_id=user_id
        ):
            pass
            
        print(f"WEBHOOK: Targeted research completed for {email}")
        
    except Exception as e:
        print(f"WEBHOOK ERROR for {email}: {e}")

@webhooks_router.post("/generic")
async def generic_webhook(
    request: Request,
    rep_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.json()
    email = payload.get("email")
    if not email:
        return {"error": "Email is required"}
    
    linkedin_url = payload.get("linkedin_url") or payload.get("url")
    
    submission = LeadSubmissionCreate(
        email=email,
        linkedin_url=linkedin_url,
        source="webhook",
        payload=json.dumps(payload)
    )
    
    saved = await save_lead_submission(db, submission, rep_id=rep_id)
    
    # Trigger research in background
    asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, payload, rep_id))
    
    return {"status": "received", "submission_id": str(saved.id)}

@webhooks_router.post("/calendly")
async def calendly_webhook(
    request: Request,
    rep_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.json()
    event = payload.get("event")
    
    if event == "invitee.created":
        data = payload.get("payload", {})
        email = data.get("email")
        # Calendly often has external_answers or responses
        questions = data.get("questions_and_answers", [])
        linkedin_url = None
        for q in questions:
            if "linkedin" in q.get("question", "").lower():
                linkedin_url = q.get("answer")
        
        submission = LeadSubmissionCreate(
            email=email,
            linkedin_url=linkedin_url,
            source="calendly",
            payload=json.dumps(payload)
        )
        saved = await save_lead_submission(db, submission, rep_id=rep_id)
        
        # Log Activity
        import hashlib
        event_uri = data.get("uri") or f"{email}:{payload.get('created_at')}"
        idempotency_key = f"calendly:{hashlib.md5(event_uri.encode()).hexdigest()}"
        
        await log_activity_and_notify(
            db, 
            type="meeting", 
            title="New Meeting Booked (Calendly)", 
            description=f"Meeting scheduled by {email}",
            metadata={"email": email, "source": "calendly", "payload": payload},
            user_id=rep_id,
            idempotency_key=idempotency_key
        )
        
        asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, payload, rep_id))
        return {"status": "processed"}
        
    return {"status": "ignored"}

@webhooks_router.post("/cal")
async def cal_webhook(
    request: Request,
    rep_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.json()
    submission_data = payload.get("payload", {})
    email = submission_data.get("email")
    
    if email:
        submission = LeadSubmissionCreate(
            email=email,
            linkedin_url=None,
            source="cal",
            payload=json.dumps(payload)
        )
        saved = await save_lead_submission(db, submission, rep_id=rep_id)
        
        # Log Activity
        import hashlib
        # Cal.com payload often has a 'uid' or 'bookingId'
        booking_id = str(payload.get("bookingId") or payload.get("uid") or f"{email}:{payload.get('createdAt')}")
        idempotency_key = f"calcom:{hashlib.md5(booking_id.encode()).hexdigest()}"

        await log_activity_and_notify(
            db, 
            type="meeting", 
            title="New Meeting Booked (Cal.com)", 
            description=f"Meeting scheduled by {email}",
            metadata={"email": email, "source": "cal", "payload": payload},
            user_id=rep_id,
            idempotency_key=idempotency_key
        )
        
        asyncio.create_task(process_webhook_lead(saved.id, email, None, payload, rep_id))
        return {"status": "processed"}
    
    return {"status": "ignored"}

@webhooks_router.post("/convertkit")
async def convertkit_webhook(
    request: Request,
    rep_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.json()
    subscriber = payload.get("subscriber", {})
    email = subscriber.get("email_address")
    
    if email:
        # ConvertKit sends "form" object if the trigger was a form subscription
        form_data = payload.get("form", {})
        form_id = str(form_data.get("id")) if form_data.get("id") else None
        form_name = form_data.get("name")
        
        # Extract custom fields if any
        custom_fields = subscriber.get("fields", {})
        linkedin_url = custom_fields.get("linkedin_url") or custom_fields.get("linkedin")
        
        submission = LeadSubmissionCreate(
            email=email,
            linkedin_url=linkedin_url,
            source="convertkit",
            payload=json.dumps(payload),
            external_form_id=form_id,
            external_form_name=form_name
        )
        saved = await save_lead_submission(db, submission, rep_id=rep_id)
        
        # Add form context to the research extras
        extras = {
            **payload,
            "lead_intent": f"Subscribed to form: {form_name}" if form_name else "Joined subscriber list"
        }
        
        asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, extras, rep_id))
        return {"status": "processed"}
        
    return {"status": "ignored"}

@webhooks_router.post("/typeform")
async def typeform_webhook(
    request: Request,
    rep_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.json()
    form_response = payload.get("form_response", {})
    answers = form_response.get("answers", [])
    
    email = None
    linkedin_url = None
    
    # Typeform answers are an array of objects
    for answer in answers:
        field_type = answer.get("type")
        value = answer.get(field_type)
        
        # We look for fields that look like email or linkedin
        # This is a bit heuristic, Typeform payloads usually have field IDs/refs
        if field_type == "email":
            email = value
        elif isinstance(value, str) and "linkedin.com" in value.lower():
            linkedin_url = value
            
    if email:
        submission = LeadSubmissionCreate(
            email=email,
            linkedin_url=linkedin_url,
            source="typeform",
            payload=json.dumps(payload)
        )
        saved = await save_lead_submission(db, submission, rep_id=rep_id)
        asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, payload, rep_id))
        return {"status": "processed"}
        
    return {"status": "ignored"}

async def process_webhook_lead(submission_id, email, linkedin_url, extras, rep_id=None):
    """Background task to run research for a webhook lead."""
    from datetime import datetime
    from sqlalchemy import update
    from db.models import LeadSubmission
    
    options = InputLeadData(
        project_urgency=2, # Default to medium
        refresh=False,
        extra_metadata=extras # Pass the full payload as context
    )
    
    try:
        from services.research_service import run_single_research
        result = await run_single_research(
            linkedin_url=linkedin_url,
            email=email,
            options=options,
            user_id=rep_id
        )
        
        research_id = result.get("result", {}).get("id")
        
        # Update submission with research_id and processed timestamp
        async with get_db_session() as db:
            await db.execute(
                update(LeadSubmission)
                .where(LeadSubmission.id == submission_id)
                .values(processed_at=datetime.utcnow(), research_id=research_id)
            )
            await db.commit()
            
    except Exception as e:
        print(f"Error processing webhook lead {submission}: {e}")

@webhooks_router.post("/email-received")
async def email_received_webhook(payload: EmailWebhookPayload, background_tasks: BackgroundTasks):
    """
    Trigger research update when a new email is received.
    """
    background_tasks.add_task(run_targeted_research_background, payload.email_id, "email_update")
    return {"status": "accepted", "message": f"Research update triggered for {payload.email_id}"}

@webhooks_router.post("/crm-updated")
async def crm_updated_webhook(payload: CRMWebhookPayload, background_tasks: BackgroundTasks):
    """
    Trigger research update when CRM data changes.
    """
    background_tasks.add_task(run_targeted_research_background, payload.contact_email, "crm_update")
    return {"status": "accepted", "message": f"Research update triggered for {payload.contact_email}"}
