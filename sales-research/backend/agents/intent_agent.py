import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from sqlalchemy import select

from db.database import SessionLocal
from db.models import OrganizationSettings
from services.email_service import EmailService, EmailConfig
from workflow.state import AgentState

class IntentAnalysisResult(BaseModel):
    intent: str = Field(description="The primary intent of the lead (e.g., Interested, Not Interested, Pricing Query, Comparison, Cold)")
    summary: str = Field(description="A brief summary of the conversation history.")
    next_steps: str = Field(description="Recommended next steps for the sales rep.")
    sentiment: str = Field(description="Overall sentiment: Positive, Negative, or Neutral")

def analyze_email_intent(email_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes a list of email messages to determine the lead's intent.
    """
    if not email_history:
        return {
            "intent": "No Data",
            "summary": "No email history found.",
            "next_steps": "Initiate first contact.",
            "sentiment": "Neutral"
        }

    # Format history for the prompt
    conversation_text = ""
    for email in sorted(email_history, key=lambda x: x.get('date', ''), reverse=False): # Chronological for analysis
        direction = email.get('direction', 'unknown').upper()
        sender = email.get('from', 'Unknown')
        subject = email.get('subject', 'No Subject')
        body = email.get('text', '')[:500] if email.get('text') else "No Content" # Truncate body
        
        conversation_text += f"---\n[{direction}] From: {sender}\nSubject: {subject}\nBody: {body}\n\n"

    # LLM Setup
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    parser = JsonOutputParser(pydantic_object=IntentAnalysisResult)
    
    prompt = PromptTemplate(
        template="""You are a senior sales strategist. Analyze the following email conversation history between a sales rep and a lead.
        
        Determine the lead's current Intent, summarize the interaction, suggest the Next Best Action, and gauge the Sentiment.
        
        <conversation_history>
        {conversation_history}
        </conversation_history>
        
        {format_instructions}
        """,
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
            "sentiment": "Unknown"
        }

async def email_history_node(state: AgentState):
    """
    LangGraph node to fetch email history and analyze intent.
    """
    email_id = state.get("email_id")
    print(f"DEBUG email_history_node: email_id = {email_id}")
    
    if not email_id:
        print("No email_id in state, skipping email history fetch.")
        return {"email_history": [], "intent_analysis": {}}

    email_history = []
    
    # 1. Fetch Credentials from DB
    async with SessionLocal() as db:
        result = await db.execute(select(OrganizationSettings).limit(1))
        settings = result.scalars().first()
        
        if settings and settings.email_config:
            try:
                config_data = json.loads(settings.email_config)
                print(f"DEBUG: Loaded email config: {list(config_data.keys())}")
                # Ensure all required fields are present
                if all(k in config_data for k in ["imap_server", "email_user", "email_password"]):
                    config = EmailConfig(**config_data)
                    service = EmailService(config)
                    print(f"Fetching email history for {email_id}...")
                    email_history = service.fetch_email_history(email_id)
                    print(f"DEBUG: Fetched {len(email_history)} emails")
                else:
                    print("Incomplete email config in DB.")
            except Exception as e:
                print(f"Error parsing email config or fetching emails: {e}")
        else:
            print("No email config found in settings.")

    # 2. Analyze Intent (even if empty, to return consistent structure)
    analysis = analyze_email_intent(email_history)
    print(f"DEBUG: Intent analysis result: {analysis}")
    
    result = {
        "email_history": email_history, 
        "intent_analysis": analysis
    }
    print(f"DEBUG: Returning from email_history_node: email_history length = {len(email_history)}")
    
    return result
