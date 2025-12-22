import os

from fastapi import APIRouter, Body
import langchain
import langchain_community
import langchain_community.chat_message_histories
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories.redis import RedisChatMessageHistory
from agents import Agent
from pydantic import BaseModel
from models.chat_models import Message, Conversation
import redis
import json


chat_router = APIRouter(prefix='/chat', tags=['chat'], responses={404: {"description": "Not found"}})

r = redis.Redis(host='localhost', port=6379, db=0)

chat_history=[]


@chat_router.post("/")
async def chat(message: Message, conversation_id:str):

    llm= ChatOpenAI(api_key= os.environ.get("OPEN_API_SECRET"), temperature=0, model= "gpt-4o-mini")
    
    message_history = RedisChatMessageHistory(url="redis://localhost:6379", ttl=600, session_id=conversation_id)
    chat_key=r.get(conversation_id)
    if message_history:
        chat_history= await message_history.aget_messages()
    else:
        chat_history=[]

    input=message.content    
    agent= Agent()
    agent_executor= agent.create_agent_with_tools(llm)
    print("chat_history", chat_history)
    response= agent_executor.invoke({"input": input, "chat_history": chat_history})

    # add_to_history(input,response["output"],conversation_id)
    message_history.add_user_message(input)
    message_history.add_ai_message(response["output"])

    return  response["output"]


def add_to_history(input: str,output:str,conversation_id ):

    chat_history.extend(
    [
        HumanMessage(content=input),
        AIMessage(content= output),
    ])

    r.set(conversation_id, chat_history)
