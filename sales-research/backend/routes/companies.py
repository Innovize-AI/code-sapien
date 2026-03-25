from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from db import get_db
from db.models import Company
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/companies", tags=["Companies"])

class PeopleSchema(BaseModel):
    id: UUID
    name: Optional[str]
    headline: Optional[str]
    linkedin_url: str
    email: Optional[str]
    is_fit: bool
    is_decision_maker: bool
    is_buy_signal: bool = False
    is_strategic_seller: bool = False
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    post_topic_depth: Optional[str] = None
    fit_reasoning: Optional[str]
    interaction_history: Optional[str] = None
    last_interaction_at: Optional[datetime] = None
    latest_report_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class CompanySchema(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    name: str
    domain: Optional[str]
    linkedin_url: Optional[str]
    website: Optional[str]
    description: Optional[str]
    industries: Optional[str]
    employee_count: Optional[int]
    revenue: Optional[str]
    market_cap: Optional[str]
    total_funding: Optional[str]
    headquarters: Optional[str]
    follower_count: Optional[int]
    employee_count_range: Optional[str]
    news: Optional[str]
    hiring: Optional[str]
    technologies: Optional[str]
    technology_names: Optional[str]
    funding_events: Optional[str]
    latest_funding_stage: Optional[str]
    latest_funding_date: Optional[str]
    headcount_growth: Optional[str] = None
    email: Optional[str] = None
    apollo_id: Optional[str]
    people: List[PeopleSchema] = []

    class Config:
        from_attributes = True

@router.get("/{company_id}", response_model=CompanySchema)
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Fetch full details for a specific company by its UUID, including identified people.
    """
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    # Fetch identified profiles for this company, joining with ResearchReport to get latest_report_id
    from db.models import IdentifiedProfile, ResearchReport
    from sqlalchemy import func
    
    profiles_res = await db.execute(
        select(IdentifiedProfile).where(IdentifiedProfile.company_id == company_id)
    )
    profiles = profiles_res.scalars().all()
    
    if profiles:
        # Get latest report for each profile using the normalized_linkedin_url
        urls = [p.normalized_linkedin_url for p in profiles if p.normalized_linkedin_url]
        if urls:
            reports_res = await db.execute(
                select(
                    ResearchReport.normalized_linkedin_url,
                    ResearchReport.id
                ).where(
                    ResearchReport.normalized_linkedin_url.in_(urls)
                ).order_by(
                    ResearchReport.normalized_linkedin_url,
                    ResearchReport.created_at.desc()
                )
            )
            # Create a mapping of url -> latest_report_id
            report_mapping = {}
            for url, r_id in reports_res:
                if url not in report_mapping:
                    report_mapping[url] = r_id
            
            for p in profiles:
                p.latest_report_id = report_mapping.get(p.normalized_linkedin_url)
                
                # Unpack AI signals from metadata if not already on the object
                if p.profile_metadata:
                    import json
                    try:
                        meta = json.loads(p.profile_metadata) if isinstance(p.profile_metadata, str) else p.profile_metadata
                        if isinstance(meta, dict):
                            p.is_buy_signal = meta.get("is_buy_signal", False)
                            p.is_strategic_seller = meta.get("is_strategic_seller", False)
                            # Intent/Sentiment fallback
                            if not p.intent: p.intent = meta.get("intent")
                            if not p.sentiment: p.sentiment = meta.get("sentiment")
                    except Exception as e:
                        print(f"Error unpacking metadata for {p.id}: {e}")
    
    # Attach to Pydantic model
    setattr(company, "people", profiles)
    
    return company
