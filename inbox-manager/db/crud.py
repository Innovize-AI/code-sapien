from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Email, Profile
from db.schemas import EmailCreate
from db.database import SessionLocal, engine, Base
from sqlalchemy.future import select

async def create_email(email: EmailCreate, db:AsyncSession):

    print(type(db))  # Should print <class 'sqlalchemy.ext.asyncio.session.AsyncSession'>

    db_email = Email(
        
        subject=email.subject,
        category=email.category,
        received_at=email.received_at,
        user_id=email.user_id,
        sender_email = email.sender_email,
        intent= email.intent,
        pii_detected = email.pii_detected,
        preprocesses_email = email.preprocessed_email,
        requires_response = email.requires_response,
        escalated_to_human= email.escalated_to_human,
        category_confidence_score= email.category_confidence_score,
        email_response_draft= email.email_response_draft
    )
    db.add(db_email)
    await db.commit()
    await db.refresh(db_email)
    return db_email


async def get_emails_with_user(email_id: str, db:AsyncSession):

    query =text( """
        SELECT *
        FROM emails e
        JOIN profiles u ON e.user_id = u.id
        WHERE u.email = :email_id;
    """)
    result = await db.execute(query, {"email_id": email_id})
    return result.fetchall() 

async def get_user_id_with_email(email_id:str, db:AsyncSession):
    # query= text("""
    #     SELECT id from profiles where email= :email_id
    #             """)
    query = text("SELECT id FROM profiles WHERE email = :email_id")
    try:
        result = await db.execute(query, {"email_id": email_id})
        rows = result.fetchone()
        print("rows" , rows)
        return rows
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

    # result= await db.execute(query, {"email_id": email_id})
    # return result.fetchone()
        