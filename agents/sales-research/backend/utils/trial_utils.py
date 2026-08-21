import logging
import os
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from db.models import IdentifiedProfile, ResearchReport

logger = logging.getLogger(__name__)

# Constants for default limits if not specified in environment
DEFAULT_IDENTIFIED_LIMIT = 100
DEFAULT_CLASSIFICATION_LIMIT = 50
DEFAULT_RESEARCH_LIMIT = 5

def get_trial_limits():
    """Helper to get all trial limits from environment."""
    return {
        "identified_limit": int(os.getenv("TRIAL_IDENTIFIED_LIMIT", str(DEFAULT_IDENTIFIED_LIMIT))),
        "classification_limit": int(os.getenv("TRIAL_CLASSIFICATION_LIMIT", str(DEFAULT_CLASSIFICATION_LIMIT))),
        "research_limit": int(os.getenv("TRIAL_RESEARCH_LIMIT", str(DEFAULT_RESEARCH_LIMIT))),
    }

async def check_trial_lead_limit(db: AsyncSession, org_id: UUID | str | None, user_id: UUID | str | None = None) -> bool:
    """
    Checks if a trial organization has reached its lead identification limit.
    Returns True if the limit is reached, False otherwise.
    """
    is_trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    if not is_trial_mode:
        return False
        
    limits = get_trial_limits()
    trial_limit = limits["identified_limit"]
    
    count_query = select(func.count(IdentifiedProfile.id))
    
    if org_id:
        o_id = UUID(str(org_id)) if isinstance(org_id, str) else org_id
        count_query = count_query.where(IdentifiedProfile.organization_id == o_id)
    elif user_id:
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        count_query = count_query.where(IdentifiedProfile.created_by_id == u_id)
    else:
        return False
        
    try:
        count_res = await db.execute(count_query)
        current_count = count_res.scalar() or 0
        
        if current_count >= trial_limit:
            logger.warning(f"Trial Mode Lead Limit Reached: {current_count}/{trial_limit} for {org_id or user_id}")
            return True
    except Exception as e:
        logger.error(f"Error checking trial lead limit: {e}")
        return False
        
    return False

async def check_trial_classification_limit(db: AsyncSession, org_id: UUID | str | None, user_id: UUID | str | None = None) -> bool:
    """
    Checks if a trial organization has reached its classification limit.
    A lead is considered classified if it has 'fit_reasoning' OR is marked as 'is_fit' OR has 'intent'.
    """
    is_trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    if not is_trial_mode:
        return False
        
    limits = get_trial_limits()
    trial_limit = limits["classification_limit"]
    
    # Unified classification criteria: fit_reasoning, is_fit, or intent
    count_query = select(func.count(IdentifiedProfile.id)).where(
        or_(
            IdentifiedProfile.fit_reasoning.isnot(None),
            IdentifiedProfile.is_fit == True,
            IdentifiedProfile.intent.isnot(None)
        )
    )
    
    if org_id:
        o_id = UUID(str(org_id)) if isinstance(org_id, str) else org_id
        count_query = count_query.where(IdentifiedProfile.organization_id == o_id)
    elif user_id:
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        count_query = count_query.where(IdentifiedProfile.created_by_id == u_id)
    else:
        return False
        
    try:
        count_res = await db.execute(count_query)
        current_count = count_res.scalar() or 0
        
        if current_count >= trial_limit:
            logger.warning(f"Trial Mode Classification Limit Reached: {current_count}/{trial_limit} for {org_id or user_id}")
            return True
    except Exception as e:
        logger.error(f"Error checking trial classification limit: {e}")
        return False
        
    return False

async def check_trial_research_limit(db: AsyncSession, org_id: UUID | str | None, user_id: UUID | str | None = None) -> bool:
    """
    Checks if a trial organization has reached its deep research report limit.
    """
    is_trial_mode = os.getenv("TRIAL_MODE", "false").lower() == "true"
    if not is_trial_mode:
        return False
        
    limits = get_trial_limits()
    trial_limit = limits["research_limit"]
    
    count_query = select(func.count(ResearchReport.id))
    
    if org_id:
        o_id = UUID(str(org_id)) if isinstance(org_id, str) else org_id
        count_query = count_query.where(ResearchReport.organization_id == o_id)
    elif user_id:
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        count_query = count_query.where(ResearchReport.created_by_id == u_id)
    else:
        return False
        
    try:
        count_res = await db.execute(count_query)
        current_count = count_res.scalar() or 0
        
        if current_count >= trial_limit:
            logger.warning(f"Trial Mode Research Limit Reached: {current_count}/{trial_limit} for {org_id or user_id}")
            return True
    except Exception as e:
        logger.error(f"Error checking trial research limit: {e}")
        return False
        
    return False
