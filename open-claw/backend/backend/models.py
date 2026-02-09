from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from .database import Base

class ProviderEnum(str, enum.Enum):
    digitalocean = "digitalocean"
    aws = "aws"
    gcp = "gcp"

class InstanceStatus(str, enum.Enum):
    provisioning = "provisioning"
    active = "active"
    down = "down"
    terminated = "terminated"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True) # Supabase User ID (UUID string)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    subscriptions = relationship("Subscription", back_populates="user")
    instances = relationship("Instance", back_populates="user")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    stripe_subscription_id = Column(String)
    status = Column(String) # active, past_due, etc.
    plan_tier = Column(String) # basic, pro
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="subscriptions")

class Instance(Base):
    __tablename__ = "instances"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    provider = Column(Enum(ProviderEnum))
    provider_instance_id = Column(String) # ID from the cloud provider
    ip_address = Column(String, nullable=True)
    status = Column(Enum(InstanceStatus), default=InstanceStatus.provisioning)
    region = Column(String)
    meta = Column(JSON, nullable=True) # Provider specific data (e.g. AWS Instance ID)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="instances")
