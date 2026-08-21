from workflow.state import AgentState
from db.database import SessionLocal
from db.crud import match_crm_context

async def crm_lookup_node(state: AgentState):
    """
    Looks up the lead in the local CRMContext table (HubSpot data).
    Identifies if they are a past champion, lost deal, or known prospect.
    """
    email = state.get("email_id")
    li_url = state.get("linkedin_url")
    
    # We use a context manager to get a fresh DB session for the agent node
    async with SessionLocal() as db:
        crm_data = await match_crm_context(db, email=email, linkedin_url=li_url)
        
        if not crm_data:
            return {"crm_context": None}
            
        return {
            "crm_context": {
                "type": crm_data.type,
                "deal_name": crm_data.deal_name,
                "original_company": crm_data.original_company,
                "closed_lost_reason": crm_data.closed_lost_reason,
                "stage": crm_data.deal_stage,
                "hubspot_contact_id": crm_data.hubspot_contact_id
            }
        }
