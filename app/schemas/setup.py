from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


# Request Models
class InitSetupRequest(BaseModel):
    user_email: EmailStr
    canvas_base_url: str
    notion_token: str
    notion_parent_page_id: str


class CanvasPATRequest(BaseModel):
    canvas_pat: str


class CanvasTestRequest(BaseModel):
    canvas_base_url: str
    canvas_pat: str


class SyncStartRequest(BaseModel):
    user_email: EmailStr


# Response Models
class SetupResponse(BaseModel):
    message: str
    user_email: str


class SetupStatusResponse(BaseModel):
    user_email: str
    has_canvas: bool
    has_notion: bool
    has_google: bool
    calendar_id: Optional[str] = None
    last_canvas_sync: Optional[datetime] = None
    last_notion_sync: Optional[datetime] = None
    last_google_sync: Optional[datetime] = None
    last_assignment_sync: Optional[datetime] = None
    setup_complete: bool
    next_steps: list[str]


class CanvasTestResponse(BaseModel):
    success: bool
    message: str
    user_info: Optional[Dict[str, Any]] = None


class ProfessorDetectionResponse(BaseModel):
    success: bool
    course_id: int
    course_name: str
    professors_via_sections: Dict[str, Any]
    instructors_via_enrollments: Dict[str, Any]
    teachers_from_course: Dict[str, Any]
    recommendation: str
