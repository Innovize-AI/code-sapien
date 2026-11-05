"""
LangGraph graph — signal_extractor → supervisor → lead_agent | voice_note_node
"""

from langgraph.graph import StateGraph, END

from workflow.state import LeadState
from workflow.supervisor import supervisor, voice_note_node
from agents.signal_extractor import signal_extractor_node
from agents.lead_agent import lead_agent_node


def build_graph():
    graph = StateGraph(LeadState)

    graph.add_node("signal_extractor", signal_extractor_node)
    graph.add_node("supervisor",        supervisor)
    graph.add_node("lead_agent",        lead_agent_node)
    graph.add_node("voice_note",        voice_note_node)

    graph.set_entry_point("signal_extractor")
    graph.add_edge("signal_extractor", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        lambda s: s["active_agent"],
        {
            "lead_agent":  "lead_agent",
            "voice_note":  "voice_note",
        },
    )

    graph.add_edge("lead_agent", END)
    graph.add_edge("voice_note", END)

    return graph.compile()


lead_agent_graph = build_graph()
