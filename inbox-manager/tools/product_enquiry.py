from langchain_core.tools import tool
from workflow.state import AgentGraphState
@tool("product_enquiry")
def product_enquiry(processed_email_body:str):
    '''use when the query is related to product or service enquiry (eg: how you can help us, pricing, setup requirements, integrations  )'''

    #implement a rag system
    return f"innovize ai helps business automate processes with ai agnets and ml models"

@tool("integrations")
def get_integrations(processed_email_body:str):
    '''use when the query is related to integrations  )'''
    return f"yes our solutions integrate with various platforms"
