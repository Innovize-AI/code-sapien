#changes according to design
from typing import TypedDict, Annotated
from langgraph.graph import MessagesState,add_messages
from langchain_core.messages import AnyMessage

class AgentGraphState(TypedDict):
    #
    sender_email_id: str
    to_email_id:str
    raw_email_body:str
    processed_email_body:str
    email_thread_history: str
    company_domain_name:str

    #categorize
    category:str
    needs_response:bool
    confidence_score:float

    #email draft
    email_draft:str

    #intermediate messages
    messages: Annotated[list[AnyMessage], add_messages]

    

state= AgentGraphState(
    raw_email_body= ""
) 