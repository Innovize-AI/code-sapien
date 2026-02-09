import json
from fastapi import APIRouter, Depends, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db, save_lead_submission, get_db_session
from db.schemas import LeadSubmissionCreate
from routes.sales_research import run_single_research
from workflow.state import InputLeadData
from utils.activity_helper import log_activity_and_notify
import asyncio

webhooks_router = APIRouter(tags=['Webhooks'], prefix="/webhooks")

@webhooks_router.post("/generic")
async def generic_webhook(
    request: Request,
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
    
    saved = await save_lead_submission(db, submission)
    
    # Trigger research in background
    asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, payload))
    
    return {"status": "received", "submission_id": str(saved.id)}

@webhooks_router.post("/calendly")
async def calendly_webhook(
    request: Request,
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
        saved = await save_lead_submission(db, submission)
        
        # Log Activity
        await log_activity_and_notify(
            db, 
            type="meeting", 
            title="New Meeting Booked (Calendly)", 
            description=f"Meeting scheduled by {email}",
            metadata={"email": email, "source": "calendly", "payload": payload}
        )
        
        asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, payload))
        return {"status": "processed"}
        
    return {"status": "ignored"}

@webhooks_router.post("/cal")
async def cal_webhook(
    request: Request,
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
        saved = await save_lead_submission(db, submission)
        
        # Log Activity
        await log_activity_and_notify(
            db, 
            type="meeting", 
            title="New Meeting Booked (Cal.com)", 
            description=f"Meeting scheduled by {email}",
            metadata={"email": email, "source": "cal", "payload": payload}
        )
        
        asyncio.create_task(process_webhook_lead(saved.id, email, None, payload))
        return {"status": "processed"}
    
    return {"status": "ignored"}

@webhooks_router.post("/convertkit")
async def convertkit_webhook(
    request: Request,
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
        saved = await save_lead_submission(db, submission)
        
        # Add form context to the research extras
        extras = {
            **payload,
            "lead_intent": f"Subscribed to form: {form_name}" if form_name else "Joined subscriber list"
        }
        
        asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, extras))
        return {"status": "processed"}
        
    return {"status": "ignored"}

@webhooks_router.post("/typeform")
async def typeform_webhook(
    request: Request,
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
        saved = await save_lead_submission(db, submission)
        asyncio.create_task(process_webhook_lead(saved.id, email, linkedin_url, payload))
        return {"status": "processed"}
        
    return {"status": "ignored"}

async def process_webhook_lead(submission_id, email, linkedin_url, extras):
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
        result = await run_single_research(
            linkedin_url=linkedin_url,
            email=email,
            options=options
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
        print(f"Error processing webhook lead {submission_id}: {e}")
