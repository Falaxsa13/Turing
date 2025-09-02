from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime


class UserSettings(BaseModel):
    """User settings model for Firebase Firestore"""

    user_email: EmailStr = Field(description="User email")
    created_at: datetime = Field(default_factory=datetime.now, description="Created at")
    updated_at: datetime = Field(default_factory=datetime.now, description="Updated at")
    canvas_base_url: Optional[str] = Field(default=None, description="Canvas base URL")
    canvas_pat: Optional[str] = Field(default=None, description="Canvas personal access token")
    last_canvas_sync: Optional[datetime] = Field(default=None, description="Last canvas sync")
    notion_token: Optional[str] = Field(default=None, description="Notion token")
    notion_parent_page_id: Optional[str] = Field(default=None, description="Notion parent page ID")
    last_notion_sync: Optional[datetime] = Field(default=None, description="Last notion sync")
    last_assignment_sync: Optional[datetime] = Field(default=None, description="Last assignment sync")
    google_credentials: Optional[Dict[str, Any]] = Field(default=None, description="Google credentials")
    google_calendar_id: Optional[str] = Field(default=None, description="Google calendar ID")
    last_google_sync: Optional[datetime] = Field(default=None, description="Last google sync")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserPreferences(BaseModel):
    """User preferences model for Firebase Firestore"""

    user_email: EmailStr = Field(description="User email")
    dashboard_layout: str = Field(default="grid", description="Dashboard layout")
    default_view: str = Field(default="assignments", description="Default view")
    notifications_enabled: bool = Field(default=True, description="Notifications enabled")
    theme: str = Field(default="light", description="Theme")
    sync_frequency: str = Field(default="manual", description="Sync frequency")

    show_completed_assignments: bool = Field(default=True, description="Show completed assignments")
    show_past_assignments: bool = Field(default=True, description="Show past assignments")
    assignments_per_page: int = Field(default=50, description="Assignments per page")


class AuditLog(BaseModel):
    """Audit log model for Firebase Firestore"""

    id: Optional[str] = Field(default=None, description="ID")
    user_email: EmailStr = Field(description="User email")
    action: str = Field(description="Action (create, update, delete, sync)")
    resource_type: str = Field(description="Resource type (course, assignment, user_settings)")
    target_id: str = Field(description="Target ID (ID of the affected resource)")
    old_value: Optional[Dict[str, Any]] = Field(default=None, description="Old value")
    new_value: Optional[Dict[str, Any]] = Field(default=None, description="New value")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadata")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserSession(BaseModel):
    """User session model for authentication"""

    user_email: EmailStr = Field(description="User email")
    user_id: str = Field(description="Firebase user ID")
    display_name: Optional[str] = Field(default=None, description="Display name")
    photo_url: Optional[str] = Field(default=None, description="Photo URL")
    access_token: str = Field(description="Access token")
    refresh_token: Optional[str] = Field(default=None, description="Refresh token")
    expires_at: datetime = Field(description="Expires at")
    created_at: datetime = Field(default_factory=datetime.now, description="Created at")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
