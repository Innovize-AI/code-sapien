import os
from tabnanny import verbose
from typing import overload
from click import prompt
from langchain_core.agents import AgentAction,AgentFinish,AgentStep
from langchain_core.runnables import Runnable

from langchain.agents import AgentExecutor, create_react_agent

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate,HumanMessagePromptTemplate
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage
from regex import A
from tools.retreival.retreiver import get_rag_tool
from tools.search import get_search_tool
from langchain_community.tools.tavily_search import TavilySearchResults

from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser

from models.chat_models import Message
import tools.slack

global agentExecutor

import asyncio
from langchain.agents import Agent
from langchain.prompts import (ChatPromptTemplate, HumanMessagePromptTemplate,
                               MessagesPlaceholder,
                               SystemMessagePromptTemplate)

from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from slack_sdk import WebClient

from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool, StructuredTool, Tool

# How to do a search over docs with conversation:
#https://langchain.readthedocs.io/en/latest/modules/memory/examples/adding_memory_chain_multiple_inputs.html
# People talking about the parsing error: https://github.com/hwchase17/langchain/issues/1657


# DEFAULT_MODEL="gpt-3.5-turbo"
# UPGRADE_MODEL="gpt-4"
# DEFAULT_TEMPERATURE=0.3


tools=[get_rag_tool(),get_search_tool()]

llm= ChatOpenAI(api_key= os.environ.get("OPEN_API_SECRET"), temperature=0, model= "gpt-4o")


class SlackAgent :
    def __init__(
        self, bot_name:str, slack_client:WebClient
    ):
        # super().__init__()
        self.bot_name = bot_name
        self.agent = None
        self.model_temperature = None
        self.slack_client = slack_client
        self.lock = asyncio.Lock()
    

    async def create_slack_agent(self,sender_user_info,channel_id, message, thread_history):

        from tools.slack.create_thread import create_new_thread_tool   

        # add all the tools of slack 
        # model_facts = f"You are based on the OpenAI model {self.model_name}. Your 'creativity temperature' is set to {self.model_temperature}."
        tools=[get_rag_tool(),get_search_tool(),create_new_thread_tool]

        slack_system_prompt=  SystemMessagePromptTemplate.from_template(
                    f"""The following is a Slack chat thread between users and you, a Slack bot named {self.bot_name}.
                    You are funny and smart, and you are here to help.
                    If you are not confident in your answer, you say so, because you know that is helpful.
                    Since you are responding in Slack, you format your messages in Slack markdown, and you LOVE to use Slack emojis to convey emotion.
                    """
        )
        general_system_prompt= SystemMessagePromptTemplate.from_template(

                    f"""You are a helpful assistant.Follow the below instructions .

                    
                    1)IMPORTANT "Only use this instruction if {thread_history} in not empty.
                    Always check the question asked if its off-topic from the thread_history. 
                    if it is off-topic you will say that its off topic in the same thread and create a new thread in the same channel 
                    using create_new_thread_tool with {channel_id},{sender_user_info.get("id")},{message}, .

                    2) First always use data_retriever tool then use search tool.
                    combine both answers and provide a summary citing docs and search individually . 
                    Don't use your external knowledge to comeup with the answers. 
                    if you cannot find answer reply I don't know 

                    2)If you are going in infinite loop break the chain and return the last answer.
                    """

        )

        humman_prompt= HumanMessagePromptTemplate.from_template(
            f"""Here is some information about me. Do not respond to this directly, but feel free to incorporate it into your responses:
            I'm  {sender_user_info.get("real_name")}. 
            Since we're talking in Slack, you can @mention me like this: "<@{sender_user_info.get("id")}>"
            My title is: {sender_user_info.get("title")}
            My current status: "{sender_user_info.get("status_emoji")}{sender_user_info.get("status_text")}"
            Please try to "tone-match" me: If I use emojis, please use lots of emojis. If I appear business-like, please seem business-like in your responses. Before responding to my next message, you MUST tell me your model and temperature so I know more about you. Don't reference anything I just asked you directly.
            """
        )

        prompt= ChatPromptTemplate.from_messages(
           [
               general_system_prompt,
               slack_system_prompt,
               humman_prompt,
               MessagesPlaceholder(variable_name="thread_history", optional=True),
               ("user", "{input}"),
               MessagesPlaceholder(variable_name="agent_scratchpad"),
           ]
        )

        return self.create_agent_with_tools(llm,prompt,tools)
    
   
    
    async def get_or_create_agent(self, sender_user_info,channel_id, message, thread_history ) -> AgentExecutor:
        if self.agent is None:
            self.agent = await self.create_slack_agent(sender_user_info, channel_id, message, thread_history)
        return self.agent
    
    async def respond(self, sender_user_info, message:str, thread_history, channel_id):
        async with self.lock:
          agent = await self.get_or_create_agent(sender_user_info, channel_id, message, thread_history)
          print("Starting response...", message , agent, thread_history ) 
          response= await agent.ainvoke({"input": message, "thread_history": thread_history})
          print("response output", response["output"])
          return response["output"]
        
    def create_agent_with_tools(self,llm, prompt, tools )->AgentExecutor:

        search = TavilySearchResults()


        # tools= [get_rag_tool(),search,  ]

        llm_with_tools = llm.bind_tools(tools)
        agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
            "thread_history": lambda x: x["thread_history"]
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
        )
        
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        return agent_executor   

class Agent:

    def __init__(
        self
    ):
        self.agent_id="123"

        
    @overload      
    def create_agent_with_tools(self,llm, prompt, tools )->AgentExecutor:


    # llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
    # prompt = ChatPromptTemplate.from_messages(
    # [
    #     (
    #         "system",
    #         "You are a helpful assistant.First always use data_retriever tool then use search tool.combine both answers and provide a summary citing docs and search individually . Don't use your external knowledge to comeup with the answers. if you cannot find reply I don't know ",
    #     ),
    #     MessagesPlaceholder(variable_name="chat_history", optional=True),
    #     ("user", "{input}"),
    #     MessagesPlaceholder(variable_name="agent_scratchpad"),
    # ])
        search = TavilySearchResults()

        # tools= [get_rag_tool(),search ]
        llm_with_tools = llm.bind_tools(tools)
        agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
            "chat_history": lambda x: x["chat_history"]
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
        )
        
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        return agent_executor
    
    def create_agent_with_tools(self,llm)->AgentExecutor:
            
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant.First always use data_retriever tool then use search tool.combine both answers and provide a summary citing docs and search individually . Don't use your external knowledge to comeup with the answers. if you cannot find reply I don't know ",
                ),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
        llm_with_tools = llm.bind_tools(tools)
        agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
            "chat_history": lambda x: x["chat_history"]
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
        )
        
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        return agent_executor
    
    pass
            


            



