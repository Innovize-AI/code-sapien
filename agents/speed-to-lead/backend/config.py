from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google (Gemini generation + text-embedding-004 for Pinecone)
    google_api_key: str

    # Pinecone
    pinecone_api_key: str

    @property
    def pinecone_index_name(self) -> str:
        return "speed-to-lead" if self.is_production else "speed-to-lead-staging"

    # Supabase — root .env uses SUPABASE_SERVICE_ROLE_KEY
    supabase_url: str
    supabase_service_key: str = Field(alias="supabase_service_role_key")
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""

    # Database — root .env uses postgresql://, SQLAlchemy needs postgresql+asyncpg://
    database_url: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_driver(cls, v: str) -> str:
        if not v:
            return v
        for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://", "postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    # Meta WhatsApp Cloud API (add to root .env when ready)
    meta_access_token: str = ""
    meta_phone_number_id: str = ""
    meta_webhook_verify_token: str = ""
    meta_app_secret: str = ""

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: str = "false"
    langchain_project: str = "speed-to-lead-re-id"

    # Alerts
    fallback_alert_email: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = Field(default="", alias="gmail_user")
    smtp_password: str = Field(default="", alias="gmail_password")

    # Booking link — injected into no-show recovery templates
    booking_link: str = "[Booking Link]"

    # Visit reminders — location details injected into template variables
    maps_link_interior: str = "[Experience Center Location]"
    maps_link_real_estate: str = "[Site Location Pin]"

    # App
    environment: str = "staging"
    log_level: str = "INFO"
    test_forward_number: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
