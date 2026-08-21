from agents.llm_node import LLMNode
from workflow.state import AgentGraphState

from langchain_core.messages import HumanMessage, SystemMessage
from prompts.page_perfector.prompts import WIREFRAME_CREATOR_PROMPT_TEMPLATE
class WireFrameCreator(LLMNode):

    def invoke(self, state:AgentGraphState):

        design_instructions= state['design_instructions']
        first_draft= state['first_draft']
        model= self.get_llm(False)

        system_prompt= """You are a wireframe assistant.."""

        human_prompt= WIREFRAME_CREATOR_PROMPT_TEMPLATE.format(
            design_instructions= design_instructions,
            first_draft= first_draft
        )
        messages = [
            SystemMessage(content=system_prompt), 
            HumanMessage(content= human_prompt)
        ]

        response= model.invoke(messages)

        wireframe= response.content

        # state['wireframe']= wireframe

        return {"wireframe":wireframe}
