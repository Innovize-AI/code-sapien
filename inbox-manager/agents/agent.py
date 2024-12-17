
from agents.llm_node import LLMNode
from langgraph.graph import StateGraph, MessagesState, START, END

class Agent(LLMNode):

   def bind_tools(self,tools):
        
        self.model_with_tools = self.get_llm().bind_tools(tools, strict=True)

        return self.model_with_tools
    
   def invoke(self, message):
        
        return self.model_with_tools.invoke(message)