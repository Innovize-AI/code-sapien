from agents.agent import Agent
from workflow.state import AgentGraphState
from langgraph.graph import END
from workflow.state import state
from langgraph.graph import StateGraph, MessagesState, START, END

class ReactAgent(Agent):

    def bind_tools(self,tools):    

        self.model_with_tools = self.get_llm().bind_tools(tools)

        return self.model_with_tools
    
    def should_continue(self, state:AgentGraphState):
        messages = state["messages"]

        print("messages in should continue", messages)
        last_message = messages[-1]
        print("last_message", last_message)
        if last_message.tool_calls:
            print("call tool")
            return "tools"
        else:
            print("ended all tools called ")    
            return END


    def call_model(self, state:AgentGraphState):
        messages = state["messages"]
        response = self.model_with_tools.invoke(messages)
        return {"messages": [response]}
    
