from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Google OAuth
    GOOGLE_CLIENT_ID: str  # Required - load from .env
    GOOGLE_CLIENT_SECRET: str = ""  # Optional for token validation

    # JWT Configuration
    SECRET_KEY: str  # Required - load from .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # CORS - Will be parsed from environment variable string
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Access Control - Whitelist of allowed email addresses
    # Hardcoded for quick iteration (can edit directly in Lambda console)
    ALLOWED_EMAILS: str = "zduanx@gmail.com"  # Comma-separated list (hardcoded)

    # Database Configuration
    DATABASE_URL: str  # PostgreSQL connection string (production)
    TEST_DATABASE_URL: str = ""  # PostgreSQL connection string (test/dev branch) - Optional

    class Config:
        # Prioritize .env.local for local development, fallback to .env
        env_file = ".env.local" if os.path.exists(".env.local") else ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from environment file

    def get_allowed_origins(self) -> List[str]:
        """Parse and return CORS origins as a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    def get_allowed_emails(self) -> List[str]:
        """Parse and return allowed emails as a list"""
        return [email.strip().lower() for email in self.ALLOWED_EMAILS.split(",")]


settings = Settings()  # type: ignore[call-arg]  # Pydantic loads from .env
