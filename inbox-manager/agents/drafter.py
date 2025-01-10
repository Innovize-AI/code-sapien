from agents.react_agent import ReactAgent
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from prompts.prompts import EMAIL_PREPROCCESSOR_SYSTEM_PROMPT, EMAIL_DRAFTER_PROMPT, EMAIL_DRAFTER_PROMPT_TEMPLATE, EMAIL_INTENT_PROMPT_TEMPLATE
from workflow.state import AgentGraphState
from langgraph.graph import END
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from langgraph.types import Command
from typing import Literal
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from workflow.state import AgentGraphState
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel

class EmailIntent(BaseModel):
    intent_type: str
    justification: str

class EmailDrafter(ReactAgent):

    ''' Email drafter react agent'''

    def create_agent_graph(self, state: AgentGraphState):

        workflow = StateGraph(AgentGraphState)
        #add resources based on the question intent and add any resources if required
        workflow.add_node("intent_detector", self.intent_identifier)
        workflow.add_node("call_model", self.call_model)
        workflow.add_node("call_tools", self.call_tools)
        workflow.add_edge("intent_detector", "call_model")
        workflow.add_edge(START, "intent_detector")
        workflow.add_edge("call_tools", "call_model")
        email_drafter_graph = workflow.compile()

        return email_drafter_graph
      
    def bind_tools(self,tools):

        self.tools= tools    
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
            # self.update_state("email_draft", last_message)
            return END

   
    
#     def call_model(self, state:AgentGraphState):

#         # processed_email= state['processed_email_body']
#         # state['messages']=[SystemMessage(content= EMAIL_DRAFTER_PROMPT) , HumanMessage(content= processed_email)]
#         messages= state['messages']
#         # print(processed_email)
#         print("messages", messages)
#         # self.model_with_tools.invoke("what is your pricing and lets setup a time for a call at 3PM next tuesday??").tool_calls
#         formatted_messages = self.format_messages(messages)

#         prompt = PromptTemplate.from_template(
#                 """
# "Write responses without starting with phrases like 'Here is' or similar introductory phrases. Avoid ending responses with conclusions or questions. Maintain a concise, direct, and engaging tone throughout.
# {messages}. You can use calendar_agent if there is need aout scheduling a meeting or any query related to meetings
# """
#                 ) 

#         chain = prompt | self.model_with_tools
#         response= chain.invoke({"messages": messages})
#         print("response from call model", response.content)
#         return {"messages":[response]}
# 
    def get_tools_dict(self):
        tools_by_name = {tool.name: tool for tool in self.tools}
        return tools_by_name

    
    def call_model(self, state:AgentGraphState)-> Command[Literal["call_tools","email_generator", "__end__"]]:

        # processed_email= state['processed_email_body']
        # state['messages']=[SystemMessage(content= EMAIL_DRAFTER_PROMPT) , HumanMessage(content= processed_email)]
        messages= state['messages']
        # print(processed_email)
        print("messages", messages)
        # self.model_with_tools.invoke("what is your pricing and lets setup a time for a call at 3PM next tuesday??").tool_calls
        formatted_messages = self.format_messages(messages)

        prompt = PromptTemplate.from_template(
                """
"Write responses without starting with phrases like 'Here is'. "Regarding" or similar introductory phrases. Avoid ending responses with conclusions or questions. Maintain a concise, direct, and engaging tone throughout.
{messages}.

## IMPORTANT(this is crucial for the success of the company):  
1) Never skip important information( e.g: next tuesday 3PM, coming tuesday 10AM(UK time))  when you are passing arguments to the tools. 
2) Never end your responses with followup questions if there is any insufficient information..(e.g: Would you like to continue,  Would you like to check availability and so on)
3) Determine if you have necessary answers and stop the execution, if all answers are found.
4)If you have a response from a tool that answers the question, generate the final answer with findings included in the tool message. you can call a tool for a maximiun of 3 times only.
5) Always include only one relavant marketing material in your output response based on the funnel stage.
6) Your response should never include additional details not related to question and included marketing material.
7) if the response from the tool is not relevant to question, output as you were unable to find the answer."""
        )

        chain = prompt | self.model_with_tools
        response= chain.invoke({"messages": messages})
        if len(response.tool_calls) > 0:
            return Command(goto="call_tools", update={"messages": [response]})
        print("response from call model", response.content)

        return Command(goto="email_generator", update={"messages": [response]}, graph= Command.PARENT)

    
    def call_tools(self, state: AgentGraphState) -> Command[Literal["call_model"]]:
        tool_calls = state["messages"][-1].tool_calls
        tools_by_name= self.get_tools_dict()
        results = []
        for tool_call in tool_calls:
            tool_ = tools_by_name[tool_call["name"]]
            tool_input_fields = tool_.get_input_schema().model_json_schema()[
                "properties"
            ]

            # this is simplified for demonstration purposes and
            # is different from the ToolNode implementation
            if "state" in tool_input_fields:
                # inject state
                tool_call = {**tool_call, "args": {**tool_call["args"], "state": state}}

            tool_response = tool_.invoke(tool_call)
            if isinstance(tool_response, ToolMessage):
                results.append(Command(update={"messages": [tool_response]}))

            # handle tools that return Command directly
            elif isinstance(tool_response, Command):
                results.append(tool_response)

        # NOTE: nodes in LangGraph allow you to return list of updates, including Command objects
        return results
    
    
    
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

    def intent_identifier(self, state: AgentGraphState):

        # Literal["awareness","interest","consideration","decision","disengaged","follow-up"]
        messages = state["messages"]

        chain= EMAIL_INTENT_PROMPT_TEMPLATE | self.get_llm(json_model=False).with_structured_output(EmailIntent)

        response= chain.invoke({"input_email": messages})

        print(response)

        if response.intent_type== "awareness":
            return {"messages":[HumanMessage("Add this the question, share either Introductory Video or Product Brochure ")]}
        elif response.intent_type=="interest":
            return {"messages":[HumanMessage("Add this the question, share either Product Brochure or some case studies")]}
        elif response.intent_type=="consideration":
            return {"messages":[HumanMessage("Add this the question, share either Feature Comparison Guide or Demo Video")]}
        elif response.intent_type=="decision":
            return {"messages":[HumanMessage("Add this the question, share either Implementation Plan Pricing Guide Training Resource Customer Testimonial Collection")]}

        return  state
