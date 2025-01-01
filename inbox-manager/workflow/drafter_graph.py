
import sys
import os

try:
    # Use __file__ if available
    current_dir = os.path.dirname(__file__)
except NameError:
    # Fallback for interactive environments
    current_dir = os.getcwd()

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(current_dir, "..")))

from agents.drafter import EmailDrafter
from langgraph.graph import StateGraph, MessagesState, START, END
from state import AgentGraphState
from langgraph.prebuilt import ToolNode, tools_condition
from state import state

def create_email_drafter_graph(tools) :

    workflow = StateGraph(AgentGraphState)
    tool_node= ToolNode(tools)
    email_drafter_agent= EmailDrafter(
        model= "claude-3-5-sonnet-20241022",
        state= state,
        server="claude"
    )
    
    print("bind started sucessfully")

    email_drafter_agent.bind_tools(tools)
    print("bind completed sucessfully")
    # Define the two nodes we will cycle between
    workflow.add_node("call_model", email_drafter_agent.call_model)
    workflow.add_node("call_tools", email_drafter_agent.call_tools)

    # workflow.add_node("query_rewriter", email_drafter_agent.query_rewriter)  # Re-writing the question
    # workflow.add_node("generator", email_drafter_agent.generate)

    workflow.add_edge(START, "call_model")

    # Decide whether to tools
    # workflow.add_conditional_edges(
    #     "email_drafter",
    #     # Assess agent decision
    #     tools_condition,
    #     {
    #         # Translate the condition outputs to nodes in our graph
    #         tools: "call_tools",
    #         END: END,
    #     },
    # )
    # workflow.add_conditional_edges("email_drafter", email_drafter_agent.should_continue, ["tools", END])

    # workflow.add_conditional_edges("tools",email_drafter_agent.grade_documents) 
    workflow.add_edge("call_tools", "call_model")

    # workflow.add_edge("generator", END)
    # workflow.add_edge("query_rewriter", "email_drafter")
    email_drafter_graph = workflow.compile()

    return email_drafter_graph