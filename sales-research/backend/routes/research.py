import operator
import logging

logger = logging.getLogger(__name__)
from typing import Annotated, Any

from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END


class State(TypedDict):
    # The operator.add reducer fn makes this append-only
    aggregate: Annotated[list, operator.add]


class ReturnNodeValue:
    def __init__(self, node_secret: str):
        self._value = node_secret

    def __call__(self, state: State) -> Any:
        logger.info(f"Adding {self._value} to {state['aggregate']}")
        return {"aggregate": [self._value]}

def user_linkedin_analyzer(username):

    # get linkedin summary
    #get user posts
    #analyze posts 
    return



def company_analysis(companyname):
    
    #scrape webcontent
    #extract all data
    #funding rounds
    #google news
    #Hiring
    return

def report_creator():
    #
    return

builder = StateGraph(State)
builder.add_node("a", ReturnNodeValue("I'm A"))
builder.add_edge(START, "a")
builder.add_node("b", ReturnNodeValue("I'm B"))
builder.add_node("c", ReturnNodeValue("I'm C"))
builder.add_node("d", ReturnNodeValue("I'm D"))
builder.add_edge("a", "b")
builder.add_edge("a", "c")
builder.add_edge("b", "d")
builder.add_edge("c", "d")
builder.add_edge("d", END)
graph = builder.compile()

graph.invoke({"aggregate": []}, {"configurable": {"thread_id": "foo"}})


from IPython.display import Image, display

display(Image(graph.get_graph().draw_mermaid_png()))