import httpx
import logging
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

async def verify_email(email: str, api_key: str) -> str:
    """
    Verify email using Million Verifier Single API.
    Returns the 'result' field (ok, invalid, catch_all, unknown, disposable).
    """
    if not api_key:
        logger.warning("Million Verifier API key not provided.")
        return "not_verified"
    
    url = "https://api.millionverifier.com/api/v3/"
    params = {
        "api": api_key,
        "email": email
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Email verification for {email}: {data}")
            # Million Verifier returns result like 'ok', 'invalid', 'catch_all', 'unknown', 'disposable'
            result = data.get("result", "unknown")
            logger.info(f"Email verification for {email}: {result}")
            return result
    except Exception as e:
        logger.error(f"Error verifying email {email} with Million Verifier: {e}")
        return "error"
if __name__ == "__main__":
    print(os.getenv("MILLION_VERIFIER_API_KEY"))
    print(asyncio.run(verify_email("pavan.kumar@innovizeai.com", os.getenv("MILLION_VERIFIER_API_KEY"))))