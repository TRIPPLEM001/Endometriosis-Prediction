"""
config.py

All runtime settings, read from environment variables (or a local .env
file). Nothing secret is hardcoded: JWT_SECRET and DATABASE_URL have no
defaults, so the app refuses to start if they are missing rather than
silently running with something insecure.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_name: str = "Endometriosis Screening API"
    environment: str = "development"  # development | production

    # --- Database ---
    database_url: str  # e.g. postgresql+psycopg://user:pass@host:5432/dbname

    # --- Auth ---
    jwt_secret: str  # required; generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # --- CORS (comma-separated list of allowed frontend origins) ---
    cors_origins: str = "http://localhost:3000"

    # --- Model / pipeline ---
    artifacts_dir: Path = BASE_DIR / "ml_artifacts"
    model_version: str = "2026-10-v1"  # bump whenever models are retrained
    tier1_threshold: float = 0.5
    tier2_threshold: float = 0.5

    # While False, every result is labelled a prototype and wording is
    # softened (no "confirmed"). Flip to True only after the models have
    # been validated on real clinical data.
    model_validated: bool = False

    # --- Consent ---
    consent_version: str = "2026-10-v1"  # bump when the privacy text changes

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_strong(cls, value: str) -> str:
        # A short or placeholder secret makes tokens forgeable, so refuse to
        # start rather than run that way (this also catches the .env.example placeholder).
        if len(value) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
