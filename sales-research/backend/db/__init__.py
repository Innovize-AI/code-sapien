from .database import get_db, Base, SessionLocal, engine
from .crud import save_report, get_history, get_report, get_report_by_email_or_linkedin, save_lead_submission

def get_db_session():
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def session():
        async with SessionLocal() as s:
            yield s
    return session()
