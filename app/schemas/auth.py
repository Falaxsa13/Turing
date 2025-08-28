"""
Authentication schemas for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class FirebaseLoginRequest(BaseModel):
    """Request model for Firebase login."""

    id_token: str = Field(description="Firebase ID token from Google OAuth")


class LoginResponse(BaseModel):
    """Response model for successful login."""

    success: bool = Field(description="Whether the login was successful")
    message: str = Field(description="Human-readable message about the login")
    user_email: str = Field(description="User's email address")
    user_id: str = Field(description="User's unique identifier")
    display_name: Optional[str] = Field(default=None, description="User's display name")
    photo_url: Optional[str] = Field(default=None, description="User's profile photo URL")
    access_token: str = Field(description="JWT access token for API calls")
    token_type: str = Field(description="Token type (usually 'bearer')")
    expires_in: int = Field(description="Token expiration time in seconds")


class LogoutRequest(BaseModel):
    """Request model for logout."""

    revoke_token: bool = Field(default=False, description="Whether to revoke the current token")


class LogoutResponse(BaseModel):
    """Response model for logout."""

    success: bool = Field(description="Whether the logout was successful")
    message: str = Field(description="Human-readable message about the logout")
    user_email: str = Field(description="Email of the user who logged out")
    logout_timestamp: str = Field(description="ISO timestamp of when logout occurred")
    note: str = Field(description="Important note about token handling")


class FirebaseKeys(BaseModel):
    apiKey: str
    authDomain: str
    projectId: str
    storageBucket: str
    messagingSenderId: str
    appId: str
    measurementId: str | None = None


class FirebaseConfigResponse(BaseModel):
    """Response model for Firebase configuration."""

    firebase: FirebaseKeys
