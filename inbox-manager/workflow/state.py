#changes according to design
from typing import TypedDict, Annotated
from langgraph.graph import MessagesState,add_messages
from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field

class EmailOutput(BaseModel):
    """email output structure"""

    confidence: str = Field(
        description="confidence of the relevancy of the draft generated (0 or 1 or 2)"
    )
    email_draft: str = Field(
         description="email draft generated"
    )
    hand_off_to_human: str= Field("whether to handle to human agent  'yes' or 'no ")

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
    email_output:EmailOutput

    #intermediate messages
    messages: Annotated[list[AnyMessage], add_messages]

    




state= AgentGraphState(
    raw_email_body= ""
) 