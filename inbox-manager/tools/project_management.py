from langchain_core.tools import tool

from workflow.state import AgentGraphState
@tool("project_management")
def project_management(state:AgentGraphState):

    '''Get details about a client project status, details etc sender_email_id: email id of sender'''
    return f"your project is in progress {state['sender_email_id']}"
