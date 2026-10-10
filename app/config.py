# app/config.py
# This file reads environment variables from the .env file and makes them
# available throughout the application as a single settings object.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Full database connection URL.
    # Default: SQLite file in the project root — no installation required.
    # To use PostgreSQL, override this in .env.
    database_url: str = "sqlite:///./bulk_cert.db"

    # Directory where generated PDF files will be saved
    certificates_dir: str = "generated_certificates"

    # Port to run the server on — Render sets this automatically
    port: int = 8000

    # pydantic-settings v2 configuration:
    # env_file      : read from .env file
    # env_file_encoding : use utf-8 (avoids Windows BOM issue)
    # extra='ignore' : silently ignore unknown env vars instead of erroring
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",  # utf-8-sig strips Windows BOM automatically
        extra="ignore",
        case_sensitive=False,
    )


# Create a single shared instance used across the whole app
settings = Settings()
