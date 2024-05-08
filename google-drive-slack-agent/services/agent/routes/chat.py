import os

from fastapi import APIRouter, Body
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from agents import create_agent_with_tools
from pydantic import BaseModel
from models.chat_models import Message, Conversation

router = APIRouter(prefix='/chat', tags=['chat'], responses={404: {"description": "Not found"}})

chat_history=[]

@router.post("/")
async def chat(message: Message):

    llm= ChatOpenAI(api_key= os.environ.get("OPEN_API_SECRET"), temperature=0)

    input=message.content    
    agent= create_agent_with_tools(llm)
 
    response= agent.invoke({"input": input, "chat_history": chat_history})

    add_to_history(input,response["output"])
    

    return  response["output"]


def add_to_history(input: str,output:str):

    chat_history.extend(
    [
        HumanMessage(content=input),
        AIMessage(content= output),
    ]
)