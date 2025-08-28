"""
Configuration management for the Turing Project application.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional
from pathlib import Path
import os


class FirebaseSettings(BaseSettings):
    """Firebase configuration settings."""

    api_key: str = Field(default="dummy_api_key", description="Firebase API key")
    auth_domain: str = Field(default="dummy-project.firebaseapp.com", description="Firebase auth domain")
    project_id: str = Field(default="dummy-project-id", description="Firebase project ID")
    storage_bucket: str = Field(default="dummy-project.appspot.com", description="Firebase storage bucket")
    messaging_sender_id: str = Field(default="123456789", description="Firebase messaging sender ID")
    app_id: str = Field(default="1:123456789:web:abcdef123456789", description="Firebase app ID")
    measurement_id: str = Field(default="G-ABCDEFGHIJ", description="Firebase measurement ID")

    class Config:
        env_prefix = "FIREBASE_"


class JWTSettings(BaseSettings):
    """JWT configuration settings."""

    secret_key: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    expire_minutes: int = Field(default=60 * 24, description="JWT expiration time in minutes")

    class Config:
        env_prefix = "JWT_"


class CanvasSettings(BaseSettings):
    """Canvas LMS configuration settings."""

    base_url: str = Field(default="https://example.instructure.com", description="Canvas base URL")
    pat: str = Field(default="dummy_token_for_testing", description="Canvas personal access token")

    class Config:
        env_prefix = "CANVAS_"


class NotionSettings(BaseSettings):
    """Notion configuration settings."""

    token: str = Field(default="dummy_token_for_testing", description="Notion integration token")
    parent_page_id: str = Field(default="dummy_parent_page_id", description="Notion parent page ID")

    class Config:
        env_prefix = "NOTION_"


class GoogleSettings(BaseSettings):
    """Google OAuth configuration settings."""

    client_id: str = Field(default="dummy_client_id", description="Google OAuth client ID")
    client_secret: str = Field(default="dummy_client_secret", description="Google OAuth client secret")
    redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback", description="Google OAuth redirect URI"
    )

    class Config:
        env_prefix = "GOOGLE_"


class AppSettings(BaseSettings):
    """Main application settings."""

    # Environment
    app_env: str = Field(default="dev", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Polling settings
    poll_interval_minutes: int = Field(default=15, description="Polling interval in minutes")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Firebase keys path
    firebase_keys_path: str = Field(default="./firebase-keys", description="Path to Firebase keys")

    # Nested settings
    firebase: FirebaseSettings = FirebaseSettings()
    jwt: JWTSettings = JWTSettings()
    canvas: CanvasSettings = CanvasSettings()
    notion: NotionSettings = NotionSettings()
    google: GoogleSettings = GoogleSettings()

    @field_validator("firebase_keys_path")
    def validate_firebase_keys_path(cls, v):
        """Validate Firebase keys path exists."""
        if not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() in ["prod", "production"]

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() in ["dev", "development"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = AppSettings()
