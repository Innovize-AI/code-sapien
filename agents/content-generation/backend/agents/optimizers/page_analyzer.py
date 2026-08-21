from agents.llm_node import LLMNode
from workflow.state import AgentGraphState

from langchain_core.prompts import PromptTemplate
from prompts.page_perfector.prompts import PAGE_ANALYZER_PROMPT_TEMPLATE
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

class PageAnalyzer(LLMNode):

    def invoke(self, state:AgentGraphState):

        target_keywords= state['target_keywords']
        scrape_webpage_content= state['scraped_website_content']
        model= self.get_llm(False)

        system_prompt= """You are a useful assistant."""

        human_prompt= PAGE_ANALYZER_PROMPT_TEMPLATE.format(
            target_keywords= target_keywords,
            scrape_webpage_content= scrape_webpage_content
        )

        messages = [
            SystemMessage(content=system_prompt), 
            HumanMessage(content= human_prompt)
        ]

        response= model.invoke(messages)

        page_analysis= response.content

        # state['page_analysis']= page_analysis

        return {"page_analysis":page_analysis}