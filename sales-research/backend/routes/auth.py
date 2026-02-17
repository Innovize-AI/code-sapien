from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from services.auth_service import auth_service
from db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Profile

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = auth_service.sign_in(request.email, request.password)
    if not res or not res.session:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Fetch role from database
    user_id = res.user.id
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalars().first()
    
    role = profile.role if profile else "user"
    
    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "user": {
            "id": res.user.id,
            "email": res.user.email,
            "role": role,
            "full_name": profile.full_name if profile else None
        }
    }
