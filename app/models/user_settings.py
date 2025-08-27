from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


class UserSettings(BaseModel):
    """User settings model for Firebase Firestore"""

    user_email: EmailStr

    # Canvas configuration
    canvas_base_url: Optional[str] = None
    canvas_pat: Optional[str] = None  # Personal Access Token

    # Notion configuration
    notion_token: Optional[str] = None
    notion_parent_page_id: Optional[str] = None

    # Google Calendar configuration
    google_credentials: Optional[Dict[str, Any]] = None  # JSON credentials
    google_calendar_id: Optional[str] = None

    # Sync timestamps
    last_canvas_sync: Optional[datetime] = None
    last_notion_sync: Optional[datetime] = None
    last_google_sync: Optional[datetime] = None
    last_assignment_sync: Optional[datetime] = None

    # Audit timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserPreferences(BaseModel):
    """User preferences model for Firebase Firestore"""

    user_email: EmailStr
    dashboard_layout: str = "grid"  # grid, list
    default_view: str = "assignments"  # assignments, courses, dashboard
    notifications_enabled: bool = True
    theme: str = "light"  # light, dark
    sync_frequency: str = "manual"  # manual, hourly, daily

    # UI preferences
    show_completed_assignments: bool = True
    show_past_assignments: bool = True
    assignments_per_page: int = 50


class SyncLog(BaseModel):
    """Sync log model for Firebase Firestore"""

    id: Optional[str] = None
    user_email: EmailStr
    sync_type: str  # "courses", "assignments", "canvas_test", "notion_test"
    status: str  # "success", "failed", "partial"
    items_processed: int = 0
    items_created: int = 0
    items_failed: int = 0
    items_skipped: int = 0
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class AuditLog(BaseModel):
    """Audit log model for Firebase Firestore"""

    id: Optional[str] = None
    user_email: EmailStr
    action: str  # "create", "update", "delete", "sync"
    resource_type: str  # "course", "assignment", "user_settings"
    target_id: str  # ID of the affected resource
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class UserSession(BaseModel):
    """User session model for authentication"""

    user_email: EmailStr
    user_id: str  # Firebase user ID
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    last_activity: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
