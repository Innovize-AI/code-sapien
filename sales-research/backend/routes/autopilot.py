from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from db.database import get_db
from db.models import Profile
from db.schemas import AutopilotRule, AutopilotRuleCreate, Competitor, CompetitorCreate
from db import crud
from dependencies import get_current_user

autopilot_router = APIRouter(tags=['Autopilot'])

@autopilot_router.get("/autopilot/rules", response_model=List[AutopilotRule])
async def get_autopilot_rules(
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Get all active autopilot rules for the organization.
    """
    return await crud.get_autopilot_rules(
        db, 
        rule_type=type,
        org_id=current_user.organization_id,
        user_id=str(current_user.id)
    )

@autopilot_router.post("/autopilot/rules", response_model=AutopilotRule)
async def create_autopilot_rule(
    rule_data: AutopilotRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    import os
    is_trial = os.getenv("TRIAL_MODE", "false").lower() == "true"
    if is_trial and rule_data.type == 'apollo_config':
        raise HTTPException(
            status_code=400, 
            detail="Apollo Discovery is not available in Trial Mode."
        )

    if rule_data.type == 'keyword':
        existing_rules = await crud.get_autopilot_rules(
            db, 
            rule_type='keyword',
            org_id=current_user.organization_id,
            user_id=str(current_user.id)
        )
        if len(existing_rules) >= 5:
            raise HTTPException(
                status_code=400, 
                detail="Maximum limit of 5 keywords reached. Please delete an existing keyword to add a new one."
            )
            
    rule_dict = rule_data.model_dump()
    return await crud.create_autopilot_rule(
        db, 
        rule_dict, 
        user_id=str(current_user.id),
        org_id=current_user.organization_id
    )

@autopilot_router.delete("/autopilot/rules/{rule_id}")
async def delete_autopilot_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """
    Deactivate an autopilot rule. Creator or Admin only.
    """
    from db.models import AutopilotRule
    from sqlalchemy import select
    
    # Fetch rule to check owner
    result = await db.execute(select(AutopilotRule).where(AutopilotRule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    is_owner = rule.created_by_id == current_user.id
    is_same_org = current_user.organization_id and rule.organization_id == current_user.organization_id
    
    if not (is_owner or (is_same_org and current_user.role == "admin") or current_user.role == "super_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this rule")

    success = await crud.delete_autopilot_rule(db, rule_id)
    return {"status": "success"}

# Re-expose competitor routes with attribution
@autopilot_router.get("/autopilot/competitors", response_model=List[Competitor])
async def get_autopilot_competitors(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    return await crud.get_competitors(
        db,
        org_id=current_user.organization_id,
        user_id=str(current_user.id)
    )

@autopilot_router.post("/autopilot/competitors", response_model=Competitor)
async def create_autopilot_competitor(
    comp_data: CompetitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    existing_competitors = await crud.get_competitors(
        db,
        org_id=current_user.organization_id,
        user_id=str(current_user.id)
    )
    if len(existing_competitors) >= 3:
        raise HTTPException(
            status_code=400, 
            detail="Maximum limit of 3 competitors reached. Please delete an existing competitor to add a new one."
        )
        
    comp_dict = comp_data.model_dump()
    return await crud.create_competitor(
        db, 
        comp_dict, 
        user_id=str(current_user.id),
        org_id=current_user.organization_id
    )

@autopilot_router.delete("/autopilot/competitors/{comp_id}")
async def delete_autopilot_competitor(
    comp_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    from db.models import Competitor
    from sqlalchemy import select
    
    # Fetch to check owner
    result = await db.execute(select(Competitor).where(Competitor.id == comp_id))
    comp = result.scalar_one_or_none()
    
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found")
        
    is_owner = comp.created_by_id == current_user.id
    is_same_org = current_user.organization_id and comp.organization_id == current_user.organization_id

    if not (is_owner or (is_same_org and current_user.role == "admin") or current_user.role == "super_admin"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this competitor")

    success = await crud.delete_competitor(db, comp_id)
    return {"status": "success"}
