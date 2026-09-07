import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "config" / "settings.json"

DEFAULTS = {
    "company_name": "InnovizeAI",
    "company_email": "admin@innovizeai.com",
    "confidence_threshold": 0.75,
    "amount_threshold": 500000,
    "gst_rate": 18,
    "dispatch_start_hour": 8,
    "dispatch_end_hour": 20,
    "quote_validity_days": 30,
    "payment_terms": "50% advance, 50% before dispatch",
    "reviewer_email": "admin@innovizeai.com",
    "slack_review_channel": "#rfq-review",
    "auto_dispatch_enabled": True,
}


def _load() -> dict:
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text())
            return {**DEFAULTS, **data}
    except Exception as e:
        logger.warning(f"Failed to read settings: {e}")
    return dict(DEFAULTS)


def _save(data: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    confidence_threshold: Optional[float] = None
    amount_threshold: Optional[float] = None
    gst_rate: Optional[float] = None
    dispatch_start_hour: Optional[int] = None
    dispatch_end_hour: Optional[int] = None
    quote_validity_days: Optional[int] = None
    payment_terms: Optional[str] = None
    reviewer_email: Optional[str] = None
    slack_review_channel: Optional[str] = None
    auto_dispatch_enabled: Optional[bool] = None


@router.get("/settings")
def get_settings():
    return _load()


@router.patch("/settings")
def update_settings(body: SettingsUpdate):
    current = _load()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    current.update(updates)
    _save(current)
    return current
