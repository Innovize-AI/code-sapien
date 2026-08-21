from fastapi import APIRouter, Query
from workflow.graph import create_Workflow
from pydantic import BaseModel
from routes.database import create_email_record, get_user_with_email, get_db
from db.schemas import EmailCreate
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends, HTTPException
from workflow.state import AgentGraphState
import datetime
import requests
import os
inbox_manager_router = APIRouter(prefix='/generate-draft', tags=['Inbox Manager'],responses={404: {"description": "Not found"}},)

workflow= create_Workflow()
N8N_WEBHOOK_URL= os.getenv("N8N_WEBHOOK_URL")

class DrafterRequest(BaseModel):
    raw_email_body:str
    company_domain_name:str
    sender_email_id:str
    to_email_id:Optional[str]
    thread_id:str
    thread_messages: Optional[list[dict]]

class SendEmailRequest(BaseModel):
    thread_id:str
    email_draft: str

@inbox_manager_router.post("/")
@inbox_manager_router.post("")
async def run_workflow(drafter_request: DrafterRequest,db: AsyncSession = Depends(get_db) ):

    response:AgentGraphState= workflow.invoke({
    
    "raw_email_body": drafter_request.raw_email_body,
    "company_domain_name": drafter_request.company_domain_name,
    "sender_email_id": drafter_request.sender_email_id,
    "email_thread_history": drafter_request.thread_messages
    # "to_email_id": drafter_request.to_email_id
    
    })

    user_id= await get_user_with_email(drafter_request.to_email_id,db)
    print("user_id from inbox", user_id)
    emailcreate= EmailCreate(
            sender_email= drafter_request.sender_email_id,
            user_id= str(user_id),
            category= response['category'],
            category_confidence_score=response['confidence_score'],
            pii_detected= False, #temporary
            email_response_draft= response['email_output'].email_draft,
            escalated_to_human= False if response['email_output'].confidence==2 else True,
            intent= "awareness",
            preprocessed_email=  response['processed_email_body'],
            requires_response= True if response['needs_response']== "Needs Response" else False,
            received_at= datetime.datetime.now(),
            thread_id= drafter_request.thread_id,
            email_sent= False

                    )
    #add to database
    db_email= await create_email_record(
       emailcreate , db
    )

    if db_email:
        print("Email row inserted succesfully")

    return response

@inbox_manager_router.post("/trigger-n8n/")
def trigger_n8n_send_email_hook(send_email_request: SendEmailRequest):
    """
    Endpoint to trigger the n8n webhook with provided data.
    """
    try:
        # Send the POST request to the n8n webhook

        request= send_email_request.model_dump_json()

        response = requests.post(N8N_WEBHOOK_URL, json=request)
        response.raise_for_status()  # Raise an error for non-2xx status codes
        return {"status": "success", "n8n_response": response.json()}
    except requests.RequestException as e:
        # Handle request errors
        raise HTTPException(status_code=500, detail=f"Request to n8n failed: {str(e)}")