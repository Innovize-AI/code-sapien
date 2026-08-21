from dotenv import load_dotenv
import os
import logging
import jwt as pyjwt
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)
from supabase import create_client, Client
load_dotenv()


@dataclass
class _MockUser:
    """Minimal user object that mimics the Supabase user structure."""
    id: str
    email: str
    user_metadata: dict


@dataclass
class _MockUserResponse:
    user: _MockUser


class AuthService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.database_url = os.getenv("DATABASE_URL")
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET")

        # Robust URL resolution
        if self.url and (
            "pooler.supabase.com" in self.url or not self.url.startswith("http")
        ):
            if self.database_url and "postgres." in self.database_url:
                try:
                    part1 = self.database_url.split("postgres.")[1]
                    project_ref = part1.split(":")[0]
                    self.url = f"https://{project_ref}.supabase.co"
                except:
                    pass

        self.client: Client = None
        if self.url and self.anon_key:
            try:
                self.client = create_client(self.url, self.anon_key)
            except Exception as e:
                logger.info(f"Failed to create Supabase client: {e}")

    def sign_in(self, email, password):
        try:
            return self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as e:
            logger.info(f"Sign in failed: {e}")
            return None

    def get_user(self, token: str) -> Optional[_MockUserResponse]:
        """
        Verify and decode a Supabase JWT locally without a network call.
        Falls back to the Supabase API only if local verification fails
        (e.g. missing JWT secret or unexpected token format).
        """
        if self.jwt_secret:
            try:
                # Supabase access tokens are short-lived (typically 1 hour). To prevent automatic logout
                # on inactivity and effectively increase the session lifetime indefinitely, we bypass
                # the expiration check ('verify_exp': False). The signature and integrity are still
                # fully verified against the local Supabase JWT secret.
                payload = pyjwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False, "verify_exp": False},  # Bypass expiration check
                )
                user_id = payload.get("sub")
                email = payload.get("email", "")
                user_metadata = payload.get("user_metadata", {})

                if user_id:
                    return _MockUserResponse(
                        user=_MockUser(
                            id=user_id,
                            email=email,
                            user_metadata=user_metadata,
                        )
                    )
            except pyjwt.ExpiredSignatureError:
                logger.debug("JWT expired")
                return None
            except pyjwt.InvalidTokenError as e:
                logger.debug(f"JWT invalid, falling back to Supabase API: {e}")

        # Fallback: hit Supabase API (slow path — only reached if jwt_secret missing)
        try:
            return self.client.auth.get_user(token)
        except Exception as e:
            logger.warning(f"Supabase get_user fallback failed: {e}")
            return None


auth_service = AuthService()
