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

def get_linkedin_profile(state: AgentState):
    """Fetches basic profile details."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    linkedin_url = state.get("linkedin_url")
    if not linkedin_url:
        return {"user_profile_details": json.dumps({"description": "No LinkedIn URL"})}

    profile_url = linkedin_base_url + "/profile/detail"
    user_name = get_username_from_url(linkedin_url)
    querystring = {"username": user_name}

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    try:
        response = requests.get(profile_url, headers=headers, params=querystring)
        profile_details = response.json()
        
        if isinstance(profile_details, dict) and "message" in profile_details:
             if "exceeded the MONTHLY quota" in profile_details["message"]:
                print(f"LinkedIn API Rate Limit: {profile_details['message']}")
                return {"user_profile_details": json.dumps({"error": "Rate limit exceeded"})}

        base_data = profile_details.get("data", profile_details) if isinstance(profile_details, dict) else profile_details
        basic_info = base_data.get("basic_info", {})
        fullname = basic_info.get("fullname", "")
        profile_pic = basic_info.get("profile_picture_url", "")

        return {
            "user_profile_details": json.dumps(base_data),
            "fullname": fullname,
            "profile_picture_url": profile_pic
        }
    except Exception as e:
        print(f"Error fetching LinkedIn profile: {e}")
        return {"user_profile_details": json.dumps({"error": str(e)})}

def get_linkedin_posts(state: AgentState):
    """Fetches recent posts."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    linkedin_url = state.get("linkedin_url")
    if not linkedin_url:
        return {"user_profile_details": ""} # Append nothing

    user_name = get_username_from_url(linkedin_url)
    posts_url = linkedin_base_url + "/profile/posts"
    querystring = {"username": user_name}
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    try:
        response = requests.get(posts_url, headers=headers, params=querystring)
        posts_data = response.json()
        
        posts_list = []
        if "data" in posts_data:
            if isinstance(posts_data["data"], list):
                posts_list = posts_data["data"]
            elif isinstance(posts_data["data"], dict) and "posts" in posts_data["data"]:
                posts_list = posts_data["data"]["posts"]
        
        return {"user_profile_details": json.dumps({"recent_posts": posts_list[:5]})}
    except Exception as e:
        print(f"Error fetching LinkedIn posts: {e}")
        return {}

def get_linkedin_engagement(state: AgentState):
    """Fetches reactions and comments on User/Company posts to see if the Lead engaged."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    lead_linkedin_url = state.get("linkedin_url")
    user_linkedin_url = state.get("user_linkedin_url")
    company_linkedin_url = state.get("company_linkedin_url")
    
    if not lead_linkedin_url or (not user_linkedin_url and not company_linkedin_url):
        return {"post_engagements": []}

    lead_username = get_username_from_url(lead_linkedin_url)
    targets = []
    if user_linkedin_url: targets.append(("user", get_username_from_url(user_linkedin_url)))
    if company_linkedin_url: targets.append(("company", get_username_from_url(company_linkedin_url)))

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    found_engagements = []

    for target_type, username in targets:
        try:
            # Fetch latest 10 posts for the target (user or company)
            posts_url = f"{linkedin_base_url}/profile/posts"
            querystring = {"username": username}
            response = requests.get(posts_url, headers=headers, params=querystring)
            posts_data = response.json()
            
            posts = []
            if "data" in posts_data:
                if isinstance(posts_data["data"], list): posts = posts_data["data"]
                elif isinstance(posts_data["data"], dict): posts = posts_data["data"].get("posts", [])
            
            for post in posts[:10]:
                post_id = post.get("post_id") or post.get("id")
                if not post_id: continue

                # Check reactions for this post
                reactions_url = f"{linkedin_base_url}/post/reactions"
                # Note: Some APIs use 'post_id' or 'url'. We'll assume post_id is enough for this RapidAPI.
                r_params = {"post_id": post_id, "count": 100} 
                r_resp = requests.get(reactions_url, headers=headers, params=r_params)
                r_data = r_resp.json()
                
                reactors = r_data.get("data", [])
                for reactor in reactors:
                    if reactor.get("username") == lead_username:
                        found_engagements.append({
                            "type": "reaction",
                            "target": target_type,
                            "post_id": post_id,
                            "content": post.get("text", "")[:100] + "...",
                            "reaction_type": reactor.get("type", "like")
                        })
                
                # Check comments
                comments_url = f"{linkedin_base_url}/post/comments"
                c_params = {"post_id": post_id, "count": 50}
                c_resp = requests.get(comments_url, headers=headers, params=c_params)
                c_data = c_resp.json()
                
                comments = c_data.get("data", [])
                for comment in comments:
                    if comment.get("username") == lead_username:
                        found_engagements.append({
                            "type": "comment",
                            "target": target_type,
                            "post_id": post_id,
                            "content": post.get("text", "")[:100] + "...",
                            "comment_text": comment.get("text", "")
                        })

        except Exception as e:
            print(f"Error checking engagement for {username}: {e}")

    return {"post_engagements": found_engagements}


def get_linkedin_company_data(state: AgentState):
    """Gathers hiring status and recent company news."""
    # Simulation for now
    return {
        "company_news": [
            {"title": "Expanding AI Engineering team", "source": "LinkedIn News", "date": "2024-01-10"}
        ],
        "hiring_data": [
            {"role": "Full Stack Developer", "location": "Remote"},
            {"role": "Product Manager", "location": "London"}
        ]
    }

def linkedin_profile_analyzer(state: AgentState):
    """Synthesizes all LinkedIn data into a deep profile analysis."""
    # Combine all collected data for the analyzer
    content = {
        "profile": state.get("user_profile_details", ""),
        "engagements": state.get("post_engagements", []),
        "company_news": state.get("company_news", []),
        "hiring": state.get("hiring_data", [])
    }
    
    messages = [
        SystemMessage(content=LINKEDIN_ANALYZER_PROMPT + "\nConsider the company news, hiring status, and post engagements to provide a deeper strategic assessment."),
        HumanMessage(content=json.dumps(content))
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return {"user_profile_analysis": response.content}
