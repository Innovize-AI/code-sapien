from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from sqlalchemy import UUID
from db.models import CategoryEnum
from db.models import IntentEnum

class EmailCreate(BaseModel):
    subject: Optional[str] = None
    user_id:str
    sender_email: str
    category: CategoryEnum
    intent: Optional[IntentEnum]
    pii_detected: Optional[bool]
    preprocessed_email: str
    requires_response: Optional[bool]
    received_at: Optional[datetime]
    escalated_to_human:Optional[bool]
    category_confidence_score:float
    email_response_draft: str

    class Config:
        orm_mode = True
