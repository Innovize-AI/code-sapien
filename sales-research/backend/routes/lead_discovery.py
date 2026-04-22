from typing import List, Optional, Union
from pydantic import BaseModel, Field
import os
import json
import requests
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
# Internal imports
from db.models import OrganizationSettings, IdentifiedProfile
from agents.linkedin_agent import enrich_company_waterfall
from db.crud import batch_upsert_identified_profiles, upsert_company

logger = logging.getLogger(__name__)

# --- Construction logic remains same ---

class LeadDiscoveryInput(BaseModel):
    industry: Optional[Union[str, List[str]]] = Field(None, description="Target industry (Legacy)")
    job_title: Optional[Union[str, List[str]]] = Field(None, description="Target job title (Legacy)")
    location: Optional[Union[str, List[str]]] = Field(None, description="Target location (Legacy)")
    company_size: Optional[Union[str, List[str]]] = Field(None, description="Target company size (Legacy)")
    provider: Optional[str] = Field("tavily", description="Search provider: 'tavily', 'apollo', or 'linkedin_keyword'")
    keywords: Optional[Union[str, List[str]]] = Field(None, description="Keywords for LinkedIn post search")

    # Advanced Apollo Filters
    person_titles: Optional[Union[str, List[str]]] = Field(None)
    include_similar_titles: Optional[bool] = Field(None, description="Whether to include fuzzy-matched job titles")
    person_seniorities: Optional[Union[str, List[str]]] = Field(None)
    person_locations: Optional[Union[str, List[str]]] = Field(None)
    organization_locations: Optional[Union[str, List[str]]] = Field(None)
    organization_domains: Optional[Union[str, List[str]]] = Field(None)
    organization_ids: Optional[Union[str, List[str]]] = Field(None, description="Apollo company IDs to target directly")
    contact_email_status: Optional[Union[str, List[str]]] = Field(None)
    organization_num_employees_ranges: Optional[Union[str, List[str]]] = Field(None)
    revenue_min: Optional[int] = Field(None)
    revenue_max: Optional[int] = Field(None)
    currently_using_all_of_technology_uids: Optional[Union[str, List[str]]] = Field(None, description="Org must use ALL of these technologies")
    currently_using_any_of_technology_uids: Optional[Union[str, List[str]]] = Field(None, description="Org uses ANY of these technologies")
    currently_not_using_any_of_technology_uids: Optional[Union[str, List[str]]] = Field(None, description="Exclude orgs using any of these technologies")
    q_organization_job_titles: Optional[Union[str, List[str]]] = Field(None, description="Active job posting titles at org")
    organization_job_locations: Optional[Union[str, List[str]]] = Field(None, description="Locations where org is actively hiring")
    organization_num_jobs_range_min: Optional[int] = Field(None, description="Minimum number of active job postings")
    organization_num_jobs_range_max: Optional[int] = Field(None, description="Maximum number of active job postings")
    organization_job_posted_at_range_min: Optional[str] = Field(None, description="Earliest job post date (YYYY-MM-DD)")
    organization_job_posted_at_range_max: Optional[str] = Field(None, description="Latest job post date (YYYY-MM-DD)")
    q_keywords: Optional[str] = Field(None, description="General keyword search — use this for industry filtering (e.g. 'fintech', 'healthcare')")
    page: Optional[int] = Field(1)
    
def normalize_to_list(val: Optional[Union[str, List[str]]]) -> List[str]:
    """Helper to ensure we send flat lists of non-empty strings to Apollo."""
    if not val:
        return []
    if isinstance(val, list):
        # Flatten any accidental nested lists and remove empty strings
        flat_list = []
        for item in val:
            if isinstance(item, list):
                flat_list.extend([str(i).strip() for i in item if i])
            elif item:
                flat_list.append(str(item).strip())
        return list(set(flat_list)) # Unique values
    return [str(val).strip()] if val else []

def generate_search_query(input_data: LeadDiscoveryInput) -> str:
    """
    Constructs a Google Dork / X-Ray search query for Tavily.
    Target: site:linkedin.com/in 
    """
    query_parts = ["site:linkedin.com/in"]
    
    # Add negative keywords to avoid job postings, company pages, etc.
    query_parts.append('-intitle:"jobs"')
    query_parts.append('-intitle:"hiring"')
    
    # Helper to handle strings or lists for search queries
    def format_search_term(term: Optional[Union[str, List[str]]]) -> Optional[str]:
        if not term:
            return None
        if isinstance(term, list):
            valid_terms = [f'"{t}"' for t in term if t]
            if not valid_terms:
                return None
            return f"({' OR '.join(valid_terms)})"
        return f'"{term}"'

    # Add specific constraints
    if input_data.job_title:
        formatted = format_search_term(input_data.job_title)
        if formatted: query_parts.append(formatted)
    
    if input_data.industry:
        formatted = format_search_term(input_data.industry)
        if formatted: query_parts.append(formatted)
        
    if input_data.location:
        formatted = format_search_term(input_data.location)
        if formatted: query_parts.append(formatted)

    return " ".join(query_parts)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def find_leads_tavily(input_data: LeadDiscoveryInput, api_key: str = None) -> List[dict]:
    """
    Uses Tavily to search for LinkedIn profiles matching the criteria.
    Returns a list of dicts: {"url": str, "website": str}
    """
    # Set the key in env for LangChain tool
    if api_key:
        os.environ["TAVILY_API_KEY"] = api_key
    elif not os.environ.get("TAVILY_API_KEY"):
         print("WARNING: TAVILY_API_KEY not found.")
         return []

    query = generate_search_query(input_data)
    print(f"Executing Search Query: {query}")
    
    # Deferred heavy import
    from langchain_community.tools.tavily_search import TavilySearchResults
    
    # max_results can be adjusted. 5-10 is usually good for a first pass.
    tavily_tool = TavilySearchResults(max_results=5)
    
    try:
        results = tavily_tool.invoke({"query": query})
        
        leads = []
        for res in results:
            url = res.get("url")
            # Basic validation to ensure it's a profile URL
            if url and "linkedin.com/in/" in url:
                # Tavily doesn't usually return the company website directly in this dork
                # We return an empty string, allowing the enrichment logic or user to fill it
                leads.append({"url": url, "website": ""})
                
        return leads
        
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        return []

def map_apollo_person(person: dict, is_enriched: bool = True) -> dict:
    """Helper to map Apollo person object to our Lead format."""
    # Prefer LinkedIn URL from enrichment, fallback to ID based URL if possible
    li_url = person.get("linkedin_url") or person.get("facebook_url") or person.get("twitter_url")
    
    # If not enriched, we might not have the URL yet. Use a placeholder for the frontend to handle.
    pid = person.get("id")
    final_url = li_url or f"apollo_id:{pid}" if pid else "unknown"
    
    # Construct a useful display name
    first = person.get("first_name", "Unknown")
    last = person.get("last_name", "")
    full_name = f"{first} {last}".strip()
    
    # Organization
    org = person.get("organization") or {}
    org_name = org.get("name", "")
    website = org.get("website_url") or \
              (f"https://{org['primary_domain']}" if org.get("primary_domain") else "")
    apollo_org_id = org.get("id") or person.get("organization_id")

    # Location
    city = person.get("city")
    state = person.get("state")
    country = person.get("country")
    location = f"{city}, {country}" if city and country else (city or country or "N/A")

    return {
        "url": final_url,
        "website": website,
        "name": full_name,
        "comment": f"{person.get('title', 'N/A')} at {org_name}" if org_name else person.get('title', 'N/A'),
        "is_enriched": is_enriched,
        "email": person.get("email"),
        "company_name": org_name,
        "industry": org.get("industry") or org.get("primary_industry"),
        "employee_count": org.get("estimated_num_employees") or org.get("num_employees"),
        "revenue_estimate": org.get("annual_revenue_printed") or org.get("organization_revenue_printed"),
        "location": location,
        "photo_url": person.get("photo_url"),
        "metadata": {
            "email": person.get("email"),
            "email_status": person.get("email_status"),
            "seniority": person.get("seniority"),
            "apollo_id": pid,
            "company_name": org_name,
            "apollo_org_id": apollo_org_id,
            "industry": org.get("industry"),
            "city": city,
            "state": state,
            "country": country
        }
    }


from utils.sse_manager import event_manager

async def enrich_and_save_leads(
    db: AsyncSession, 
    person_ids: List[str], 
    user_id: str = None,
    source_post: str = "Apollo Discovery",
    competitor: str = "Apollo"
) -> List[dict]:
    """
    Core logic to enrich person IDs via waterfall, upsert their companies, 
    and save/update identified profiles in the database.
    Now broadcasts updates via SSE for real-time UI synchronization.
    """
    if not person_ids:
        return []

    logger.info(f"Background Enrichment Started for {len(person_ids)} leads via Waterfall...")
    
    # Run Waterfall in parallel
    tasks = [enrich_company_waterfall(person_id=pid, million_verifier_enabled=True) for pid in person_ids]
    waterfall_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    raw_leads_to_save = []
    enriched_for_broadcast = []

    for i, enriched in enumerate(waterfall_results):
        pid = person_ids[i]
        if isinstance(enriched, Exception) or not enriched:
            logger.error(f"Waterfall enrichment failed for {pid}: {enriched}")
            continue

        try:
            # 1. Handle Company Linkage
            comp_id = None
            if enriched.get("company_linkedin_url") or enriched.get("domain"):
                company_obj = await upsert_company(
                    db, 
                    enriched, 
                    linkedin_url=enriched.get("company_linkedin_url"),
                    domain=enriched.get("domain")
                )
                if company_obj:
                    comp_id = str(company_obj.id)

            # 2. Map for batch_upsert
            url = enriched.get("linkedin_url") or f"apollo_id:{pid}"
            
            meta = {
                **enriched,
                "person_email": enriched.get("person_email"),
                "email_status": enriched.get("email_verification_status"),
                "apollo_id": pid,
                "company_name": enriched.get("company_name"),
                "is_enriched": True,
                "photo_url": enriched.get("photo_url")
            }
            
            lead_payload = {
                "linkedin_url": url,
                "name": enriched.get("person_name"),
                "headline": enriched.get("headline"),
                "company_id": comp_id,
                "email": enriched.get("person_email"),
                "email_verification_status": enriched.get("email_verification_status"),
                "website": enriched.get("website"),
                "profile_metadata": meta,
                "source_post": source_post,
                "competitor": competitor
            }
            
            # Map old URL for UI transition matching
            lead_payload["old_linkedin_url"] = f"apollo_id:{pid}"
            
            raw_leads_to_save.append(lead_payload)

            # 3. Format for Real-time UI Broadcast
            enriched_for_broadcast.append({
                **lead_payload,
                "comment": f"{enriched.get('headline', 'N/A')} at {enriched.get('company_name', 'N/A')}" if enriched.get('company_name') else enriched.get('headline', 'N/A'),
                "industry": enriched.get("industry"),
                "employee_count": enriched.get("employee_count"),
                "revenue_estimate": enriched.get("revenue_estimate"),
                "location": f"{enriched.get('city', '')}, {enriched.get('country', '')}".strip(", "),
                "photo_url": enriched.get("photo_url"),
                "is_enriched": True
            })

        except Exception as err:
            logger.error(f"Error processing enriched lead {pid}: {err}")
            continue

    if raw_leads_to_save:
        await batch_upsert_identified_profiles(db, raw_leads_to_save)
        await db.commit()
        
        # BROADCAST to frontend via SSE
        logger.info(f"Broadcasting enrichment updates for {len(enriched_for_broadcast)} leads")
        await event_manager.broadcast({
            "type": "classification_update", 
            "leads": enriched_for_broadcast
        })
        
        # Trigger classification if user_id present
        if user_id:
            try:
                from services.classification_service import run_classification_and_update
                await run_classification_and_update(raw_leads_to_save, user_id=str(user_id))
            except Exception as e:
                logger.error(f"Failed to trigger follow-up classification: {e}")

    return enriched_for_broadcast

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def find_leads_apollo(input_data: LeadDiscoveryInput, api_key: str = None, db: AsyncSession = None, user_id: str = None) -> List[dict]:
    """
    Search for leads using Apollo.io API.
    """
    import os
    final_api_key = api_key or os.getenv("APOLLO_API_KEY")
    if not final_api_key:
        raise Exception("Apollo API Key is required. Please set it in Organization Settings.")

    search_url = "https://api.apollo.io/api/v1/mixed_people/api_search"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": final_api_key
    }
    
    search_payload = {
        "page": input_data.page or 1,
        "per_page": 100
    }
    
    # helper to add normalized lists only if they exist
    def add_filter(key, val):
        norm = normalize_to_list(val)
        if norm:
            search_payload[key] = norm

    add_filter("person_titles", input_data.person_titles or input_data.job_title)
    add_filter("person_locations", input_data.person_locations or input_data.location)
    add_filter("organization_industries", input_data.industry)
    add_filter("q_organization_domains_list", input_data.organization_domains)
    add_filter("organization_ids", input_data.organization_ids)
    add_filter("contact_email_status", input_data.contact_email_status)
    add_filter("organization_num_employees_ranges", input_data.organization_num_employees_ranges)
    add_filter("currently_using_any_of_technology_uids", input_data.currently_using_any_of_technology_uids)
    add_filter("currently_using_all_of_technology_uids", input_data.currently_using_all_of_technology_uids)
    add_filter("currently_not_using_any_of_technology_uids", input_data.currently_not_using_any_of_technology_uids)
    add_filter("q_organization_job_titles", input_data.q_organization_job_titles)
    add_filter("organization_job_locations", input_data.organization_job_locations)
    
    if input_data.person_seniorities:
        add_filter("person_seniorities", input_data.person_seniorities)

    # q_keywords: We use this only for explicit search keywords now.
    # Industry is handled by organization_industries above.
    # We sanitize special characters (like &) by replacing them with spaces.
    import re
    def sanitize_for_apollo(text: str) -> str:
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text or "")
        return " ".join(clean.split())

    explicit_kw_clean = sanitize_for_apollo(input_data.q_keywords)
    if explicit_kw_clean:
        search_payload["q_keywords"] = explicit_kw_clean

    # Add optional boolean/numeric filters only if provided
    if input_data.include_similar_titles is not None:
        search_payload["include_similar_titles"] = input_data.include_similar_titles
        
    if input_data.revenue_min is not None:
        search_payload["organization_revenue_min"] = input_data.revenue_min
    if input_data.revenue_max is not None:
        search_payload["organization_revenue_max"] = input_data.revenue_max

    if input_data.organization_num_jobs_range_min is not None or input_data.organization_num_jobs_range_max is not None:
        search_payload["organization_num_jobs_range"] = {}
        if input_data.organization_num_jobs_range_min is not None:
            search_payload["organization_num_jobs_range"]["min"] = input_data.organization_num_jobs_range_min
        if input_data.organization_num_jobs_range_max is not None:
            search_payload["organization_num_jobs_range"]["max"] = input_data.organization_num_jobs_range_max

    if input_data.organization_job_posted_at_range_min or input_data.organization_job_posted_at_range_max:
        search_payload["organization_job_posted_at_range"] = {}
        if input_data.organization_job_posted_at_range_min:
            search_payload["organization_job_posted_at_range"]["min"] = input_data.organization_job_posted_at_range_min
        if input_data.organization_job_posted_at_range_max:
            search_payload["organization_job_posted_at_range"]["max"] = input_data.organization_job_posted_at_range_max

    print(f"DEBUG: Apollo Search Payload: {json.dumps(search_payload, indent=2)}")
    try:
        response = requests.post(search_url, headers=headers, json=search_payload)
        
        if response.status_code == 422 or response.status_code == 403:
            error_msg = response.text.lower()
            if "paid plan" in error_msg or "upgrade" in error_msg:
                raise Exception("Apollo API requires a paid plan. Please upgrade or use Tavily.")
            else:
                raise Exception(f"Apollo API Error: {response.text}")
                
        response.raise_for_status()
        data = response.json()
        
        people_found = data.get("people", [])
        total_found = data.get("total_entries", 0)
        logger.info(f"Apollo Search returned {len(people_found)} results (Total: {total_found})")
        
        if not people_found:
            return []

        # Step 1.5: Metadata-Based Deduplication
        # We identify existing leads by checking if their apollo_id exists in profile_metadata
        if db:
            try:
                apollo_ids = [p.get("id") for p in people_found if p.get("id")]
                if apollo_ids:
                    from sqlalchemy import or_
                    
                    # We check for:
                    # 1. Matching placeholder linkedin_url (apollo_id:xyz)
                    # 2. Matching apollo_id inside the profile_metadata string
                    placeholder_urls = [f"apollo_id:{aid}" for aid in apollo_ids]
                    
                    # profile_metadata is currently a Text column (stringified JSON)
                    # We use LIKE for a robust match on the specific "apollo_id": "xyz" pattern
                    # Using escaped double-quotes to match the JSON serialization precisely
                    meta_filters = [IdentifiedProfile.profile_metadata.like(f'%\"apollo_id\": \"{aid}\"%') for aid in apollo_ids]
                    
                    query = select(IdentifiedProfile.profile_metadata, IdentifiedProfile.linkedin_url).where(
                        or_(
                            IdentifiedProfile.linkedin_url.in_(placeholder_urls),
                            *meta_filters
                        )
                    )
                    
                    res = await db.execute(query)
                    existing_data = res.all()
                    
                    existing_ids = set()
                    for em, lurl in existing_data:
                        # Case 1: Matching via placeholder URL
                        if lurl and lurl.startswith("apollo_id:"):
                            existing_ids.add(lurl.split(":")[-1])
                        
                        # Case 2: Matching via metadata
                        if em:
                            try:
                                m = json.loads(em) if isinstance(em, str) else em
                                if isinstance(m, dict) and m.get("apollo_id"):
                                    existing_ids.add(m["apollo_id"])
                            except:
                                continue
                    
                    if existing_ids:
                        original_count = len(people_found)
                        people_found = [p for p in people_found if p.get("id") not in existing_ids]
                        filtered_count = original_count - len(people_found)
                        if filtered_count > 0:
                            logger.info(f"Filtered {filtered_count} existing leads from discovery results.")
            except Exception as e:
                logger.error(f"Error during Apollo deduplication check: {e}")

        # Step 2: Immediate Return
        # We no longer wait for enrichment here. 
        # The enrichment is handled as a background task by the caller.
        return [map_apollo_person(p, is_enriched=False) for p in people_found]

    except Exception as e:
        logger.error(f"Error during Apollo search: {e}")
        # Re-raise user-friendly exceptions so they bubble up to the UI
        if "requires a paid plan" in str(e):
            raise e
        return []

if __name__ == "__main__":
    # Test block
    test_input = LeadDiscoveryInput(
        industry="Artificial Intelligence",
        job_title="Founder",
        location="San Francisco",
        provider="tavily"
    )
    urls = find_leads_tavily(test_input)
    logger.info("Found URLs (Tavily):", urls)
