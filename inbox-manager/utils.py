from langchain_openai import OpenAIEmbeddings
from openai import embeddings
from qdrant_client import QdrantClient
from langchain_community.vectorstores.qdrant import Qdrant
from langchain_core.vectorstores import VectorStoreRetriever
import os

from typing import Annotated

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langchain_openai import ChatOpenAI
from langgraph.types import Command

def get_qdrant_as_retriver(collection_name)-> VectorStoreRetriever:

    embeddings= OpenAIEmbeddings(model="text-embedding-3-small", api_key= os.environ.get("OPENAI_API_KEY"))

    client= QdrantClient()

    qd = Qdrant(client, collection_name, embeddings)

    retriever= qd.as_retriever()

    return retriever



def make_handoff_tool(*, agent_name: str):
    """Create a tool that can return handoff via a Command"""
    tool_name = f"transfer_to_{agent_name}"

    @tool(tool_name)
    def handoff_to_agent(
        # # optionally pass current graph state to the tool (will be ignored by the LLM)
        state: Annotated[dict, InjectedState],
        # optionally pass the current tool call ID (will be ignored by the LLM)
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        """Ask another agent for help."""
        tool_message = {
            "role": "tool",
            "content": f"Successfully transferred to {agent_name}",
            "name": tool_name,
            "tool_call_id": tool_call_id,
        }
        return Command(
            # navigate to another agent node in the PARENT graph
            goto=agent_name,
            graph=Command.PARENT,
            # This is the state update that the agent `agent_name` will see when it is invoked.
            # We're passing agent's FULL internal message history AND adding a tool message to make sure
            # the resulting chat history is valid. See the paragraph above for more information.
            update={"messages": state["messages"] + [tool_message]},
        )

    return handoff_to_agent


def get_calendar_events():

    
    return