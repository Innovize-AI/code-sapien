from agents.react_agent import ReactAgent
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from prompts.prompts import EMAIL_PREPROCCESSOR_SYSTEM_PROMPT, EMAIL_DRAFTER_PROMPT, EMAIL_DRAFTER_PROMPT_TEMPLATE
from workflow.state import AgentGraphState
from langgraph.graph import END
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

class CalendarAgent(ReactAgent):

    ''' Calendar react agent'''

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
            return END

   
    
    def call_model(self, state:AgentGraphState):

        # processed_email= state['processed_email_body']
        # state['messages']=[SystemMessage(content= EMAIL_DRAFTER_PROMPT) , HumanMessage(content= processed_email)]
        messages= state['messages']
        # print(processed_email)
        print("messages", messages)
        # self.model_with_tools.invoke("what is your pricing and lets setup a time for a call at 3PM next tuesday??").tool_calls
        formatted_messages = self.format_messages(messages)

        prompt = PromptTemplate.from_template(
                """
"Write responses without starting with phrases like 'Here is' or similar introductory phrases. Avoid ending responses with conclusions or questions. Maintain a concise, direct, and engaging tone throughout.
{messages}.
""") 

        chain = prompt | self.model_with_tools
        response= chain.invoke({"messages": messages})
        print("response from call model", response.content)
        return {"messages":[response]}
    
    
    def generate(self,state:AgentGraphState):
        """
        Generate answer

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with re-phrased question
        """
        print("---GENERATE---")
        messages = state["messages"]
        question = messages[0].content
        last_message = messages[-1]

        docs = last_message.content 
        print("calling generate function  ", docs)
        draft_prompt = PromptTemplate.from_template(
            EMAIL_DRAFTER_PROMPT
            )
        # Chain
        rag_chain =  draft_prompt | self.get_llm(json_model=False) | StrOutputParser()

        # Run
        response = rag_chain.invoke({"context": docs, "question": question})
        return {"messages": [response]}
    

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
