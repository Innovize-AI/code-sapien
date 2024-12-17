from agents.react_agent import ReactAgent
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from prompts.prompts import EMAIL_PREPROCCESSOR_SYSTEM_PROMPT, EMAIL_DRAFTER_PROMPT, EMAIL_DRAFTER_PROMPT_TEMPLATE
from workflow.state import AgentGraphState
from langgraph.graph import END

class EmailDrafter(ReactAgent):

    ''' Email drafter react agent'''

    def bind_tools(self,tools):

            
        self.model_with_tools = self.get_llm(json_model=False).bind_tools(tools)

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
            print("email draft", state['messages'][-1].content)
            state["email_draft"]= last_message.content
            print("updated state successfully") 
            # self.update_state("email_draft", last_message)
            return END

   
    
    def call_model(self, state:AgentGraphState):

        # processed_email= state['processed_email_body']
        # state['messages']=[SystemMessage(content= EMAIL_DRAFTER_PROMPT) , HumanMessage(content= processed_email)]
        messages= state['messages']
        # print(processed_email)
        print("messages", messages)
        # self.model_with_tools.invoke("what is your pricing and lets setup a time for a call at 3PM next tuesday??").tool_calls
        formatted_messages = self.format_messages(messages)

        response = self.model_with_tools.invoke(messages)

        print("response from call model", response.content)
        return {"messages":[response]}
    

    def format_messages(self,messages):
        """
        Converts LangChain message objects into the required dict format.
        """
        formatted = []
        for message in messages:
            if isinstance(message, HumanMessage):
                formatted.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                formatted.append({"role": "assistant", "content": message.content})
            elif isinstance(message, SystemMessage):
                formatted.append({"role": "system", "content": message.content})
        return formatted
    
    # messages=[HumanMessage(content=processed_email)]
