from langchain_core.tools import tool
import datetime 
from langgraph.prebuilt import ToolNode
from workflow.state import AgentGraphState
from langgraph.types import Command

@tool("calender_availability")
def calender_availability(time:str):
    '''use when query related to scheduling meeting or meeting request. Get the calendar availability based on request'''

    current_time= datetime.datetime.now()
    # print("current time ", current_time.strftime("%Y-%m-%d"))
    print("time ", time)
    return f"sry i am not available {time}"
    