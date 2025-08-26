from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App settings
    app_env: str = "dev"

    # Database settings
    database_url: str = "postgresql://postgres:postgres@localhost:5432/canvas_sync"

    # Canvas settings (optional for testing)
    canvas_base_url: str = "https://example.instructure.com"
    canvas_pat: str = "dummy_token_for_testing"

    # Notion settings (optional for testing)
    notion_token: str = "dummy_token_for_testing"
    notion_parent_page_id: str = "dummy_parent_page_id"

    # Google settings (optional for testing)
    google_client_id: str = "dummy_client_id"
    google_client_secret: str = "dummy_client_secret"
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Polling settings
    poll_interval_minutes: int = 15

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
