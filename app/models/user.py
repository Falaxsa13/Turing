"""
User model for authentication and user management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .user_settings import UserSettings, UserPreferences


class User(BaseModel):
    """User model for authenticated users."""

    user_email: str = Field(description="User's email address")
    user_id: str = Field(description="User's unique identifier")
    display_name: Optional[str] = Field(default=None, description="User's display name")
    photo_url: Optional[str] = Field(default=None, description="User's profile photo URL")
    created_at: Optional[datetime] = Field(default=None, description="When the user was created")
    updated_at: Optional[datetime] = Field(default=None, description="When the user was last updated")

    class Config:
        from_attributes = True


class UserProfile(User):
    """Extended user model with additional profile information."""

    settings: Optional[UserSettings] = Field(default=None, description="User settings and preferences")
    preferences: Optional[UserPreferences] = Field(default=None, description="User preferences")
    setup_status: Optional[dict] = Field(default=None, description="User setup completion status")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    is_active: bool = Field(default=True, description="Whether the user account is active")


class AuthenticatedUser(User):
    """User model specifically for authenticated requests."""

    token_expires_at: Optional[datetime] = Field(default=None, description="When the current token expires")
    auth_method: Optional[str] = Field(default=None, description="Authentication method used")

    def is_token_expired(self) -> bool:
        """Check if the current token is expired."""
        if not self.token_expires_at:
            return True
        return datetime.utcnow() > self.token_expires_at
