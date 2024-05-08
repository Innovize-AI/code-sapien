from tabnanny import verbose
from langchain_core.agents import AgentAction,AgentFinish,AgentStep
from langchain_core.runnables import Runnable

from langchain.agents import AgentExecutor, create_react_agent

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate,HumanMessagePromptTemplate
from langchain_core.messages import AIMessage,SystemMessage,HumanMessage
from regex import A
from tools.retreival.retreiver import get_rag_tool
from langchain_community.tools.tavily_search import TavilySearchResults

from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser

from models.chat_models import Message

global agentExecutor


def create_agent_with_tools(llm)->AgentExecutor:

    
    # llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
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
    search = TavilySearchResults()

    tools= [get_rag_tool(),search ]
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


def get_agent():

    agent= agentExecutor

    return agentExecutor

    
