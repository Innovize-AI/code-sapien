from agents.llm_node import LLMNode
from workflow.state import AgentGraphState, RelevantThreadMessages
from prompts.prompts import RELEVANT_THREAD_PROMPT_TEMPLATE

class RelevantThreadMessagesExtractor(LLMNode):

    def invoke(self, state: AgentGraphState):

        thread_messages= state['thread_messages']

        prompt= RELEVANT_THREAD_PROMPT_TEMPLATE.format(thread_messages= thread_messages)

        chain= RELEVANT_THREAD_PROMPT_TEMPLATE | self.get_llm(json_model=False).with_structured_output(RelevantThreadMessages)

        response= chain.invoke({"thread_messages": thread_messages})

        return {"thread_messages":response}