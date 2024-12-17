from langchain_core.tools import tool

from langgraph.prebuilt import ToolNode
from workflow.state import AgentGraphState

@tool("calender_availability")
def calender_availability(time:str):
    '''Get the calendar availability based on request'''
    return f"meeting scheduled at {time}"
    
