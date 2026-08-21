import httpx
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

async def send_slack_notification(webhook_url: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None):
    """
    Sends a notification to a Slack webhook.
    """
    if not webhook_url:
        logger.warning("Slack webhook URL not provided. Skipping notification.")
        return False

    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
