from agents.llm_node import LLMNode
from workflow.state import AgentGraphState

from prompts.page_perfector.prompts import EEAT_REVISOR_PROMPT_TEMPLATE
from langchain_core.messages import HumanMessage, SystemMessage
class EEATRevisor(LLMNode):

    def invoke(self, state:AgentGraphState):

        first_draft= state['first_draft']
        eeat_analysis= state['eeat_analysis']
        model= self.get_llm(False)

        system_prompt= """Only output the EEAT Analysis and action items. Use markdown format.."""

        human_prompt= EEAT_REVISOR_PROMPT_TEMPLATE.format(
            first_draft= first_draft,
            eeat_analysis= eeat_analysis
        )
        messages = [
            SystemMessage(content=system_prompt), 
            HumanMessage(content= human_prompt)
        ]

        response= model.invoke(messages)

        eeat_revision= response.content

        # state['eeat_revision']= eeat_revision

        return {"eeat_revision":eeat_revision }
