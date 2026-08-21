#changes according to design
from typing import Annotated, TypedDict
import operator
from langgraph.graph import MessagesState,add_messages
from langchain_core.messages import AnyMessage

class AgentGraphState(TypedDict):
    #
    # input
    target_keywords: Annotated[list[str], operator.add]
    url_to_scrape: Annotated[str, operator.add]

    #intermediate
    messages: Annotated[list[AnyMessage], add_messages]

    scraped_website_content: str
    keyword_knowledge: str
    brand_knowledge: str
    p_quotes: str
    p_statistics:str
    p_general_info: str
    page_analysis: str

    first_draft: str
    eeat_analysis: str
    eeat_revision:str
    wireframe:str
    design_instructions: str
    entity_analysis:str


    #output
    final_draft: str
