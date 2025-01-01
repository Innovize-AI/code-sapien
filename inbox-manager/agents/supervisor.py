from typing import TypeVar, Literal, TypedDict, Union, Optional
from langchain_core.language_models.chat_models import BaseChatModel

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langchain_core.messages import HumanMessage, trim_messages
from agents.llm_node import LLMNode
from workflow.state import AgentGraphState

class Supervisor(LLMNode):

    def __init__(self,members, state:Optional[str] = None,model=None, server=None, temperature=0, model_endpoint=None, stop=None, guided_json=None,):

        super().__init__(model=model, server=server)     
        self.members= members

    def make_supervisor_node(self) -> str:
        options = ["FINISH"] + self.members
        system_prompt = (
            "You are a supervisor tasked with managing a conversation between the"
            f" following workers: {self.members}. Given the following user request,"
            " respond with the worker to act next. Each worker will perform a"
            " task and respond with their results and status. When finished,"
            " respond with FINISH."
        )

        class Router(TypedDict):
            """Worker to route to next. If no workers are needed, route to FINISH."""
            next: Literal["FINISH", *self.members]

        def supervisor_node(state: AgentGraphState) -> Command[Literal[*self.members, "__end__"]]:
            """An LLM-based router."""
            messages = [
                {"role": "system", "content": system_prompt},
            ] + state["messages"]
            print("messages from supervisor node", messages)
            print("models llm", self.get_llm(json_model=False))
            response = self.get_llm().with_structured_output(Router).invoke(messages)
            goto = response["next"]
            print("go to from supervisor node", goto)
            if goto == "FINISH":
                goto = END  # Replace with your appropriate END value

            return Command(goto=goto)

        return supervisor_node
