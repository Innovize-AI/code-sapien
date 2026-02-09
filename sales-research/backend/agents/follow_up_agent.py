from langchain_core.messages import SystemMessage, HumanMessage
import json
from workflow.state import AgentState
from prompts.sales_prompts import FOLLOW_UP_STRATEGY_PROMPT
from models.openai_models import get_open_ai

def follow_up_strategy_node(state: AgentState):
    """Crafts a tailored follow-up strategy for existing prospect relationships."""
    email_history = state.get("email_history", [])
    meeting_notes = state.get("meeting_notes", "No meeting notes available.")
    pain_points = state.get("target_pain_points", "")
    solutions = state.get("strategic_solutions", "")
    journey_analysis = state.get("buyer_journey_analysis", {})

    intelligence_context = {
        "email_history": email_history,
        "meeting_notes": meeting_notes,
        "pain_points": pain_points,
        "solutions": solutions,
        "journey_context": journey_analysis
    }

    messages = [
        SystemMessage(content=FOLLOW_UP_STRATEGY_PROMPT),
        HumanMessage(content=f"DRAFT FOLLOW-UP STRATEGY: {json.dumps(intelligence_context)}")
    ]

    try:
        model = get_open_ai(model="gpt-4o-mini", temperature=0.7)
        response = model.invoke(messages)
        return {"follow_up_strategy": response.content}
    except Exception as e:
        print(f"Error in follow_up_strategy_node: {e}")
        return {"follow_up_strategy": "Error generating follow-up strategy."}
