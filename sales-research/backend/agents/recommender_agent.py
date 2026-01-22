from langchain_core.messages import SystemMessage, HumanMessage
import json
from workflow.state import AgentState
from prompts.sales_prompts import GLOBAL_STRATEGY_ADVISOR_PROMPT
from models.openai_models import get_open_ai
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class BuyerJourneyStage(str, Enum):
    AWARENESS = "Awareness"
    CONSIDERATION = "Consideration"
    DECISION = "Decision"
    NEGOTIATING = "Negotiating"
    CLOSED = "Closed"

class StrategicRecommendation(BaseModel):
    journey_stage: BuyerJourneyStage = Field(description="The current stage of the prospect in the buyer journey.")
    optimal_play: str = Field(description="The single most effective next action to take.")
    strategic_reasoning: str = Field(description="Explanation of why this stage and play were chosen, backed by evidence.")
    sentiment_score: int = Field(description="Lead sentiment/heat score from 1-100.", ge=1, le=100)
    urgency_level: str = Field(description="High, Medium, or Low urgency.")

def strategic_recommender_node(state: AgentState):
    """Determines the prospect's stage and recommends the next strategic move."""
    lead_score_analysis = state.get("lead_score_analysis", {})
    user_profile_analysis = state.get("user_profile_analysis", {})
    email_history = state.get("email_history", [])
    meeting_notes = state.get("meeting_notes", "No meeting notes available.")
    intent_analysis = state.get("intent_analysis", {})

    # Package intelligence for the recommender
    intelligence_context = {
        "scoring_intent": {
            "scores": lead_score_analysis,
            "intent": intent_analysis
        },
        "social_persona": user_profile_analysis,
        "email_history": email_history,
        "meeting_notes": meeting_notes
    }

    messages = [
        SystemMessage(content=GLOBAL_STRATEGY_ADVISOR_PROMPT),
        HumanMessage(content=f"PROSPECT INTELLIGENCE: {json.dumps(intelligence_context)}")
    ]

    try:
        model = get_open_ai(model="gpt-4o-mini", temperature=0)
        structured_llm = model.with_structured_output(StrategicRecommendation)
        response = structured_llm.invoke(messages)
        
        if not response:
             return {"buyer_journey_analysis": {}}
             
        return {"buyer_journey_analysis": response.dict()}
    except Exception as e:
        print(f"Error in strategic_recommender_node: {e}")
        return {"buyer_journey_analysis": {}}
