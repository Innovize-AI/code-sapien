from langchain_community.document_loaders import WebBaseLoader
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import WEBSITE_ANALYZER_PROMPT
from models.openai_models import get_open_ai

def scrape_webpages(state: AgentState) -> dict:
    """Use requests and bs4 to scrape the provided web pages for detailed information."""
    website = state["website"]
    
    if not website:
        return {"scraped_website_content": "Could not scrape empty website"}

    loader = WebBaseLoader(website)
    docs = loader.load()
    scraped_content = "\n\n".join([doc.page_content for doc in docs])
    
    return {"scraped_website_content": scraped_content}

def website_analyzer(state: AgentState):
    messages = [
        SystemMessage(content=WEBSITE_ANALYZER_PROMPT), 
        HumanMessage(content=state['scraped_website_content'])
    ]
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"website_analysis": response.content}
