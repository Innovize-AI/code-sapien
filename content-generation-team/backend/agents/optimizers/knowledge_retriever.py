from agents.react_agent import ReactAgent
from langgraph.types import Command
from workflow.state import AgentGraphState
from langgraph.types import Command
from typing import Literal
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel


class KnowledgeRetriever(ReactAgent):

    def create_agent_graph(self, state:AgentGraphState):

        workflow = StateGraph(AgentGraphState)
        workflow.add_node("call_model", self.call_model)
        workflow.add_node("call_tools", self.call_tools)
        workflow.add_edge(START, "call_model")
        workflow.add_edge("call_tools", "call_model")
        calendar_graph = workflow.compile()

        return calendar_graph

    def call_model(self, state:AgentGraphState)-> Command[Literal["call_tools","email_generator" ,"__end__"]]:

        # processed_email= state['processed_email_body']
        # state['messages']=[SystemMessage(content= EMAIL_DRAFTER_PROMPT) , HumanMessage(content= processed_email)]
        messages= state['messages']
        # print(processed_email)
        print("messages", messages)
        # last_message= messages[-1]
        # self.model_with_tools.invoke("what is your pricing and lets setup a time for a call at 3PM next tuesday??").tool_calls
        formatted_messages = self.format_messages(messages)

        prompt = PromptTemplate.from_template(
                """
    "Write responses without starting with phrases like 'Here is', "Regarding" or similar introductory phrases. Avoid ending responses with conclusions or questions. Maintain a concise, direct, and engaging tone throughout.


    ## IMPORTANT(this is crucial for the success of the company):  
    1) Never skip important information( e.g: next tuesday 3PM, coming tuesday 10AM(UK time))  when you are passing arguments to the tools. 
    2) Never end your responses with followup questions if there is any insufficient information.(e.g: Would you like to continue,  Would you like to check availability and so on)
    3)If you have a response from a tool that answers the question, generate the final answer with findings included in the tool message. Never loop through a tool and you can call a tool only once at maximum.

    input: {messages}


    """) 

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
