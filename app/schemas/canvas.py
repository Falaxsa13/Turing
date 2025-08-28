from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CanvasTeacher(BaseModel):
    """Canvas teacher/instructor information from the official API."""

    id: int = Field(description="Teacher's Canvas user ID")
    short_name: str = Field(description="Teacher's short name (what Canvas actually returns)")
    avatar_image_url: Optional[str] = Field(default=None, description="Teacher's avatar URL")
    html_url: Optional[str] = Field(default=None, description="URL to access the teacher's profile")


class CanvasTerm(BaseModel):
    """Canvas term/semester information from the official API."""

    id: int = Field(description="Term ID")
    name: str = Field(description="Term name (e.g., 'Spring 2024')")
    start_at: Optional[str] = Field(default=None, description="Term start date (ISO format)")
    end_at: Optional[str] = Field(default=None, description="Term end date (ISO format)")


class CanvasCourse(BaseModel):
    """Canvas course information from the official API."""

    # Core course information (always present)
    id: int = Field(description="Canvas course ID")
    name: str = Field(description="Course name")
    course_code: Optional[str] = Field(default=None, description="Course code (e.g., 'CS101')")
    workflow_state: Optional[str] = Field(
        default=None, description="Course state: unpublished, available, completed, deleted"
    )

    # Dates
    created_at: Optional[str] = Field(default=None, description="When the course was created (ISO format)")
    start_at: Optional[str] = Field(default=None, description="Course start date (ISO format)")
    end_at: Optional[str] = Field(default=None, description="Course end date (ISO format)")

    # Account information
    account_id: Optional[int] = Field(default=None, description="Account associated with the course")
    root_account_id: Optional[int] = Field(default=None, description="Root account ID")
    enrollment_term_id: Optional[int] = Field(default=None, description="Enrollment term ID")

    # People and enrollment
    teachers: List[CanvasTeacher] = Field(
        default_factory=list, description="List of teachers (when include[]=teachers)"
    )
    total_students: Optional[int] = Field(
        default=None, description="Total enrolled students (when include[]=total_students)"
    )

    # Term information
    term: Optional[CanvasTerm] = Field(default=None, description="Term object (when include[]=term)")

    # Additional Canvas fields (when included)
    course_image: Optional[str] = Field(default=None, description="Course image URL (when include[]=course_image)")
    uuid: Optional[str] = Field(default=None, description="Course UUID")
    sis_course_id: Optional[str] = Field(default=None, description="SIS course ID")
    integration_id: Optional[str] = Field(default=None, description="Integration ID")

    # Course settings
    time_zone: Optional[str] = Field(default=None, description="Course timezone")
    locale: Optional[str] = Field(default=None, description="Course locale")
    default_view: Optional[str] = Field(default=None, description="Default course view")
    syllabus_body: Optional[str] = Field(default=None, description="Course syllabus HTML")

    # Grading and permissions
    grading_standard_id: Optional[int] = Field(default=None, description="Grading standard ID")
    grade_passback_setting: Optional[str] = Field(default=None, description="Grade passback setting")
    hide_final_grades: Optional[bool] = Field(default=None, description="Whether final grades are hidden")
    apply_assignment_group_weights: Optional[bool] = Field(
        default=None, description="Whether assignment weights are applied"
    )

    # Computed fields from your service (not from Canvas API)
    teacher_names: Optional[List[str]] = Field(
        default=None, description="List of teacher names (computed by your service)"
    )
    parsed_info: Optional[Dict[str, Any]] = Field(default=None, description="Parsed course information for Notion")

    class Config:
        from_attributes = True


class CanvasInspectionResponse(BaseModel):
    """Response model for Canvas course inspection."""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable message about the operation")
    courses_found: int = Field(description="Number of courses found")
    courses: List[CanvasCourse] = Field(description="List of detailed course information")
    note: str = Field(description="Additional information about the response")
