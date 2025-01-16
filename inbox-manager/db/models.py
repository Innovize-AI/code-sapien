from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from db.database import Base


from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum

class IntentEnum(str, Enum):
    AWARENESS= "awareness"
    INTEREST ="interest"
    CONSIDERATION= "consideration"
    DECISION="decision"
    DISENGAGED= "disengaged"

from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum

class CategoryEnum(str, Enum):
    WARM_UP = "Warm-up"
    TRANSACTIONAL = "Transactional"
    MARKETING = "Marketing"
    SALES = "Sales"
    CUSTOMER_SUPPORT = "Customer Support"
    FINANCE_ADMINISTRATIVE = "Finance/Administrative"
    LEGAL_COMPLIANCE = "Legal/Compliance"
    HR_RECRUITMENT = "HR/Recruitment Emails"
    TECHNICAL_SUPPORT = "Technical Support"
    EDUCATION_TRAINING = "Education and Training"
    SECURITY_ALERT = "Security and Alert"
    FEEDBACK_REVIEW = "Feedback and Review"
    COMMUNITY_ENGAGEMENT = "Community Engagement"
    GENERAL_NOTIFICATIONS = "General Notifications"
    PROJECT_MANAGEMENT = "Project Management"
    ENQUIRY = "Enquiry"
    LOGISTICS = "Logistics"
    INTERNAL= "Internal"

# class User(Base):
#     __tablename__ = "users"
#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     email = Column(String, nullable=False)

class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "public"}  # Use the schema if applicable

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String, unique=True, nullable=False)

class Email(Base):
    __tablename__ = "emails"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.profiles.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    sender_email = Column(String, nullable=False)
    preprocesses_email= Column(Text,nullable=False)
    received_at = Column(DateTime, default=datetime.now())
    category = Column(SQLAlchemyEnum(CategoryEnum), nullable=False)
    intent= Column(SQLAlchemyEnum(IntentEnum), nullable= True)
    pii_detected = Column(Boolean, default=False)
    requires_response = Column(Boolean, default=False)
    escalated_to_human= Column(Boolean, default= False)
    category_confidence_score= Column(Float)
    email_response_draft = Column(Text, nullable=True)  # Field to store AI response
    created_at = Column(DateTime, default=datetime.now())