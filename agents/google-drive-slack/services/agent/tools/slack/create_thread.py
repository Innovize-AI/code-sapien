

from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import StructuredTool

from slackbot import slack_bot


class SlackThread(BaseModel):
    channel_id: str = Field(description="slack channel id")
    message: str= Field(description="message(question) to send")
    user_id: str=Field(description="user id who asked question")
   


async def create_new_thread(channel_id: str,user_id:str ,message:str, ) -> str:
    """use when a new slack thread should be created."""
    print("calling create new thread", message)
    mes= "@"
    
    res=  await slack_bot.reply_to_slack(channel_id,  message, user_id)
    thread_ts=res["ts"]
    await slack_bot.add_ai_to_thread(channel_id,thread_ts)
#    Retrieve the timestamp of the posted message
    print("res", res)
    print("calling create new thread" , channel_id, message)
    return await slack_bot.respond_to_message(channel_id,thread_ts,thread_ts,user_id,message)

create_new_thread_tool = StructuredTool(
        
        name = "create_slack_thread",
        args_schema= SlackThread,
        func=create_new_thread,
        description="""use when a new slack thread should be created with arguments like "{{"channel_id": str, "user_id":str, "message": str}}"
        """,
        coroutine=create_new_thread
    )