import json
# langchain imports moved inside functions
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy import select

from db.database import SessionLocal
from db.models import OrganizationSettings
from services.email_service import EmailService, EmailConfig
from workflow.state import AgentState
from utils.activity_helper import log_activity_and_notify

from prompts.sales_prompts import INTENT_ANALYZER_PROMPT

class IntentAnalysisResult(BaseModel):
    intent: str = Field(description="The primary intent of the lead (e.g., Interested, Not Interested, Pricing Query, Comparison, Cold)")
    summary: str = Field(description="A brief summary of the conversation history.")
    next_steps: str = Field(description="Recommended next steps for the sales rep.")
    sentiment: str = Field(description="Overall sentiment: Positive, Negative, or Neutral")
    recommended_email: Optional[str] = Field(None, description="A ready-to-send, human-like email draft if the next step involves a follow-up. Keep it concise, professional, and personalized.")

def analyze_email_intent(email_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes a list of email messages to determine the lead's intent.
    """
    if not email_history:
        return {
            "intent": "No Data",
            "summary": "No email history found.",
            "next_steps": "Initiate first contact.",
            "sentiment": "Neutral",
            "recommended_email": "Hi, I noticed we haven't connected yet. I'd love to chat about how we can help with your goals. Let me know if you have time this week."
        }

    # Format history for the prompt
    conversation_text = ""
    for email in sorted(email_history, key=lambda x: x.get('date', ''), reverse=False): # Chronological for analysis
        direction = email.get('direction', 'unknown').upper()
        sender = email.get('from', 'Unknown')
        subject = email.get('subject', 'No Subject')
        body = email.get('text', '')[:500] if email.get('text') else "No Content" # Truncate body
        
        conversation_text += f"---\n[{direction}] From: {sender}\nSubject: {subject}\nBody: {body}\n\n"

    # LLM Setup (Deferred imports)
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import PromptTemplate

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    parser = JsonOutputParser(pydantic_object=IntentAnalysisResult)
    
    prompt = PromptTemplate(
        template=INTENT_ANALYZER_PROMPT,
        input_variables=["conversation_history"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        result = chain.invoke({"conversation_history": conversation_text})
        return result
    except Exception as e:
        print(f"Error creating intent analysis: {e}")
        return {
            "intent": "Error",
            "summary": f"Failed to analyze conversation: {e}",
            "next_steps": "Check logs.",
            "sentiment": "Unknown",
            "recommended_email": None
        }

async def email_history_fetcher_node(state: AgentState):
    """
    Early LangGraph node to fetch raw email history.
    """
    email_id = state.get("email_id")
    if not email_id:
        return {"email_history": []}

    email_history = []
    async with SessionLocal() as db:
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        
        if settings and settings.email_config:
            try:
                config_data = json.loads(settings.email_config)
                if all(k in config_data for k in ["imap_server", "email_user", "email_password"]):
                    config = EmailConfig(**config_data)
                    service = EmailService(config)
                    email_history = service.fetch_email_history(email_id)
                
                # Log Activity if new incoming emails found
                incoming_emails = [e for e in email_history if e.get('direction') == 'incoming']
                if incoming_emails:
                    latest_email = incoming_emails[0]
                    await log_activity_and_notify(
                        db,
                        type="email",
                        title=f"New Email Interaction: {email_id}",
                        description=f"Received: {latest_email.get('subject')}",
                        metadata={"email": email_id, "subject": latest_email.get('subject')},
                        idempotency_key=f"email_interaction:{email_id}:{latest_email.get('subject')}"
                    )
            except Exception as e:
                print(f"Error fetching emails: {e}")

    return {"email_history": email_history}

async def email_intent_analyzer_node(state: AgentState):
    """
    Late LangGraph node (Post-CSO) to analyze intent with strategic guidance.
    """
    email_history = state.get("email_history", [])
    cso_briefing = state.get("cso_strategic_briefing", {})
    
    # 1. Analyze Intent
    # Inject CSO perspective if available
    cso_context = cso_briefing.get("unified_command", {}).get("verdict", "")
    
    analysis = analyze_email_intent(email_history)
    
    # If CSO has a specific command, we can refine the analysis
    if cso_context and analysis.get("intent") == "Interested":
         analysis["next_steps"] = f"CRITICAL: {cso_context}. {analysis.get('next_steps')}"

    return {"intent_analysis": analysis}
