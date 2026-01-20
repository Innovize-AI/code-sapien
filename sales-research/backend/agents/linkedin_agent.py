import requests
import json
import os
import time
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional, List, Dict
from prompts.sales_prompts import LINKEDIN_ANALYZER_PROMPT, AI_LEAD_EVALUATOR_PROMPT, PROFILE_CLASSIFIER_PROMPT, BATCH_PROFILE_CLASSIFIER_PROMPT, COMPANY_CONTEXT
from models.openai_models import get_open_ai

load_dotenv()

load_dotenv()

class ProfileClassificationResult(BaseModel):
    id: str = Field(description="The LinkedIn URL or unique identifier of the profile")
    is_competitor: bool = Field(description="Is the person a competitor working for a rival company?")
    is_fit: bool = Field(description="Is the person a potential fit/customer based on ICP?")
    is_decision_maker: bool = Field(description="Is the person a decision maker (C-Level, VP, Director, etc)?")
    reasoning: str = Field(description="Brief explanation of the classification.")

class BatchProfileClassification(BaseModel):
    classifications: List[ProfileClassificationResult] = Field(description="List of profile classifications")

class ProfileClassification(BaseModel):
    is_competitor: bool = Field(description="Is the person a competitor working for a rival company?")
    is_fit: bool = Field(description="Is the person a potential fit/customer based on ICP?")
    is_decision_maker: bool = Field(description="Is the person a decision maker (C-Level, VP, Director, etc)?")
    reasoning: str = Field(description="Brief explanation of the classification.")

def batch_classify_profiles(profiles: List[Dict]):
    """
    Classifies a batch of profiles using LLM based on headline and company context.
    Expects profiles list of dicts: [{'id': 'url', 'headline': '...'}, ...]
    """
    if not profiles:
        return {}
        
    try:
        # Reverting to gpt-4o-mini as gpt-5-mini is not a valid model
        llm = get_open_ai(temperature=0, model="gpt-4.1-mini")
        structured_llm = llm.with_structured_output(BatchProfileClassification)
        
        # Format profiles for prompt
        profiles_text = json.dumps(profiles, indent=2)
        
        prompt = BATCH_PROFILE_CLASSIFIER_PROMPT.format(
            company_context=COMPANY_CONTEXT,
            profiles_data=profiles_text
        )
        
        response = structured_llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ])
        
        results_map = {}
        if response and response.classifications:
            for res in response.classifications:
                results_map[res.id] = res.dict()
                
        return results_map

    except Exception as e:
        print(f"Error in batch classification: {e}")
        return {}

def classify_profile(name: str, headline: str):
    """
    Classifies a profile using LLM based on headline and company context.
    Uses structured output for reliable JSON parsing.
    """
    if not headline or len(headline) < 3:
        return {"is_competitor": False, "is_fit": False, "is_decision_maker": False, "reasoning": "No headline provided."}
        
    try:
        llm = get_open_ai(temperature=0, model="gpt-4o-mini")
        structured_llm = llm.with_structured_output(ProfileClassification)
        
        prompt = PROFILE_CLASSIFIER_PROMPT.format(
            name=name, 
            headline=headline,
            company_context=COMPANY_CONTEXT
        )
        
        response = structured_llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ])
        
        if response:
            return response.dict()
        else:
             return {"is_competitor": False, "is_fit": False, "is_decision_maker": False, "reasoning": "Empty response from LLM"}

    except Exception as e:
        print(f"Error classifying profile {name}: {e}")
        return {"is_competitor": False, "is_fit": False, "is_decision_maker": False, "reasoning": "Error during classification."}

def get_username_from_url(linkedin_url: str):
    # Remove query parameters and trailing slashes
    url = linkedin_url.split("?")[0].strip("/")
    parts = url.split("/")
    
    # Common formats:
    # linkedin.com/in/username
    # linkedin.com/company/username
    # linkedin.com/company/username/posts
    if "company" in parts:
        idx = parts.index("company")
        if len(parts) > idx + 1:
            return parts[idx+1]
    if "in" in parts:
        idx = parts.index("in")
        if len(parts) > idx + 1:
            return parts[idx+1]
            
    return parts[-1]

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

def analyze_competitor_posts(competitor_urls: list[str]):
    """Fetches and analyzes posts from multiple competitor LinkedIn profiles."""
    all_competitor_data = []
    
    for url in competitor_urls:
        try:
            # We can reuse get_linkedin_data logic
            # but since get_linkedin_data expects state, let's refactor slightly or call it with a fake state
            dummy_state = {"linkedin_url": url}
            data = get_linkedin_data(dummy_state)
            all_competitor_data.append({
                "url": url,
                "data": json.loads(data["user_profile_details"])
            })
        except Exception as e:
            print(f"Error fetching data for {url}: {e}")
            all_competitor_data.append({
                "url": url,
                "error": str(e)
            })

    from prompts.sales_prompts import COMPETITOR_POST_ANALYZER_PROMPT
    
    messages = [
        SystemMessage(content=COMPETITOR_POST_ANALYZER_PROMPT),
        HumanMessage(content=json.dumps(all_competitor_data))
    ]
    
    model = get_open_ai(model="gpt-4o-mini", temperature=1)
    response = model.invoke(messages)
    return response.content

def get_post_commenters(post_id: str):
    """Fetches commenters for a specific LinkedIn post."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    comments_url = f"{linkedin_base_url}/post/comments"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }
    
    params = {"post_url": post_id, "page_number": 1}
    
    try:
        response = requests.get(comments_url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"DEBUG: comments API error {response.status_code}: {response.text[:200]}")
            raise Exception(f"LinkedIn Comments API error: {response.status_code} - {response.text[:100]}")
            
        data = response.json()
        payload = data.get("data")
        if isinstance(payload, dict):
            return payload.get("comments", [])
        elif isinstance(payload, list):
            return payload
        return []
    except Exception as e:
        print(f"Error fetching comments for post {post_id}: {e}")
        return []

def analyze_lead_with_ai(lead: dict, icp_data: dict):
    """Evaluates a single lead against the ICP using AI."""
    try:
        model = get_open_ai(model="gpt-4o-mini", temperature=0) # Use 0 temp for consistent scoring
        
        prompt = AI_LEAD_EVALUATOR_PROMPT.format(
            name=lead.get("name"),
            comment=lead.get("comment_text"),
            post_context=lead.get("source_post"),
            icp_json=json.dumps(icp_data)
        )
        
        messages = [
            SystemMessage(content="You are a Lead Qualification Expert. Return ONLY JSON."),
            HumanMessage(content=prompt)
        ]
        
        response = model.invoke(messages)
        # Handle code block formatting if LLM includes it
        content = response.content.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(content)
        
        lead["fit_score"] = analysis.get("fit_score", 0)
        lead["fit_reasoning"] = analysis.get("fit_reasoning", "N/A")
        lead["is_qualified"] = analysis.get("is_qualified", False)
        
        return lead
    except Exception as e:
        print(f"Error analyzing lead with AI: {e}")
        lead["fit_score"] = 0
        lead["fit_reasoning"] = "Analysis failed"
        lead["is_qualified"] = False
        return lead

def _process_single_post(post, user_name):
    """Helper to process a single post and return extracted leads."""
    leads_acc = []
    # Resilient post_id extraction
    post_id = post.get("post_id") or post.get("id")
    
    if not post_id:
        urn_val = post.get("urn")
        if isinstance(urn_val, dict):
            post_id = urn_val.get("activity_urn")
        elif isinstance(urn_val, str):
            post_id = urn_val.split(":")[-1]
    
    if not post_id:
        return []
    
    source_post_title = post.get("text", "")[:100] + "..."
    source_post_url = post.get("post_url") or post.get("url") or (f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}" if ":" not in str(post_id) else f"https://www.linkedin.com/feed/update/{post_id}")

    try:
        commenters = get_post_commenters(source_post_url)
    except Exception as e:
        print(f"Error fetching commenters for post {post_id}: {e}")
        return []

    for commenter in commenters:
        author = commenter.get("author")
        if not author: continue
        linkedin_url = author.get("profile_url")
        if not linkedin_url: continue
        
        # Normalize URL: remove query params, trailing slashes, strip whitespace
        linkedin_url = linkedin_url.split("?")[0].strip().strip("/")
        
        comment_text = commenter.get("text")
        headline = author.get("headline") or author.get("subtitle") or author.get("description") or ""

        # Collect raw lead info
        leads_acc.append({
            "name": author.get("name") or "Anonymous",
            "headline": headline,
            "linkedin_url": linkedin_url,
            "comment_text": comment_text,
            "source_post": source_post_title,
            "source_post_url": source_post_url or "",
            "competitor": user_name,
            # Initialize classification fields as unset/default
            "is_fit": False,
            "is_competitor": False,
            "is_decision_maker": False,
            "fit_reasoning": ""
        })
    return leads_acc

def discover_leads_from_competitor(competitor_url: str):
    """Fetches recent posts from a competitor and extracts commenters as potential leads."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    user_name = get_username_from_url(competitor_url)
    posts_url = f"{linkedin_base_url}/profile/posts"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }
    
    try:
        print(f"DEBUG: Starting discovery for competitor: {competitor_url}")
        # 1. Fetch recent posts
        response = requests.get(posts_url, headers=headers, params={"username": user_name}, timeout=15)
        if response.status_code != 200:
            print(f"DEBUG: posts API error {response.status_code} for {user_name}: {response.text[:200]}")
            raise Exception(f"LinkedIn Posts API error: {response.status_code} for {user_name}")
            
        posts_data = response.json()
        
        posts = []
        if isinstance(posts_data, list):
            posts = posts_data
        elif isinstance(posts_data, dict):
            if "data" in posts_data:
                d = posts_data["data"]
                if isinstance(d, list): posts = d
                elif isinstance(d, dict): posts = d.get("posts", [])
            elif "posts" in posts_data:
                posts = posts_data["posts"]
        
        if not posts:
            print(f"DEBUG: No posts found in response for {user_name}. Keys present: {list(posts_data.keys()) if isinstance(posts_data, dict) else 'is list'}")
            print(f"DEBUG: Response snippet: {str(posts_data)[:200]}")

        print(f"DEBUG: Found {len(posts)} total posts for {user_name}")

        # Filter posts from the last 30 days
        now_ms = int(time.time() * 1000)
        one_month_ms = 30 * 24 * 60 * 60 * 1000
        
        recent_posts = []
        for p in posts:
            posted_at = p.get("posted_at", {})
            timestamp = posted_at.get("timestamp")
            if timestamp:
                try:
                    ts = int(timestamp)
                    if (now_ms - ts) <= one_month_ms:
                        recent_posts.append(p)
                except:
                    pass
            else:
                pass
        
        print(f"DEBUG: {len(recent_posts)} posts within last 30 days out of {len(posts)}")
        posts = recent_posts if recent_posts else posts[:5] # Fallback to latest 5 if none

        # Sort posts by engagement
        def get_engagement(p):
            stats = p.get("stats", {})
            try:
                return int(stats.get("comments", 0)) + int(stats.get("total_reactions", 0)) + int(stats.get("reposts", 0))
            except:
                return 0

        posts.sort(key=get_engagement, reverse=True)
        top_posts = posts[:5]

        raw_leads_buffer = []

        # 2. Sequential Comment Fetching (Safety First)
        # Avoid nested threading inside discover_leads (which is already threaded)
        # Timeouts on requests ensure this won't hang for long
        for post in top_posts:
            try:
                leads = _process_single_post(post, user_name)
                if leads:
                    raw_leads_buffer.extend(leads)
            except Exception as exc:
                print(f"Post processing exception for {post.get('id', 'unknown')}: {exc}")
        
        print(f"DEBUG: Found {len(raw_leads_buffer)} interactions for {user_name}")
        return raw_leads_buffer
    except Exception as e:
        print(f"CRITICAL Error discovering leads from competitor {competitor_url}: {e}")
        import traceback
        traceback.print_exc()
        raise e


async def batch_classify_profiles_async(profiles: List[Dict]):
    """
    Async version: Classifies a batch of profiles using LLM based on headline and company context.
    Expects profiles list of dicts: [{'id': 'url', 'headline': '...'}, ...]
    """
    if not profiles:
        return {}
        
    try:
        llm = get_open_ai(temperature=0, model="gpt-4.1-mini")
        structured_llm = llm.with_structured_output(BatchProfileClassification)
        
        # Format profiles for prompt
        profiles_text = json.dumps(profiles, indent=2)
        
        prompt = BATCH_PROFILE_CLASSIFIER_PROMPT.format(
            company_context=COMPANY_CONTEXT,
            profiles_data=profiles_text
        )
        
        # Native async call
        response = await structured_llm.ainvoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ])
        
        results_map = {}
        if response and response.classifications:
            for item in response.classifications:
                results_map[item.id] = {
                    "is_fit": item.is_fit,
                    "is_competitor": item.is_competitor,
                    "is_decision_maker": item.is_decision_maker,
                    "reasoning": item.reasoning
                }
                
        return results_map

    except Exception as e:
        print(f"Error in async batch classification: {e}")
        return {}

async def get_posts_by_keyword(keywords: List[str]):
    """Get linkedin posts by keywords - Async version with parallel execution for multiple keywords"""
    import asyncio
    
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    if not linkedin_base_url:
        print("Error: LINKEDIN_RAPID_BASE_URL not set")
        return []
        
    search_url = f"{linkedin_base_url.rstrip('/')}/posts/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    async def fetch_for_single_keyword(keyword: str):
        try:
            print(f"DEBUG: Fetching posts for keyword: '{keyword}'")
            response = await asyncio.to_thread(
                requests.get,
                search_url,
                headers=headers,
                params={"keyword": keyword}
            )
            
            if response.status_code != 200:
                print(f"DEBUG: API error for keyword '{keyword}': {response.status_code}")
                return []

            posts_data = response.json()
            
            if "data" in posts_data:
                if isinstance(posts_data["data"], list):
                    return posts_data["data"]
                elif isinstance(posts_data["data"], dict):
                    if "posts" in posts_data["data"]:
                        return posts_data["data"]["posts"]
                    return [posts_data["data"]]
            return []
        except Exception as e:
            print(f"Error fetching for keyword '{keyword}': {e}")
            return []

    try:
        # Run all keyword searches in parallel
        tasks = [fetch_for_single_keyword(k) for k in keywords]
        results = await asyncio.gather(*tasks)
        
        # Flatten and Deduplicate based on URN/ID
        all_posts = []
        seen_ids = set()
        
        for i, batch in enumerate(results):
            keyword_for_batch = keywords[i]
            for post in batch:
                # Try to find a unique ID
                pid = post.get("id") or post.get("urn")
                if isinstance(pid, dict): pid = pid.get("activity_urn")
                
                # If no ID, generate a signature from text (fallback)
                if not pid:
                     pid = str(hash(post.get("text", "")[:50]))
                
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    # Tag post with keyword
                    post["matched_keyword"] = keyword_for_batch
                    all_posts.append(post)

        print(f"DEBUG: Found {len(all_posts)} unique posts across {len(keywords)} keywords")
        return all_posts

    except Exception as e:
        print(f"Error in get_posts_by_keyword: {e}")
        return []

async def discover_leads_from_keywords(keywords: List[str]):
    """
    High-level function to discover leads via keyword search.
    1. Fetches posts matching keywords.
    2. Extracts the AUTHOR of each post as a lead.
    """
    posts = await get_posts_by_keyword(keywords)
    print(f"DEBUG: Processing {len(posts)} posts for leads extraction...")
    
    leads = []
    seen_urls = set()
    
    for post in posts:
        try:
            author = post.get("author", {})
            if not author:
                continue
                
            linkedin_url = author.get("profile_url") or author.get("url")
            if not linkedin_url and author.get("username"):
                linkedin_url = f"https://www.linkedin.com/in/{author.get('username')}"
                
            if not linkedin_url:
                continue
            
            # Normalize
            linkedin_url = linkedin_url.split("?")[0].strip().strip("/")
            
            if linkedin_url in seen_urls:
                continue
                
            seen_urls.add(linkedin_url)
            
            headline = author.get("headline") or author.get("subtitle") or author.get("description") or ""
            post_text = post.get("text", "")
            
            # Post URL
            post_id = post.get("id") or post.get("urn")
            if isinstance(post_id, dict): post_id = post_id.get("activity_urn")
            elif isinstance(post_id, str) and ":" in post_id: post_id = post_id.split(":")[-1]
            
            source_post_url = post.get("post_url") or post.get("url")
            if not source_post_url and post_id:
                 source_post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}"

            # Get matched keyword
            matched_keyword = post.get("matched_keyword", "Keyword Search")
            competitor_source = f"Keyword: {matched_keyword}"

            leads.append({
                "name": author.get("name") or "Unknown",
                "headline": headline,
                "linkedin_url": linkedin_url,
                "comment_text": f"Posted about keywords: {post_text[:200]}...", # Storing post text as 'comment' context
                "source_post": post_text[:100] + "...",
                "source_post_url": source_post_url or "",
                "competitor": competitor_source, # Marker with keyword
                "is_fit": False,
                "is_competitor": False,
                "is_decision_maker": False,
                "fit_reasoning": ""
            })
            
        except Exception as e:
            print(f"Error extracting lead from post: {e}")
            continue
            
    print(f"DEBUG: Extracted {len(leads)} unique leads from keyword search posts.")
    return leads
