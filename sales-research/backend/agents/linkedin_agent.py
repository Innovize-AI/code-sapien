import requests
import json
import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from prompts.sales_prompts import LINKEDIN_ANALYZER_PROMPT
from models.openai_models import get_open_ai

load_dotenv()

def get_username_from_url(linkedin_url: str):
    return linkedin_url.strip("/").split("/")[-1]

def merge_json(json1, json2):
    for key, value in json2.items():
        if key in json1 and isinstance(json1[key], dict) and isinstance(value, dict):
            merge_json(json1[key], value)
        else:
            json1[key] = value
    return json1

def get_linkedin_data(state: AgentState):
    """Used to analyze a linkedin user profile and create summary of profile posts etc"""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    linkedin_url = state.get("linkedin_url")
    if not linkedin_url:
        return {
            "user_profile_details": json.dumps({"description": "No LinkedIn URL provided"}),
            "fullname": "",
            "profile_picture_url": ""
        }

    profile_url = linkedin_base_url + "/profile/detail"
    user_name = get_username_from_url(linkedin_url)
    querystring = {"username": user_name}

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    response = requests.get(profile_url, headers=headers, params=querystring)
    profile_details = response.json()

    # Check for RapidAPI quota limit error
    if isinstance(profile_details, dict) and "message" in profile_details:
        if "exceeded the MONTHLY quota" in profile_details["message"]:
            raise Exception(f"LinkedIn API Rate Limit: {profile_details['message']}")

    posts_url = linkedin_base_url + "/profile/posts"
    response = requests.get(posts_url, headers=headers, params=querystring)
    profile_posts_data = response.json()
    
    if isinstance(profile_posts_data, dict) and "message" in profile_posts_data:
        if "exceeded the MONTHLY quota" in profile_posts_data["message"]:
            raise Exception(f"LinkedIn API Rate Limit: {profile_posts_data['message']}")
    
    posts_list = []
    if "data" in profile_posts_data:
        if isinstance(profile_posts_data["data"], list):
            posts_list = profile_posts_data["data"]
        elif isinstance(profile_posts_data["data"], dict) and "posts" in profile_posts_data["data"]:
            posts_list = profile_posts_data["data"]["posts"]
    
    profile_posts = posts_list[:3]
    posts_dict = {"posts": profile_posts}
    
    base_data = profile_details.get("data", profile_details) if isinstance(profile_details, dict) else profile_details
    
    fullname = base_data["basic_info"].get("fullname")
    profile_pic = base_data["basic_info"].get("profile_picture_url")
    
    merged_json = merge_json(base_data.copy(), posts_dict)
    merged_json["fullname"] = fullname
    merged_json["profile_picture_url"] = profile_pic

    return {
        "user_profile_details": json.dumps(merged_json),
        "fullname": fullname,
        "profile_picture_url": profile_pic
    }

def linkedin_profile_analyzer(state: AgentState):
    messages = [
        SystemMessage(content=LINKEDIN_ANALYZER_PROMPT),
        HumanMessage(content=state['user_profile_details'])
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"user_profile_analysis": response.content}
