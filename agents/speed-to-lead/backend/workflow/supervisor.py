"""
Supervisor node — routes inbound messages to the correct agent.

Audio messages get an immediate "please send as text" reply and skip the lead agent.
Everything else → lead_agent.
"""

from workflow.state import LeadState


def supervisor(state: LeadState) -> LeadState:
    if state["message_type"] == "audio":
        state["active_agent"] = "voice_note"
    else:
        state["active_agent"] = "lead_agent"
    return state


async def voice_note_node(state: LeadState) -> LeadState:
    state["response_text"] = "Can you send that as a text? Can't process voice notes here."
    state["path_taken"] = "voice_note"
    state["tools_called"] = []
    return state
