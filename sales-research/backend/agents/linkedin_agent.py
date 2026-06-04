import asyncio
import logging
import requests
import json
import os
import time
import re
import datetime
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from workflow.state import AgentState
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from prompts.sales_prompts import LINKEDIN_ANALYZER_PROMPT, AI_LEAD_EVALUATOR_PROMPT, PROFILE_CLASSIFIER_PROMPT, BATCH_PROFILE_CLASSIFIER_PROMPT, DEFAULT_COMPANY_CONTEXT
from models.gemini_models import get_gemini_model
from models.structured_output import LinkedInAnalysis
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def _extract_classifications(response) -> list:
    """Robustly pull the classifications list out of whatever the LLM returns.

    Gemini's structured output can come back as a Pydantic model, a clean dict,
    a dict with whitespace/quote-polluted keys (e.g. '\n"classifications'),
    or a raw JSON string — handle all four cases.
    """
    if not response:
        return []

    logger.info(f"classifications: {response.classifications}")
    # Pydantic model
    if hasattr(response, "classifications"):
        return response.classifications or []

    # Dict — may have malformed keys like '\n"classifications'
    if isinstance(response, dict):
        if "classifications" in response:
            return response["classifications"] or []
        for key, value in response.items():
            if key.strip().strip('"') == "classifications":
                return value or []
        return []

    # Raw string — strip markdown fences and parse
    if isinstance(response, str):
        try:
            text = re.sub(r"```(?:json)?\s*", "", response).strip().rstrip("`").strip()
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed.get("classifications", [])
        except Exception:
            pass

    return []

load_dotenv()

class ProfileClassificationResult(BaseModel):
    id: str = Field(description="The LinkedIn URL or unique identifier of the profile")
    is_competitor: bool = Field(description="Is the person a competitor working for a rival company?")
    is_fit: bool = Field(description="Is the person a potential fit/customer based on ICP?")
    is_decision_maker: bool = Field(description="Is the person a decision maker (C-Level, VP, Director, etc)?")
    is_buy_signal: bool = Field(default=False, description="Does the profile exhibit a genuine buy signal/pain point?")
    is_strategic_seller: bool = Field(default=False, description="Is the profile a strategic seller/consultant self-promoting?")
    reasoning: str = Field(description="Brief explanation of the classification.")
    intent: Optional[str] = Field(None, description="The person's localized intent (hand_raiser, prospect_pain, passive_expert, strategic_seller, low_signal)")
    post_topic_depth: Optional[str] = Field(None, description="Detailed nature of the post: sharing_framework, tool_showcase, complaining_keywords, industry_synthesis, etc.")
    sentiment: Optional[str] = Field(None, description="The sentiment of their interaction (positive, neutral, negative)")

class BatchProfileClassification(BaseModel):
    classifications: List[ProfileClassificationResult] = Field(description="List of profile classifications")

class ProfileClassification(BaseModel):
    is_competitor: bool = Field(description="Is the person a competitor working for a rival company?")
    is_fit: bool = Field(description="Is the person a potential fit/customer based on ICP?")
    is_decision_maker: bool = Field(description="Is the person a decision maker (C-Level, VP, Director, etc)?")
    is_buy_signal: bool = Field(default=False, description="Does the profile exhibit a genuine buy signal/pain point?")
    is_strategic_seller: bool = Field(default=False, description="Is the profile a strategic seller/consultant self-promoting?")
    reasoning: str = Field(description="Brief explanation of the classification.")

# Using LinkedInAnalysis from models.structured_output

def batch_classify_profiles(profiles: List[Dict], company_context: str | None = None):
    """
    Classifies a batch of profiles using LLM based on headline and company context.
    Expects profiles list of dicts: [{'id': 'url', 'headline': '...'}, ...]
    """
    if not profiles:
        return {}
        
    try:
        llm = get_gemini_model(temperature=0, model="gemini-3-flash-preview")
        structured_llm = llm.with_structured_output(BatchProfileClassification)
        
        # Format profiles for prompt
        profiles_text = json.dumps(profiles, indent=2)
        
        prompt = BATCH_PROFILE_CLASSIFIER_PROMPT.format(
            company_context=company_context or DEFAULT_COMPANY_CONTEXT,
            profiles_data=profiles_text
        )
        
        response = structured_llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ])
        
        results_map = {}

        for res in _extract_classifications(response):
            # Handle res as either a Pydantic model or a dict
            if hasattr(res, "id"):
                r_id = res.id
                r_data = {
                    "is_fit": getattr(res, "is_fit", False),
                    "is_competitor": getattr(res, "is_competitor", False),
                    "is_decision_maker": getattr(res, "is_decision_maker", False),
                    "is_buy_signal": getattr(res, "is_buy_signal", False),
                    "is_strategic_seller": getattr(res, "is_strategic_seller", False),
                    "reasoning": getattr(res, "reasoning", ""),
                    "intent": getattr(res, "intent", None),
                    "post_topic_depth": getattr(res, "post_topic_depth", None),
                    "sentiment": getattr(res, "sentiment", None)
                }
            else:
                r_id = res.get("id")
                r_data = {
                    "is_fit": res.get("is_fit", False),
                    "is_competitor": res.get("is_competitor", False),
                    "is_decision_maker": res.get("is_decision_maker", False),
                    "is_buy_signal": res.get("is_buy_signal", False),
                    "is_strategic_seller": res.get("is_strategic_seller", False),
                    "reasoning": res.get("reasoning", ""),
                    "intent": res.get("intent"),
                    "post_topic_depth": res.get("post_topic_depth"),
                    "sentiment": res.get("sentiment")
                }
            
            if r_id:
                results_map[r_id] = r_data
                
        return results_map

    except Exception as e:
        logger.error(f"Error in batch classification: {type(e).__name__}: {e}")
        return {}

def classify_profile(name: str, headline: str, company_context: str | None = None):
    """
    Classifies a profile using LLM based on headline and company context.
    Uses structured output for reliable JSON parsing.
    """
    if not headline or len(headline) < 3:
        return {"is_competitor": False, "is_fit": False, "is_decision_maker": False, "reasoning": "No headline provided."}
        
    try:
        llm = get_gemini_model(temperature=0, model="gemini-3-flash-preview")
        structured_llm = llm.with_structured_output(ProfileClassification)
        
        prompt = PROFILE_CLASSIFIER_PROMPT.format(
            name=name, 
            headline=headline,
            company_context=company_context or DEFAULT_COMPANY_CONTEXT
        )
        
        response = structured_llm.invoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ])
        
        if response:
            return response.model_dump()
        else:
             return {"is_competitor": False, "is_fit": False, "is_decision_maker": False, "reasoning": "Empty response from LLM"}

    except Exception as e:
        logger.error(f"Error classifying profile {name}: {e}")
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
    # Check if we already have the profile data in state to avoid duplicate calls
    # Check if we already have the profile data in state to avoid duplicate calls
    user_details = state.get("user_profile_details")
    
    # Handle if it's already a dict (new state) or string (old state/transition)
    if isinstance(user_details, str):
        try:
             user_details = json.loads(user_details)
        except:
             user_details = {}

    if isinstance(user_details, dict) and "id" in user_details:
        # Even if lead_company_linkedin_url is missing as a separate state field, 
        # we can extract it from the cached detail if available.
        if not state.get("lead_company_linkedin_url"):
            try:
                base_data = user_details
                experience = base_data.get("experience", [])
                if experience and len(experience) > 0:
                    current_job = experience[0]
                    if isinstance(current_job, dict):
                        lead_company_url = current_job.get("company_linkedin_url") or current_job.get("url")
                        return {"lead_company_linkedin_url": lead_company_url}
            except Exception:
                pass

        logger.debug("LinkedIn profile already fetched, skipping duplicate call.")
        return state

    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    linkedin_url = state.get("linkedin_url")
    if not linkedin_url:
        return {"user_profile_details": {"description": "No LinkedIn URL"}}

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
                logger.warning(f"LinkedIn API Rate Limit: {profile_details['message']}")
                return {"user_profile_details": {"error": "Rate limit exceeded"}}

        base_data = profile_details.get("data", profile_details) if isinstance(profile_details, dict) else profile_details
        basic_info = base_data.get("basic_info", {})
        fullname = basic_info.get("fullname", "")
        profile_pic = basic_info.get("profile_picture_url", "")
        urn = basic_info.get("urn", "")

        # Extract lead's current company URL if possible
        lead_company_linkedin_url = None
        experience = base_data.get("experience", [])
        if experience and len(experience) > 0:
            current_job = experience[0]
            if isinstance(current_job, dict):
                lead_company_linkedin_url = current_job.get("company_linkedin_url") or current_job.get("url")

        return {
            "user_profile_details": base_data,
            "fullname": fullname,
            "profile_picture_url": profile_pic,
            "lead_company_linkedin_url": lead_company_linkedin_url,
            "lead_li_urn": urn
        }

    except Exception as e:
        logger.error(f"Error fetching LinkedIn profile: {e}")
        return {"user_profile_details": {"error": str(e)}}

def get_linkedin_posts(state: AgentState):
    """Fetches recent posts."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    linkedin_url = state.get("linkedin_url")
    if not linkedin_url:
        return {"user_profile_details": {}} # Append nothing

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
        
        return {"user_profile_details": {"recent_posts": posts_list[:5]}}
    except Exception as e:
        logger.error(f"Error fetching LinkedIn posts: {e}")
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

    lead_urn = state.get("lead_li_urn")
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
            querystring = {"username": username, "page_number": 1}
            response = requests.get(posts_url, headers=headers, params=querystring)
            posts_data = response.json()
            
            posts = []
            if "data" in posts_data:
                if isinstance(posts_data["data"], list): posts = posts_data["data"]
                elif isinstance(posts_data["data"], dict): posts = posts_data["data"].get("posts", [])
            
            for post in posts[:10]:
                post_urn = post.get("urn").get("activity_urn", "")
                post_text= post.get("text", "")
                post_date = post.get("posted_at", {})
                if not post_urn: continue

                # Check reactions for this post
                if lead_urn:
                    reactions_url = f"{linkedin_base_url}/post/reactions"
                    r_params = {"post_url": post_urn, "page_number": 1} 
                    r_resp = requests.get(reactions_url, headers=headers, params=r_params)
                    r_data = r_resp.json()
                    
                    data = r_data.get("data", {})
                    for reaction in data.get("reactions", []):
                        reactor = reaction.get("reactor", {})
                        if reactor.get("urn") == lead_urn:
                            reaction_type = reaction.get("reaction_type", "LIKE")
                            logger.debug(f"Found engagement for {target_type}: {reaction_type}")
                            found_engagements.append({
                                "type": "reaction",
                                "target": target_type,
                                "post_id": post_urn,
                                "content": post_text[:100] + "...",
                                "post_url":posts_url,
                                "reaction_type": reaction_type,
                                "reactor_urn": reactor.get("urn", "")
                            })
                
                # Check comments
                comments_url = f"{linkedin_base_url}/post/comments"
                c_params = {"post_url": post_urn, "page_number": 1}
                c_resp = requests.get(comments_url, headers=headers, params=c_params)
                c_data = c_resp.json()
                
                data = c_data.get("data", {})
                for comment in data.get("comments", []):
                    author = comment.get("author", {})
                    if author.get("profile_url") == lead_linkedin_url:
                        found_engagements.append({
                            "type": "comment",
                            "target": target_type,
                            "post_id": post_urn,
                            "content": post.get("text", "")[:100] + "...",
                            "comment_text": comment.get("text", "")
                        })

        except Exception as e:
            logger.error(f"Error checking engagement for {username}: {e}")

    return {"post_engagements": found_engagements}


def get_company_details(company_identifier: str):
    """Fetches company details using the company identifier (username or URL)."""
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    if not company_identifier:
        return None
    
    # RapidAPI Endpoint for company details
    company_url = f"{linkedin_base_url.rstrip('/')}/companies/detail"
    querystring = {"identifier": company_identifier}

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    try:
        response = requests.get(company_url, headers=headers, params=querystring)
        data = response.json()
        return data.get("data", data)
    except Exception as e:
        logger.error(f"Error fetching company details: {e}")
        return None

async def get_linkedin_company_data(state: AgentState):
    """LangGraph node wrapper for waterfall enrichment."""
    lead_url = state.get("linkedin_url") or state.get("user_linkedin_url")
    company_url = state.get("lead_company_linkedin_url")
    
    million_verifier_enabled = state.get("million_verifier_enabled", False)

    # Use the centralized waterfall helper
    enriched_data = await enrich_company_waterfall(
        person_url=lead_url, 
        company_url=company_url,
        existing_stats=state.get("company_stats"),
        million_verifier_enabled=million_verifier_enabled
    )
    
    if not enriched_data:
        return {}

    return {
        "company_name": enriched_data.get("name"),
        "company_description": enriched_data.get("description"),
        "company_industries": enriched_data.get("industries", []),
        "company_stats": enriched_data.get("company_stats", {}),
        "company_news": enriched_data.get("news", []),
        "hiring_data": enriched_data.get("hiring", []),
        "company_website": enriched_data.get("website"),

        # Lead email surfaced to top-level for quick access
        "email_id": enriched_data.get("person_email"),
        "email_verification_status": enriched_data.get("email_verification_status"),
        "company_linkedin_url": enriched_data.get("company_linkedin_url"),

    }


async def enrich_company_waterfall(
    person_url: str = None, 
    person_id: str = None,
    company_url: str = None, 
    existing_stats: dict = None,
    million_verifier_enabled: bool = False
):
    """
    Centralized enrichment coordinator:
    1. Apollo Match (via person_url or person_id)
    2. LinkedIn Details (via company_url) - Only if Apollo falls short
    """
    apollo_data = {}
    linkedin_data = {}
    news = []
    hiring = []

    # 1. Primary: Apollo match by person profile
    if person_url and person_url.startswith("apollo_id:"):
        person_id = person_url.split(":")[-1]
        person_url = None

    if person_url or person_id:
        logger.debug(f"CENTRAL WATERFALL: Trialing Apollo for {person_url or person_id}")
        apollo_data = await get_apollo_company_data(
            linkedin_url=person_url,
            apollo_id=person_id,
            million_verifier_enabled=million_verifier_enabled
        )
    logger.debug(f"Apollo data: {apollo_data}")
    # 2. Check if we need LinkedIn fallback
    # Skip if Apollo was successful AND provided core stats
    core_found = apollo_data.get("employee_count")
    
    # Proactively resolve company_url if not passed but present in Apollo data
    if not company_url and apollo_data.get("company_linkedin_url"):
        company_url = apollo_data.get("company_linkedin_url")
        
    if company_url:
        company_identifier = company_url.rstrip('/').split('/')[-1]
        logger.debug(f"CENTRAL WATERFALL: Fetching LinkedIn details for {company_identifier}")
        company_res = get_company_details(company_identifier)
        if company_res:
            # We always want updates and jobs
            news = company_res.get("updates", [])
            hiring = company_res.get("jobs", [])
            
            # If Apollo fell short, we also capture core stats
            if not core_found:
                linkedin_data = company_res.get("stats", {})
                if "basic_info" in company_res:
                     linkedin_data["basic_info"] = company_res["basic_info"]
                     
            # Extract company_id to fetch active jobs from jobs/search endpoint
            comp_id = None
            if "basic_info" in company_res and isinstance(company_res["basic_info"], dict):
                comp_id = company_res["basic_info"].get("id") or company_res["basic_info"].get("company_id")
            if not comp_id:
                comp_id = company_res.get("id") or company_res.get("company_id")
                
            if comp_id:
                logger.info(f"CENTRAL WATERFALL: Resolved company_id {comp_id}, querying active jobs.")
                searched_jobs = get_linkedin_jobs(company_id=str(comp_id))
                if searched_jobs:
                    hiring = searched_jobs
            else:
                logger.warning(f"CENTRAL WATERFALL: Could not resolve company_id for {company_identifier} to fetch jobs.")

    is_person_lookup = bool(person_url or person_id)
    
    # 3. Merge Strategy
    stats = {**linkedin_data}
    if apollo_data:
        stats.update({
            "employee_count": apollo_data.get("employee_count") or stats.get("employee_count"),
            "revenue": apollo_data.get("revenue_estimate") or stats.get("revenue"),
            "market_cap": apollo_data.get("market_cap") or stats.get("market_cap"),
            "total_funding": apollo_data.get("total_funding") or stats.get("total_funding"),
            "apollo_id": apollo_data.get("apollo_id"),
            "website": apollo_data.get("website") or stats.get("website"),
            "headcount_growth": apollo_data.get("headcount_growth"),
        })
        if is_person_lookup:
            stats.update({
                "person_name": apollo_data.get("person_name"),
                "first_name": apollo_data.get("first_name"),
                "last_name": apollo_data.get("last_name"),
                "headline": apollo_data.get("headline"),
                "linkedin_url": apollo_data.get("linkedin_url"),
                "person_email": apollo_data.get("person_email"),
                "city": apollo_data.get("city"),
                "state": apollo_data.get("state"),
                "photo_url": apollo_data.get("photo_url"),
            })

    # Backup from existing injections
    if existing_stats:
        for k, v in existing_stats.items():
            if k not in stats or not stats[k]:
                stats[k] = v

    # Final payload
    basic = linkedin_data.get("basic_info", {})
    # Prepare nested stats for backward compatibility
    company_stats = {
        "employee_count": apollo_data.get("employee_count"),
        "revenue": apollo_data.get("revenue_estimate"),
        "market_cap": apollo_data.get("market_cap"),
        "total_funding": apollo_data.get("total_funding"),
        "follower_count": apollo_data.get("follower_count"),
        "employee_count_range": apollo_data.get("employee_count_range"),
        "technologies": apollo_data.get("technologies"),
        "technology_names": apollo_data.get("technology_names"),
        # Funding details
        "funding_events": apollo_data.get("funding_events"),
        "latest_funding_stage": apollo_data.get("latest_funding_stage"),
        "latest_funding_date": apollo_data.get("latest_funding_date"),
        # Headcount growth (hiring signal)
        "headcount_growth": apollo_data.get("headcount_growth"),
        "apollo_id": str(apollo_data.get("apollo_id")) if apollo_data.get("apollo_id") else None,
        "headquarters": apollo_data.get("headquarters"),
        "domain": apollo_data.get("domain") or (stats.get("website").replace("http://", "").replace("https://", "").split("/")[0] if stats.get("website") else None),
    }

    result = {
        "name": stats.get("name") or apollo_data.get("company_name") or basic.get("name") or "Unknown Company",
        "company_name": apollo_data.get("company_name") or stats.get("name") or basic.get("name"),
        "description": apollo_data.get("description") or basic.get("description") or apollo_data.get("company_name"),
        "industries": apollo_data.get("industries") or basic.get("industries", []) or ([apollo_data.get("industry")] if apollo_data.get("industry") else []),
        "news": news[:5],
        "hiring": hiring[:5],
        "website": stats.get("website"),
        "person_email": apollo_data.get("person_email"),
        "email_verification_status": apollo_data.get("email_verification_status"),
        "linkedin_url": apollo_data.get("linkedin_url") if is_person_lookup else apollo_data.get("company_linkedin_url") or stats.get("linkedin_url"),
        "company_linkedin_url": apollo_data.get("company_linkedin_url") or stats.get("linkedin_url"),
        "domain": apollo_data.get("domain") or (stats.get("website").replace("http://", "").replace("https://", "").split("/")[0] if stats.get("website") else None),
        "company_stats": company_stats,
        **company_stats
    }

    if is_person_lookup:
        result.update({
            "person_name": apollo_data.get("person_name"),
            "headline": apollo_data.get("headline"),
            "first_name": apollo_data.get("first_name"),
            "last_name": apollo_data.get("last_name"),
            "photo_url": apollo_data.get("photo_url"),
            "city": apollo_data.get("city"),
            "state": apollo_data.get("state"),
            "country": apollo_data.get("country"),
        })

    return result


def is_recent_post(post: dict) -> bool:
    """
    Checks if a LinkedIn post is recent (within ~30 days).
    Prioritizes structured date/timestamp for precision, fallbacks to relative strings.
    """
    posted_at_data = post.get("posted_at")
    if not posted_at_data:
        return False
    
    # 1. Try Precise Date String (e.g. "2025-07-30 22:02:04")
    if isinstance(posted_at_data, dict) and posted_at_data.get("date"):
        try:
            # Parse the date string
            post_date = datetime.datetime.strptime(posted_at_data["date"], "%Y-%m-%d %H:%M:%S")
            now = datetime.datetime.now()
            # Check if within 30 days
            if (now - post_date).days <= 30:
                return True
            return False
        except Exception as e:
            logger.debug(f"Failed to parse post date string: {e}")

    # 2. Try Timestamp (milliseconds)
    if isinstance(posted_at_data, dict) and posted_at_data.get("timestamp"):
        try:
            ts = posted_at_data["timestamp"] / 1000.0
            post_date = datetime.datetime.fromtimestamp(ts)
            now = datetime.datetime.now()
            if (now - post_date).days <= 30:
                return True
            return False
        except Exception as e:
            logger.debug(f"Failed to parse post timestamp: {e}")

    # 3. Fallback to Relative String (e.g. "2 weeks ago" or dict.relative)
    relative_str = ""
    if isinstance(posted_at_data, dict):
        relative_str = posted_at_data.get("relative") or posted_at_data.get("text") or ""
    elif isinstance(posted_at_data, str):
        relative_str = posted_at_data
        
    if not relative_str:
        return False
        
    relative_str = relative_str.lower()
    
    # Simple logic for relative strings
    if "second" in relative_str or "minute" in relative_str or "hour" in relative_str or "day" in relative_str or "week" in relative_str:
        return True
        
    if "month" in relative_str:
        # "1 month ago" is fine, "2 months ago" is not
        match = re.search(r'\d+', relative_str)
        if match:
            num = int(match.group())
            return num <= 1
        return "months" not in relative_str # "month ago" is fine, "months ago" usually > 1
        
    return False

def linkedin_profile_analyzer(state: AgentState):
    """Analyzes a profile using LLM based on headline and company context."""
    user_profile_raw = state.get("user_profile_details", {})
    # Ensure we work with a copy to avoid side effects
    user_profile = user_profile_raw.copy() if isinstance(user_profile_raw, dict) else {}
    
    raw_posts = user_profile.get("recent_posts", []) if isinstance(user_profile, dict) else []
    
    # Filter for recency (last 30 days)
    recent_posts = [p for p in raw_posts if is_recent_post(p)]
    
    # CRITICAL: Strip raw/stale posts from the profile object so Gemini doesn't "find" them
    if "recent_posts" in user_profile:
        del user_profile["recent_posts"]
    
    if raw_posts and not recent_posts:
        logger.info(f"Filtered out {len(raw_posts)} stale posts (> 1 month old).")

    content = {
        "profile": user_profile,
        "recent_posts": recent_posts,
        "engagements": state.get("post_engagements", []),
        "company_name": state.get("company_name", {}),
        "lead_segment": state.get("lead_segment", "POTENTIAL_CLIENT"),
        "company_description": state.get("company_description", {}),
        "company_industries": state.get("company_industries", []),
        "company_stats": state.get("company_stats", {}),
        "company_news": state.get("company_news", []),
        "hiring": state.get("hiring_data", [])
    }
    
    messages = [
        SystemMessage(content=LINKEDIN_ANALYZER_PROMPT),
        HumanMessage(content=json.dumps(content, default=str))
    ]
    
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0)
        structured_llm = model.with_structured_output(LinkedInAnalysis)
        response = structured_llm.invoke(messages)
        
        # Format the output back into a Markdown string for the report to consume easily
        # or return the dict if the downstream nodes expect that. 
        # Checking graph: downstream is 'lead_data_extractor' and 'report_generator' which expect strings or generic dicts.
        # Ideally, we format this back to a detailed markdown string so other agents can read it naturally.
        
        if not response:
             return {"user_profile_analysis": {}}

        # Return the structured analysis as a dictionary
        return {"user_profile_analysis": response.model_dump()}

    except Exception as e:
        logger.error(f"Error in linkedin_profile_analyzer: {e}")
        return {"user_profile_analysis": "Error generating structured analysis."}

async def _map_apollo_response_to_enrichment(res: dict, million_verifier_enabled: bool = False) -> dict:
    """
    Internal helper to map Apollo API response (person + org) to standard enrichment dict.
    Ensures person data is captured even if organization data is missing.
    """
    person = res.get("person", {})
    if not person:
        return {}
        
    org = person.get("organization", {}) or {}
    
    # --- Revenue ---
    raw_rev = org.get("annual_revenue") or org.get("organization_revenue")
    rev_str = org.get("annual_revenue_printed") or org.get("organization_revenue_printed")
    if not rev_str and raw_rev:
        if raw_rev >= 1_000_000_000:
            rev_str = f"{raw_rev / 1_000_000_000:.1f}B"
        elif raw_rev >= 1_000_000:
            rev_str = f"{raw_rev / 1_000_000:.1f}M"
        else:
            rev_str = str(raw_rev)

    # --- Technologies ---
    technologies = [
        {"uid": t.get("uid"), "name": t.get("name"), "category": t.get("category")}
        for t in (org.get("current_technologies") or [])
    ]
    technology_names = org.get("technology_names") or [t["name"] for t in technologies]

    # --- Funding Events ---
    funding_events = [
        {
            "date": e.get("date"),
            "type": e.get("type"),
            "amount": e.get("amount"),
            "currency": e.get("currency"),
            "investors": e.get("investors"),
            "news_url": e.get("news_url")
        }
        for e in (org.get("funding_events") or [])
    ]

    # --- Headcount Growth ---
    headcount_growth = {
        "6_month": org.get("organization_headcount_six_month_growth"),
        "12_month": org.get("organization_headcount_twelve_month_growth"),
        "24_month": org.get("organization_headcount_twenty_four_month_growth"),
    }

    # Prepare company_stats (only if org exists, otherwise empty but present)
    company_stats = {}
    if org:
        company_stats = {
            "revenue_estimate": rev_str,
            "employee_count": org.get("estimated_num_employees") or org.get("num_employees"),
            "market_cap": org.get("market_cap"),
            "total_funding": org.get("total_funding_printed"),
            "total_funding_raw": org.get("total_funding"),
            "industry": org.get("primary_industry") or org.get("industry"),
            "industries": org.get("industries") or [],
            "technologies": technologies,
            "technology_names": technology_names,
            "funding_events": funding_events,
            "latest_funding_stage": org.get("latest_funding_stage"),
            "latest_funding_date": org.get("latest_funding_round_date"),
            "headcount_growth": headcount_growth,
            "follower_count": org.get("num_followers") or org.get("linkedin_follower_count"),
            "employee_count_range": org.get("employee_count_range"),
            "headquarters": f"{org.get('city', '')}, {org.get('state', '')}, {org.get('country', '')}".strip(", "),
            "apollo_id": org.get("id"),
            "domain": org.get("domain")
        }

    result = {
        "person_name": person.get("name"),
        "company_name": org.get("name") or org.get("company_name"),
        "first_name": person.get("first_name"),
        "last_name": person.get("last_name"),
        "person_email": person.get("email"),
        "linkedin_url": person.get("linkedin_url"),
        "headline": person.get("headline") or person.get("title"),
        "photo_url": person.get("photo_url"),
        "city": person.get("city"),
        "state": person.get("state"),
        "country": person.get("country"),
        "apollo_person_id": person.get("id"),
        "apollo_organization_id": org.get("id"),
        "description": org.get("short_description"),
        "industries": org.get("industries") or ([org.get("industry")] if org.get("industry") else []),
        "website": org.get("website_url"),
        "domain": org.get("domain"),
        "company_linkedin_url": org.get("linkedin_url"),
        "company_stats": company_stats,
        **company_stats
    }

    # --- Million Verifier Integration ---
    if result.get("person_email") and million_verifier_enabled:
        try:
            from utils.email_verifier import verify_email
            mv_key = os.getenv("MILLION_VERIFIER_API_KEY")
            if mv_key:
                logger.info(f"MILLION VERIFIER: Verifying email {result['person_email']}...")
                verification_status = await verify_email(result["person_email"], mv_key)
                result["email_verification_status"] = verification_status
            else:
                result["email_verification_status"] = None
        except Exception as e:
            logger.error(f"Error during email verification: {e}")
            result["email_verification_status"] = None
    else:
        result["email_verification_status"] = None

    return result

    # --- Million Verifier Integration ---
    if result.get("person_email") and million_verifier_enabled:
        try:
            from utils.email_verifier import verify_email
            mv_key = os.getenv("MILLION_VERIFIER_API_KEY")
            if mv_key:
                logger.info(f"MILLION VERIFIER: Verifying email {result['person_email']}...")
                verification_status = await verify_email(result["person_email"], mv_key)
                result["email_verification_status"] = verification_status
            else:
                result["email_verification_status"] = None
        except Exception as e:
            logger.error(f"Error during email verification: {e}")
            result["email_verification_status"] = None
    else:
        result["email_verification_status"] = None

    return result

async def get_apollo_company_data(
    linkedin_url: str = None,
    apollo_id: str = None,
    million_verifier_enabled: bool = False
):
    """
    Enrichment using Apollo People Match or Bulk Match API.
    """
    api_key = os.getenv("APOLLO_API_KEY", "").strip()
    if not api_key:
        logger.warning("APOLLO_API_KEY not found in environment.")
        return {}
    
    import httpx
    try:
        if apollo_id:
            logger.debug(f"DEBUG: Apollo Enrichment by ID: {apollo_id}")
            url = "https://api.apollo.io/v1/people/match"
            headers = {
                "Content-Type": "application/json",
                "X-Api-Key": api_key
            }
            payload = {
                "id": apollo_id,
                "reveal_personal_emails": True
            }
        else:
            logger.debug(f"DEBUG: Apollo Enrichment by URL: {linkedin_url}")
            url = "https://api.apollo.io/v1/people/match"
            headers = {
                "Content-Type": "application/json",
                "X-Api-Key": api_key
            }
            payload = {
                "linkedin_url": linkedin_url,
                "reveal_personal_emails": True
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            if response.status_code != 200:
                logger.error(f"Apollo API Error: {response.status_code} - {response.text}")
                return {}

            res = response.json()
            
            # both endpoints now return {"person": {...}} structure when successful
            return await _map_apollo_response_to_enrichment(res, million_verifier_enabled)

    except Exception as e:
        logger.error(f"Error calling Apollo API: {e}")
        
    return {}

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
            logger.error(f"Error fetching data for {url}: {e}")
            all_competitor_data.append({
                "url": url,
                "error": str(e)
            })

    from prompts.sales_prompts import COMPETITOR_POST_ANALYZER_PROMPT
    
    messages = [
        SystemMessage(content=COMPETITOR_POST_ANALYZER_PROMPT),
        HumanMessage(content=json.dumps(all_competitor_data))
    ]
    
    model = get_gemini_model(model="gemini-3-flash-preview", temperature=1)
    response = model.invoke(messages)
    return response.content

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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
        data = response.json()
        payload = data.get("data")
        if isinstance(payload, dict):
            return payload.get("comments", [])
        elif isinstance(payload, list):
            return payload
        return []
    except Exception as e:
        logger.error(f"Error fetching comments for post {post_id}: {e}")
        return []

def analyze_lead_with_ai(lead: dict, icp_data: dict):
    """Evaluates a single lead against the ICP using AI."""
    try:
        model = get_gemini_model(model="gemini-3-flash-preview", temperature=0) # Use 0 temp for consistent scoring
        
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
        logger.error(f"Error analyzing lead with AI: {e}")
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
        logger.error(f"Error fetching commenters for post {post_id}: {e}")
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
            "comment": comment_text,
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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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
        logger.debug(f"Starting discovery for competitor: {competitor_url}")
        # 1. Fetch recent posts
        response = requests.get(posts_url, headers=headers, params={"username": user_name}, timeout=15)
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
            logger.debug(f"No posts found in response for {user_name}. Keys present: {list(posts_data.keys()) if isinstance(posts_data, dict) else 'is list'}")
            logger.debug(f"Response snippet: {str(posts_data)[:200]}")

        logger.debug(f"Found {len(posts)} total posts for {user_name}")

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
        
        logger.debug(f"{len(recent_posts)} posts within last 30 days out of {len(posts)}")
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
                logger.error(f"Post processing exception for {post.get('id', 'unknown')}: {exc}")
        
        logger.debug(f"Found {len(raw_leads_buffer)} interactions for {user_name}")
        return raw_leads_buffer
    except Exception as e:
        logger.error(f"CRITICAL Error discovering leads from competitor {competitor_url}: {e}", exc_info=True)
        raise e


async def batch_classify_profiles_async(profiles: List[Dict], company_context: str | None = None):
    """
    Async version: Classifies a batch of profiles using LLM based on headline and company context.
    Expects profiles list of dicts: [{'id': 'url', 'headline': '...'}, ...]
    """
    if not profiles:
        return {}
        
    try:
        llm = get_gemini_model(temperature=0, model="gemini-3-flash-preview")
        structured_llm = llm.with_structured_output(BatchProfileClassification)
        
        # Format profiles for prompt
        profiles_text = json.dumps(profiles, indent=2)
        logger.info(f"Profiles text: {profiles_text}")
        prompt = BATCH_PROFILE_CLASSIFIER_PROMPT.format(
            company_context=company_context or DEFAULT_COMPANY_CONTEXT,
            profiles_data=profiles_text
        )
        logger.info(f"Prompt: {prompt}")
        # Native async call
        response = await structured_llm.ainvoke([
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content=prompt)
        ])
        
        results_map = {}

        for item in _extract_classifications(response):
            # Handle item as either a Pydantic model or a dict
            if hasattr(item, "id"):
                r_id = item.id
                r_data = {
                    "is_fit": getattr(item, "is_fit", False),
                    "is_competitor": getattr(item, "is_competitor", False),
                    "is_decision_maker": getattr(item, "is_decision_maker", False),
                    "is_buy_signal": getattr(item, "is_buy_signal", False),
                    "is_strategic_seller": getattr(item, "is_strategic_seller", False),
                    "reasoning": getattr(item, "reasoning", ""),
                    "intent": getattr(item, "intent", None),
                    "post_topic_depth": getattr(item, "post_topic_depth", None),
                    "sentiment": getattr(item, "sentiment", None)
                }
            else:
                r_id = item.get("id")
                r_data = {
                    "is_fit": item.get("is_fit", False),
                    "is_competitor": item.get("is_competitor", False),
                    "is_decision_maker": item.get("is_decision_maker", False),
                    "is_buy_signal": item.get("is_buy_signal", False),
                    "is_strategic_seller": item.get("is_strategic_seller", False),
                    "reasoning": item.get("reasoning", ""),
                    "intent": item.get("intent"),
                    "post_topic_depth": item.get("post_topic_depth"),
                    "sentiment": item.get("sentiment")
                }
            
            if r_id:
                results_map[r_id] = r_data
                
        return results_map

    except Exception as e:
        logger.error(f"Error in async batch classification: {type(e).__name__}: {e}")
        return {}

async def get_posts_by_keyword(keywords: List[str]):
    """Get linkedin posts by keywords - Async version with parallel execution for multiple keywords"""
    import asyncio
    
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    if not linkedin_base_url:
        logger.error("LINKEDIN_RAPID_BASE_URL not set")
        return []
        
    search_url = f"{linkedin_base_url.rstrip('/')}/posts/search"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_for_single_keyword(keyword: str):
        try:
            logger.debug(f"Fetching posts for keyword: '{keyword}'")
            # Set a timeout for the API call
            response = await asyncio.to_thread(
                requests.get,
                search_url,
                headers=headers,
                params={"keyword": keyword},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.debug(f"API error for keyword '{keyword}': {response.status_code}")
                # Raise exception to trigger Pub/Sub retry
                response.raise_for_status()

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
            logger.error(f"Failed fetching for keyword '{keyword}': {e}")
            # Re-raising for Pub/Sub retry
            raise

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

        logger.debug(f"Found {len(all_posts)} unique posts across {len(keywords)} keywords")
        return all_posts

    except Exception as e:
        logger.error(f"Error in get_posts_by_keyword: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def discover_leads_from_keywords(keywords: List[str]):
    """
    High-level function to discover leads via keyword search.
    1. Fetches posts matching keywords.
    2. Extracts the AUTHOR of each post as a lead.
    """
    posts = await get_posts_by_keyword(keywords)
    logger.debug(f"Processing {len(posts)} posts for leads extraction...")
    
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
                "comment": f"Posted about keywords: {post_text[:200]}...", # Storing post text as 'comment' context
                "source_post": post_text[:100] + "...",
                "source_post_url": source_post_url or "",
                "competitor": competitor_source, # Marker with keyword
                "is_fit": False,
                "is_competitor": False,
                "is_decision_maker": False,
                "fit_reasoning": ""
            })
            
        except Exception as e:
            logger.error(f"Error extracting lead from post: {e}")
            continue
            
    logger.debug(f"Extracted {len(leads)} unique leads from keyword search posts.")
    return leads


def get_linkedin_jobs(
    keywords: str = None,
    location: str = None,
    company_id: str = None,
    sort: str = None,
    page_number: int = 1,
    date_posted: str = None,
    easy_apply: bool = None,
    remote: str = None,
    experience: str = None,
    job_type: str = None
):
    """
    Fetches active job listings from /jobs/search using the RapidAPI client.
    """
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    if not linkedin_base_url:
        linkedin_base_url = "https://linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
        
    url = f"{linkedin_base_url.rstrip('/')}/jobs/search"
    
    querystring = {}
    if keywords:
        querystring["keywords"] = keywords
    if location:
        querystring["location"] = location
    if company_id:
        querystring["company_id"] = str(company_id)
    if sort:
        querystring["sort"] = sort
    if page_number:
        querystring["page_number"] = str(page_number)
    if date_posted:
        querystring["date_posted"] = date_posted
    if easy_apply is not None:
        querystring["easy_apply"] = "true" if easy_apply else "false"
    if remote:
        querystring["remote"] = remote
    if experience:
        querystring["experience"] = experience
    if job_type:
        querystring["job_type"] = job_type

    # Ensure keywords is present as required by the API
    if not querystring.get("keywords") and company_id:
        querystring["keywords"] = "engineer"
        
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }

    try:
        logger.info(f"Querying LinkedIn Jobs API: {url} with params {querystring}")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        res_data = response.json()
        
        if isinstance(res_data, dict) and "message" in res_data:
             if "exceeded the MONTHLY quota" in res_data["message"]:
                logger.warning(f"LinkedIn Jobs API Rate Limit: {res_data['message']}")
                return []
                
        jobs_list = res_data.get("data", res_data) if isinstance(res_data, dict) else res_data
        if not isinstance(jobs_list, list):
            if isinstance(jobs_list, dict) and "jobs" in jobs_list:
                jobs_list = jobs_list["jobs"]
            else:
                jobs_list = []
                
        standardized_jobs = []
        for job in jobs_list:
            if not isinstance(job, dict):
                continue
            
            # Extract company details, supporting both object and direct string/URL values
            company_val = job.get("company")
            if isinstance(company_val, dict):
                company_name = company_val.get("name")
                company_url = company_val.get("url")
            else:
                company_name = company_val or job.get("company_name")
                company_url = job.get("company_url")
            
            standardized_jobs.append({
                "title": job.get("job_title") or job.get("title") or "Unknown Position",
                "company_name": company_name or "Target Company",
                "company_url": company_url,
                "company_urn": job.get("company_urn"),
                "job_id": job.get("job_id"),
                "location": job.get("location") or "Remote / Onsite",
                "salary": job.get("salary"),
                "posted_at_epoch": job.get("posted_at_epoch"),
                "skills": job.get("skills") or [],
                "benefits": job.get("benefits") or [],
                "is_easy_apply": job.get("is_easy_apply"),
                "is_promoted": job.get("is_promoted"),
                "applicant_count": job.get("applicant_count"),
                "description": job.get("description") or job.get("job_description") or "",
                "created_at_epoch": job.get("created_at_epoch"),
                "geo_id": job.get("geo_id"),
                "navigation_subtitle": job.get("navigation_subtitle"),
                "is_verified": job.get("is_verified"),
                "job_insights": job.get("job_insights") or [],
                "apply_url": job.get("apply_url"),
                "posted_time": job.get("posted_at") or job.get("created_at") or job.get("date_posted") or "Active",
                "url": job.get("job_url") or job.get("apply_url") or job.get("job_posting_url") or job.get("url") or "",
                "remote": job.get("work_type") or job.get("remote") or "onsite"
            })
        return standardized_jobs
    except Exception as e:
        logger.error(f"Error fetching jobs from RapidAPI: {e}")
        return []
        
def get_linkedin_job_details(job_id: str) -> dict:
    """
    Fetches complete details for a specific job, including the full job description.
    """
    api_key = os.getenv("RAPID_API_KEY")
    linkedin_base_url = os.getenv("LINKEDIN_RAPID_BASE_URL")
    
    if not linkedin_base_url:
        linkedin_base_url = "https://linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
        
    url = f"{linkedin_base_url.rstrip('/')}/jobs/details"
    querystring = {"job_id": str(job_id)}
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "linkedin-scraper-api-real-time-fast-affordable.p.rapidapi.com"
    }
    
    try:
        logger.info(f"Querying LinkedIn Job Details API: {url} with job_id {job_id}")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        res_data = response.json()
        
        if isinstance(res_data, dict) and "message" in res_data:
             if "exceeded the MONTHLY quota" in res_data["message"]:
                logger.warning(f"LinkedIn Job Details API Rate Limit: {res_data['message']}")
                return {}
                
        data = res_data.get("data", res_data) if isinstance(res_data, dict) else {}
        if not data:
            return {}
            
        return {
            "description": data.get("description") or data.get("job_description") or "",
            "skills": data.get("skills") or [],
            "apply_url": data.get("apply_url") or data.get("job_url") or "",
            "salary": data.get("salary") or "",
            "benefits": data.get("benefits") or []
        }
    except Exception as e:
        logger.error(f"Error fetching job details for ID {job_id}: {e}")
        return {}

async def discover_leads_from_jobs(
    keywords: str = None,
    location: str = None,
    sort: str = None,
    date_posted: str = None,
    easy_apply: bool = None,
    remote: str = None,
    experience: str = None,
    job_type: str = None,
    company_id: str = None,
    apollo_api_key: str = None
) -> List[dict]:
    """
    Finds hiring companies using get_linkedin_jobs and immediately returns 
    starter company cards for background enrichment.
    """
    logger.info(f"Hiring Lead Discovery initiated with keyword: {keywords}")
    jobs = get_linkedin_jobs(
        keywords=keywords,
        location=location,
        sort=sort,
        date_posted=date_posted,
        easy_apply=easy_apply,
        remote=remote,
        experience=experience,
        job_type=job_type,
        company_id=company_id
    )
    
    if not jobs:
        logger.info("No active jobs found for lead discovery.")
        return []
        
    # Group jobs by company name to avoid duplicate company cards
    grouped_jobs = {}
    for job in jobs:
        cname = job.get("company_name")
        if cname and cname != "Target Company":
            if cname not in grouped_jobs:
                grouped_jobs[cname] = []
            grouped_jobs[cname].append(job)
            
    if not grouped_jobs:
        logger.info("No companies with valid names found in job listings.")
        return []

    # Construct instant starter company leads
    leads = []
    for cname, company_jobs in grouped_jobs.items():
        primary_job = company_jobs[0]
        job_titles = [j.get("title") for j in company_jobs]
        desc_snippet = primary_job.get("description", "")[:150] + "..." if len(primary_job.get("description", "")) > 150 else primary_job.get("description", "")
        
        hiring_comment = f"Active hiring signals detected at company '{cname}':\n- hiring for: {', '.join(job_titles[:3])}\n- Job snippet: {desc_snippet}"
        
        leads.append({
            "name": cname,
            "headline": f"Hiring: {primary_job.get('title')} in {primary_job.get('location')}",
            "linkedin_url": primary_job.get("company_url") or f"https://www.linkedin.com/company/{cname.lower().replace(' ', '')}",
            "comment": hiring_comment,
            "source_post": f"Hiring: {primary_job.get('title')}",
            "source_post_url": primary_job.get("url") or "",
            "competitor": "LinkedIn Jobs",
            "website": "", # To be enriched in the background
            "email": None,
            "email_verification_status": None,
            "is_fit": False,
            "is_competitor": False,
            "is_decision_maker": False,
            "fit_reasoning": "Locating corporate decision makers & executing AI evaluation in the background...",
            "lead_source": "linkedin_job",
            "profile_metadata": {
                "company_name": cname,
                "job_title": primary_job.get("title"),
                "is_hiring_company": True,
                "status": "enriching",
                "hiring_jobs": company_jobs
            }
        })
        
    logger.info(f"Instant discovery returned {len(leads)} starter company leads.")
    return leads

async def enrich_job_leads_background_pipeline(
    grouped_jobs: dict,
    apollo_api_key: str = None,
    user_id: str = None,
    org_id: str = None
) -> List[dict]:
    """
    Takes grouped jobs, resolves corporate website domains, 
    queries Apollo in batches for decision makers, and maps them back.
    """
    if not grouped_jobs:
        return []

    final_api_key = apollo_api_key or os.getenv("APOLLO_API_KEY")
    if not final_api_key:
        logger.warning("Apollo API Key is missing. Cannot search for decision-makers.")
        return []

    # Default target roles for strategic outreach
    target_titles = [
        "CTO", "Chief Technology Officer", "VP of Engineering", 
        "Director of Engineering", "Head of Engineering",
        "VP of Operations", "Operations Director", "COO", "Chief Operating Officer",
        "Billing Manager", "Finance Director", "VP of HR", "HR Director",
        "Recruiting Manager", "Recruiter", "Co-Founder", "Founder", "CEO"
    ]
    
    # Dynamically fetch target titles from global/user ICP if available
    try:
        from db.database import SessionLocal
        from db.crud import get_active_icp
        async with SessionLocal() as db_session:
            icp_data = await get_active_icp(db_session, user_id=user_id, org_id=org_id)
            if icp_data and icp_data.get("job_title"):
                title_val = icp_data.get("job_title")
                if isinstance(title_val, list):
                    target_titles = [t.strip() for t in title_val if t.strip()]
                elif isinstance(title_val, str):
                    if "," in title_val:
                        target_titles = [t.strip() for t in title_val.split(",") if t.strip()]
                    elif ";" in title_val:
                        target_titles = [t.strip() for t in title_val.split(";") if t.strip()]
                    else:
                        target_titles = [title_val.strip()]
                logger.info(f"Dynamically loaded target titles from ICP: {target_titles}")
    except Exception as e:
        logger.warning(f"Failed to fetch dynamic ICP target titles: {e}. Using defaults.")

    fallback_titles = ["CEO", "Founder", "Owner", "President", "VP", "Director", "Manager"]
    
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": final_api_key
    }
    
    search_url = "https://api.apollo.io/api/v1/mixed_people/api_search"
    companies_list = list(grouped_jobs.keys())
    logger.info(f"Companies list: {companies_list}")
    # website domain resolution for all unique companies concurrently (with semaphore throttling)
    logger.info(f"Resolving domains for {len(companies_list)} hiring companies in background task.")
    loop = asyncio.get_event_loop()
    
    company_domains = {}
    
    def get_person_domain(p):
        # 1. Try organization name match (Highly reliable as we matched the queried companies list)
        org_name = p.get("organization", {}).get("name") or p.get("organization_name")
        if org_name:
            org_name_lower = org_name.lower().strip()
            for original_name, dom in company_domains.items():
                orig_name_lower = original_name.lower().strip()
                if orig_name_lower == org_name_lower or orig_name_lower in org_name_lower or org_name_lower in orig_name_lower:
                    if dom:
                        return dom.lower().strip()

        # 2. Try email domain
        email = p.get("email")
        if email and "@" in email:
            return email.split("@")[-1].lower().strip()

        # 3. Try organization website
        website = p.get("organization", {}).get("website")
        if website:
            dom = website.split("//")[-1].split("/")[0].replace("www.", "").lower().strip()
            if dom:
                return dom

        # 4. Fallback to existing fields
        return p.get("organization_domain") or p.get("organization", {}).get("primary_domain")

    sem = asyncio.Semaphore(5)

    async def resolve_company_domain(cname: str) -> str:
        async with sem:
            jobs = grouped_jobs.get(cname, [])
            if not jobs:
                return ""
            
            company_url = jobs[0].get("company_url")
            if company_url:
                cleaned = company_url.rstrip('/')
                parts = cleaned.split('/')
                identifier = parts[-1]
                if identifier in ("life", "about", "jobs") and len(parts) > 1:
                    identifier = parts[-2]

                logger.info(f"Company identifier: {identifier}") 
                if identifier:
                    try:
                        logger.info(f"Resolving website domain for '{cname}' via LinkedIn identifier '{identifier}'")
                        company_res = await loop.run_in_executor(
                            None,
                            lambda: get_company_details(identifier)
                        )
                        logger.info(f"Company details: {company_res}")
                        if company_res:
                            website_url = (
                                company_res.get("website") or 
                                company_res.get("basic_info", {}).get("website") or 
                                company_res.get("stats", {}).get("website") or
                                company_res.get("basic_info", {}).get("websiteUrl") or
                                company_res.get("websiteUrl")
                            )
                            logger.info(f"Website URL: {website_url}")
                            if website_url:
                                domain = website_url.lower().strip()
                                if domain.startswith("http://"):
                                    domain = domain[7:]
                                elif domain.startswith("https://"):
                                    domain = domain[8:]
                                if domain.startswith("www."):
                                    domain = domain[4:]
                                domain = domain.split('/')[0]
                                logger.info(f"Resolved domain '{domain}' for '{cname}'")
                                return domain
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for '{cname}' via get_company_details: {e}")
            
            # Resilient fallback: guess the domain from the company name
            guessed = cname.lower().strip()
            guessed = "".join(ch for ch in guessed if ch.isalnum() or ch.isspace())
            guessed = guessed.replace(" ", "")
            if not guessed:
                guessed = "unknown"
            domain = f"{guessed}.com"
            logger.info(f"Using guessed fallback domain '{domain}' for company '{cname}'")
            return domain

    # Concurrently resolve domains
    domain_tasks = [resolve_company_domain(cname) for cname in companies_list]
    domain_results = await asyncio.gather(*domain_tasks)
    
    for cname, dom in zip(companies_list, domain_results):
        company_domains[cname] = dom
        
    domains_list = list(set(filter(None, company_domains.values())))
    logger.info(f"Resolved {len(domains_list)} unique domains for Apollo search: {domains_list}")
    
    people = []
    
    if domains_list:
        # Phase 1: Batch search for high-priority targeted titles using domains in q_organization_domains_list
        payload = {
            "q_organization_domains_list": domains_list,
            "person_titles": target_titles,
            "page": 1,
            "per_page": 100
        }
        
        try:
            logger.info(f"Querying Apollo in batch for targeted decision-makers at {len(domains_list)} company domains.")
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(search_url, headers=headers, json=payload)
            )
            if response.status_code == 200:
                people = response.json().get("people", [])
            else:
                logger.warning(f"Apollo domain batch query failed with status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error executing primary Apollo domain batch search: {e}")
            
        logger.info(f"People found in primary search: {people}")
        # Group resolved people by domain to find missing companies
        resolved_domains = set()
        for person in people:
            dom = get_person_domain(person)
            if dom:
                resolved_domains.add(dom.lower())
                
        # Phase 2: Identify missing company domains and query fallback roles for them in a secondary batch
        missing_domains = [dom for dom in domains_list if dom.lower() not in resolved_domains]
        if missing_domains:
            logger.info(f"No targeted decision-makers found for {len(missing_domains)} domains. Querying fallback roles.")
            fallback_payload = {
                "q_organization_domains_list": missing_domains,
                "person_titles": fallback_titles,
                "page": 1,
                "per_page": 100
            }
            try:
                fallback_response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(search_url, headers=headers, json=fallback_payload, timeout=15)
                )
                if fallback_response.status_code == 200:
                    fallback_people = fallback_response.json().get("people", [])
                    people.extend(fallback_people)
                else:
                    logger.warning(f"Apollo fallback domain batch query failed with status {fallback_response.status_code}")
            except Exception as e:
                logger.error(f"Error executing fallback Apollo domain batch search: {e}")

    # Phase 3: Process all retrieved people and construct lead list
    leads = []
    processed_emails = set()
    
    for person in people:
        email = person.get("email")
        # De-duplicate leads by email to prevent duplicate cards
        if email:
            if email in processed_emails:
                continue
            processed_emails.add(email)
            
        name = person.get("name") or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or "Unknown"
        title = person.get("title") or "Executive"
        lurl = person.get("linkedin_url")
        if not lurl:
            lurl = f"apollo_id:{person.get('id')}"
            
        cname_apollo = person.get("organization", {}).get("name") or person.get("organization_name") or "Unknown Company"
        domain_apollo = get_person_domain(person)
        
        # Match back to original job company
        company_jobs = []
        matched_original_name = cname_apollo
        
        # First try to match by domain (highly accurate)
        if domain_apollo:
            lower_domain = domain_apollo.lower().strip()
            for original_name, resolved_domain in company_domains.items():
                if resolved_domain and resolved_domain.lower().strip() == lower_domain:
                    company_jobs = grouped_jobs[original_name]
                    matched_original_name = original_name
                    break
                    
        # Fallback to name-based substring matching if domain match not found
        if not company_jobs:
            lower_cname_apollo = cname_apollo.lower()
            for original_name in companies_list:
                if original_name.lower() == lower_cname_apollo or original_name.lower() in lower_cname_apollo or lower_cname_apollo in original_name.lower():
                    company_jobs = grouped_jobs[original_name]
                    matched_original_name = original_name
                    break
                    
        if not company_jobs:
            continue
            
        # Extract active jobs summary
        job_summaries = []
        for job in company_jobs[:3]:
            desc_snippet = job.get("description", "")[:120] + "..." if len(job.get("description", "")) > 120 else job.get("description", "")
            job_summaries.append(f"'{job.get('title')}' in {job.get('location')} (Snippet: {desc_snippet})")
        
        hiring_comment = f"Active hiring signals detected at company '{matched_original_name}':\n- " + "\n- ".join(job_summaries)
        
        # Determine the company's starter card URL to be used as old_linkedin_url for SSE replacement mapping
        starter_company_url = company_jobs[0].get("company_url") or f"https://www.linkedin.com/company/{matched_original_name.lower().replace(' ', '')}"
        
        leads.append({
            "name": name,
            "headline": f"{title} at {matched_original_name}",
            "linkedin_url": lurl,
            "old_linkedin_url": starter_company_url, # Key field for frontend SSE mapping!
            "comment": hiring_comment,
            "source_post": f"Hiring: {company_jobs[0].get('title')}",
            "source_post_url": company_jobs[0].get("url") or "",
            "competitor": "LinkedIn Jobs",
            "website": person.get("organization", {}).get("website") or person.get("organization_domain") or company_domains.get(matched_original_name) or "",
            "email": email,
            "email_verification_status": person.get("email_status"),
            "is_fit": False,
            "is_competitor": False,
            "is_decision_maker": False,
            "fit_reasoning": "",
            "lead_source": "linkedin_job",
            "profile_metadata": {
                "apollo_id": person.get("id"),
                "company_name": matched_original_name,
                "job_title": title,
                "email": email,
                "email_status": person.get("email_status"),
                "state": person.get("state"),
                "city": person.get("city"),
                "photo_url": person.get("photo_url"),
                "employee_count": person.get("organization", {}).get("estimated_num_employees"),
                "domain": person.get("organization", {}).get("primary_domain") or person.get("organization_domain"),
                "hiring_jobs": company_jobs
            }
        })
        
    logger.info(f"Background Apollo Job Enrichment completed. Found {len(leads)} decision-maker leads.")
    return leads
