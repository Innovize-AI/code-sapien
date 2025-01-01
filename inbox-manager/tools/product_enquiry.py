from langchain_core.tools import tool
from workflow.state import AgentGraphState
from utils import get_qdrant_as_retriver
from langchain.tools.retriever import create_retriever_tool
import datetime
from langgraph.types import Command
from typing import Literal
from langchain_core.messages import HumanMessage

# @tool("product_enquiry")
# def product_enquiry(question:str):
#     '''use when the query is related to product or service enquiry (eg: how you can help us, pricing, setup requirements, integrations  )'''

#     retriever= get_qdrant_as_retriver("inbox-manager")

#     relevent_documents= retriever.get_relevant_documents(question)


#     #implement a rag system
#     return f"innovize ai helps business automate processes with ai agnets and ml models"

# @tool("integrations")
# def get_integrations(processed_email_body:str):
#     '''use when the query is related to integrations  )'''
#     return f"yes our solutions integrate with various platforms"


def get_product_enquiry_tool():

    """when the query is related to product(or service) enquiry"""
    from langchain.tools.retriever import create_retriever_tool

    retriever= get_qdrant_as_retriver("inbox-manager")
    print("called product enquiry tool")
    product_enquiry_tool = create_retriever_tool(
        retriever,
        "product_enquiry",
        "use when the query is related to product or service enquiry (eg: how you can help us, pricing, setup requirements, integrations  )",
    )
    return product_enquiry_tool.as_tool()

# @tool
# def calender_availability(time:str):
#     '''use when query related to scheduling meeting or meeting request. Get the calendar availability based on request'''

#     current_time= datetime.datetime.now()
#     # print("current time ", current_time.strftime("%Y-%m-%d"))
#     print("time ", time)

#     return Command(goto="calendar_agent", update={"messages":[HumanMessage(content= time)]}, graph= Command.PARENT)