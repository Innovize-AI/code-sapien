
from fastapi import Depends, HTTPException
from services.auth_service import auth_service
from db.database import get_db
from db.models import Profile
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: AsyncSession = Depends(get_db)):
    token = credentials.credentials
    user_response = auth_service.get_user(token)
    
    if not user_response or not user_response.user:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    user_id = user_response.user.id
    
    # Check Profile
    from sqlalchemy import select
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalars().first()
    if not profile:
        # Create default user profile if missing
        try:
            # Try to get name from metadata
            user_meta = user_response.user.user_metadata or {}
            full_name = user_meta.get("full_name") or user_meta.get("name")
            
            # Fallback to email prefix
            if not full_name:
                full_name = user_response.user.email.split("@")[0].title()

            profile = Profile(
                id=user_id, 
                email=user_response.user.email, 
                role="user",
                full_name=full_name
            )
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        except Exception as e:
            print(f"Error creating profile: {e}")
            raise HTTPException(status_code=500, detail="Failed to create user profile")
        
    return profile

def require_admin(user: Profile = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
