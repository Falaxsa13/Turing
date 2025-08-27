from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App settings
    app_env: str = "dev"

    # Firebase configuration (with defaults for testing)
    firebase_api_key: str = "dummy_api_key"
    firebase_auth_domain: str = "dummy-project.firebaseapp.com"
    firebase_project_id: str = "dummy-project-id"
    firebase_storage_bucket: str = "dummy-project.appspot.com"
    firebase_messaging_sender_id: str = "123456789"
    firebase_app_id: str = "1:123456789:web:abcdef123456789"
    firebase_measurement_id: str = "G-ABCDEFGHIJ"

    # JWT settings for authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

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
        extra = "ignore"  # Ignore extra fields from .env file


# Global settings instance
settings = Settings()
