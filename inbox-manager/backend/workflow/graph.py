from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from langgraph.prebuilt import ToolNode
import os
import getpass
import sys



def _set_if_undefined(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Please provide your {var}")


_set_if_undefined("OPENAI_API_KEY")
_set_if_undefined("LANGCHAIN_API_KEY")
# _set_if_undefined("TAVILY_API_KEY")

# Optional, add tracing in LangSmith.
# This will help you visualize and debug the control flow
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "inbox-manager"


# Get the parent directory
parent_dir = os.path.abspath(os.path.join(os.getcwd(), ".."))

# Add parent directory to sys.path
sys.path.append(parent_dir)

from tools.product_enquiry import get_product_enquiry_tool
# from tools.product_enquiry import get_integrations
from tools.calendar import calender_check
from tools.project_management import project_management

from typing import Annotated
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from utils import make_handoff_tool

drafter_tools = [get_product_enquiry_tool(),make_handoff_tool(agent_name="calendar_agent")]
calendar_tools = [calender_check, make_handoff_tool(agent_name="email_drafter")]

from typing import Literal

from langgraph.graph import StateGraph, MessagesState, START, END
from agents.categorizer import EmailCategorizer
from agents.email_generator import EmailGenerator
from agents.node import Node
from workflow.state import AgentGraphState
from agents.drafter import EmailDrafter
from agents.calendar import CalendarAgent
from agents.preprocessor import Preprocess
from agents.relevant_threads import RelevantThreadMessagesExtractor


def create_Workflow():

    def should_respond(state: AgentGraphState) -> Literal["email_drafter", "end"]:
        """Complex routing logic"""
        if state["needs_response"] == "Needs Response":
            print("should start the email drafter model")
            return "email_drafter"
        return END

    email_categorizer= EmailCategorizer(
        model="gpt-4o-mini",
        server="openai"
    )

    preprocess_email= Preprocess()

    #get relevant threads from the current email
    relevant_thread_messages= RelevantThreadMessagesExtractor(model="gpt-4o-mini", server="openai")

    email_generator= EmailGenerator( model= "gpt-4o-mini", server= "openai")

    email_drafter_agent= EmailDrafter(
            model= "claude-3-5-sonnet-20241022",
            server="claude"
        )
    email_drafter_agent.bind_tools([get_product_enquiry_tool(), make_handoff_tool(agent_name="calendar_agent")])
    calendar_agent= CalendarAgent(
            model= "claude-3-5-sonnet-20241022",
            server="claude"
        )
    calendar_agent.bind_tools( [calender_check,make_handoff_tool(agent_name="email_drafter")])

    def final_node(state: AgentGraphState):
        email_draft =state['email_output'].email_draft
        confidence= state['email_output'].confidence
        hand_off_human=state['email_output'].hand_off_to_human
        print("email draft final node" ,email_draft)

        return state

    workflow = StateGraph(AgentGraphState)

    workflow.add_node("email_preprocessor",preprocess_email.preprocess_email)
    workflow.add_node("email_categorizer", email_categorizer.invoke)
    workflow.add_node("relevant_thread_messages", relevant_thread_messages.invoke)
    workflow.add_node("email_drafter",email_drafter_agent.create_agent_graph)
    workflow.add_node("calendar_agent", calendar_agent.create_agent_graph)
    workflow.add_node("final_response", final_node)
    workflow.add_node("email_generator", email_generator.generate)


    workflow.add_edge(START, "email_preprocessor")
    workflow.add_edge("email_preprocessor","email_categorizer")
    workflow.add_edge("email_preprocessor","relevant_thread_messages" )
    workflow.add_edge("relevant_thread_messages","email_categorizer")
    workflow.add_conditional_edges("email_categorizer", should_respond, ["email_drafter", END])
    workflow.add_edge("email_generator","final_response")
    workflow.add_edge("final_response",END)


    graph = workflow.compile()

    return graph

