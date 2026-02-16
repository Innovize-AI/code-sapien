from .database import get_db, Base, SessionLocal, engine
from .crud import save_report, get_history, get_report, get_report_by_email_or_linkedin, save_lead_submission

def get_db_session():
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def session():
        async with SessionLocal() as s:
            yield s
    return session()
from .crud import (
    save_report, get_history, get_report, get_report_by_email_or_linkedin, 
    save_competitor_analysis, get_competitor_analyses,
    create_competitor, get_competitors, delete_competitor,
    upsert_identified_profile, get_identified_profiles, batch_upsert_identified_profiles, count_identified_profiles,
    _report_to_dict, _safe_deserialize
)
