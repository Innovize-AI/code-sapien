from agents.llm_node import LLMNode
from workflow.state import AgentGraphState

from prompts.page_perfector.prompts import EEAT_ANALYZER_PROMPT_TEMPLATE
from langchain_core.messages import HumanMessage, SystemMessage
class EEATAnalyzer(LLMNode):

    def invoke(self, state:AgentGraphState):

        first_draft= state['first_draft']
        scrape_webpage_content= state['scraped_website_content']
        model= self.get_llm(False)

        system_prompt= """Only output the EEAT Analysis and action items. Use markdown format.."""

        human_prompt= EEAT_ANALYZER_PROMPT_TEMPLATE.format(
            first_draft= first_draft,
        )

        messages = [
            SystemMessage(content=system_prompt), 
            HumanMessage(content= human_prompt)
        ]

        response= model.invoke(messages)

        eeat_analysis= response.content

        # state['eeat_analysis']= eeat_analysis

        return {"eeat_analysis":eeat_analysis}