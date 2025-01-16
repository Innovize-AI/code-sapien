from fastapi import APIRouter
from db.schemas import EmailCreate
from db.crud import create_email, get_user_id_with_email, get_emails_with_user
from db.database import SessionLocal, engine, Base
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import CategoryEnum, IntentEnum
db_router = APIRouter(prefix='/db-router', tags=['DB Manager'],responses={404: {"description": "Not found"}},)

# Dependency for database session

async def get_db():
    async with SessionLocal() as session:
        yield session

@db_router.post("/create_email_record")
@db_router.post("/create_email_record/")
async def create_email_record(emailcreate: EmailCreate, db: AsyncSession = Depends(get_db)):

    db_email = await create_email(emailcreate,db)

    return db_email

@db_router.get("/user/")
@db_router.get("/user")
async def get_user_with_email(email_id:str,db: AsyncSession = Depends(get_db)):

    print("email", email_id)
    user_id= await get_user_id_with_email(email_id,db)
    print("user_id", user_id[0])
    return user_id[0]

@db_router.get("/emails_of_user")
@db_router.get("/emails_of_user/")
async def get_emails_of_user(email_id, db: AsyncSession=Depends(get_db)):

    emails= await get_emails_with_user(email_id, db)
    print(emails)
    emails_json= convert_to_json(emails)
    return emails_json


def convert_to_json(data):
    json_array = []
    for item in data:
        json_array.append(EmailCreate(
            subject=item[2],  # Add subject if present in the data
            user_id=str(item[1]),
            sender_email=item[3],
            category=CategoryEnum[item[6]],
            intent=IntentEnum[item[7]],
            pii_detected=item[8],
            preprocessed_email=item[4],
            requires_response=item[9],
            received_at=item[5],
            escalated_to_human=item[10],
            category_confidence_score=item[11],
            email_response_draft=item[12]
        ).dict())
    return json_array