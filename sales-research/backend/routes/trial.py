from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from dependencies import get_current_user, require_admin
from services.trial_service import trial_service

router = APIRouter()

@router.post("/onboard")
async def onboard_trial(
    db: AsyncSession = Depends(get_db),
    user = Depends(require_admin)
):
    """
    Triggers the trial onboarding process for the current user's organization.
    This provisions a Pinecone index and updates organization settings.
    """
    if not user.organization_id:
        raise HTTPException(status_code=400, detail="User is not associated with an organization")

    success = await trial_service.onboard_trial_organization(db, str(user.organization_id), str(user.id))
    if not success:
        raise HTTPException(status_code=500, detail="Trial onboarding failed")
        
    return {
        "status": "success", 
        "message": "Trial resources provisioned and organization onboarded successfully.",
        "organization_id": str(user.organization_id)
    }

@router.get("/status")
async def get_trial_status(
    user = Depends(get_current_user)
):
    """
    Returns the trial status for the current user.
    """
    import os
    import json
    
    is_trial_instance = os.getenv("TRIAL_MODE", "false").lower() == "true"
    profile_metadata = json.loads(user.profile_metadata or "{}") if isinstance(user.profile_metadata, str) else (user.profile_metadata or {})
    
    return {
        "is_trial_instance": is_trial_instance,
        "user_is_trial": profile_metadata.get("is_trial", False),
        "role": user.role
    }
