from agents.llm_node import LLMNode
from workflow.state import AgentGraphState
from prompts.page_perfector.prompts import DESIGN_INSTRUCTIONS_PROMPT_TEMPLATE
from langchain_core.messages import HumanMessage, SystemMessage
class DesignInstructor(LLMNode):


    def invoke(self, state:AgentGraphState):

        page_analysis= state['page_analysis']
        scrape_webpage_content= state['scraped_website_content']
        model= self.get_llm(False)

        system_prompt= """You are an assistant that manages designers and developers and tells them what to do. 
        Never provide a general best practice. Any instruction you provide must be hyper-specific to the task at hand.
"""

        human_prompt= DESIGN_INSTRUCTIONS_PROMPT_TEMPLATE.format(
            scrape_webpage_content= scrape_webpage_content,
            page_analysis= page_analysis
        )

        messages = [
            SystemMessage(content=system_prompt), 
            HumanMessage(content= human_prompt)
        ]

        response= model.invoke(messages)

        design_instructions= response.content

        # state['design_instructions']= design_instructions

        return {"design_instructions": design_instructions}
