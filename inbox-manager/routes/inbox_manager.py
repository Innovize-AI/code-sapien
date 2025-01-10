from fastapi import APIRouter, Query
from workflow.graph import create_Workflow
from pydantic import BaseModel

inbox_manager_router = APIRouter(prefix='/generate-draft', tags=['Inbox Manager'],responses={404: {"description": "Not found"}},)

workflow= create_Workflow()


class DrafterRequest(BaseModel):
    raw_email_body:str
    company_domain_name:str
    sender_email_id:str



@inbox_manager_router.post("/")
@inbox_manager_router.post("")
def run_workflow(drafter_request: DrafterRequest):

    response= workflow.invoke({
    
    "raw_email_body": drafter_request.raw_email_body,
    "company_domain_name": drafter_request.company_domain_name,
    "sender_email_id": drafter_request.sender_email_id
    
    })

    return response
