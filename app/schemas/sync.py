from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone


# Response Models
class SyncCourseInfo(BaseModel):
    notion_id: str
    canvas_id: int
    name: str
    course_code: str
    term: str
    professor: str


class SyncFailedCourse(BaseModel):
    canvas_id: int
    name: str
    error: str


class CanvasSyncResponse(BaseModel):
    success: bool
    message: str
    courses_found: int
    courses_created: int
    courses_failed: int
    courses_skipped: int
    created_courses: List[SyncCourseInfo]
    failed_courses: List[SyncFailedCourse]
    note: str


class CourseInspectionInfo(BaseModel):
    canvas_id: int
    name: str
    course_code: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    teachers: List[Dict[str, Any]]
    teacher_names: List[str]
    total_students: Optional[int] = None
    term: Optional[Dict[str, Any]] = None
    parsed_info: Dict[str, Any]


class CanvasInspectionResponse(BaseModel):
    success: bool
    message: str
    courses_found: int
    courses: List[CourseInspectionInfo]
    note: str


# Assignment Sync Models
class SyncAssignmentInfo(BaseModel):
    notion_id: str
    canvas_id: int
    name: str
    type: str
    due_date: Optional[str] = None
    total_score: float
    course_title: str


class SyncFailedAssignment(BaseModel):
    canvas_id: int
    name: str
    course_title: str
    error: str


class AssignmentSyncResponse(BaseModel):
    success: bool
    message: str
    courses_processed: int
    assignments_found: int
    assignments_created: int
    assignments_failed: int
    assignments_skipped: int
    created_assignments: List[SyncAssignmentInfo]
    failed_assignments: List[SyncFailedAssignment]
    note: str


class AssignmentSyncRequest(BaseModel):
    user_email: str


# Sync Status Models - Updated to match actual data structure
class NotionCourseInfo(BaseModel):
    # Handle both field naming conventions from different sources
    notion_id: Optional[str] = None
    notion_page_id: Optional[str] = None
    canvas_id: Optional[Union[int, str]] = None
    canvas_course_id: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    course_code: Optional[str] = None
    term: Optional[str] = None
    professor: Optional[str] = None


class NotionAssignmentInfo(BaseModel):
    # Handle both field naming conventions from different sources
    notion_id: str = Field(description="Notion ID of the course")
    notion_page_id: str = Field(description="Notion page ID of the course")
    canvas_id: Optional[Union[int, str]] = Field(description="Canvas ID of the course")
    canvas_assignment_id: Optional[str] = Field(description="Canvas assignment ID of the course")
    name: Optional[str] = Field(description="Name of the course")
    title: Optional[str] = Field(description="Title of the course")


class SetupStatus(BaseModel):
    has_canvas: bool = Field(description="Whether the user has a Canvas account")
    has_notion: bool = Field(description="Whether the user has a Notion account")


class SyncHistory(BaseModel):
    last_course_sync: Optional[str] = Field(description="Last course sync timestamp")
    last_assignment_sync: Optional[str] = Field(description="Last assignment sync timestamp")


class SyncData(BaseModel):
    courses_synced: int = Field(description="Number of courses synced")
    assignments_synced: int = Field(description="Number of assignments synced")


class SyncLog(BaseModel):
    id: str = Field(description="ID of the sync log")
    user_email: str = Field(description="User email")
    sync_type: str = Field(description="Type of sync (courses or assignments)")
    status: str = Field(description="Status of the sync (success, failed, partial)")

    items_processed: int = Field(description="Number of items processed", default=0)
    items_created: int = Field(description="Number of items created", default=0)
    items_failed: int = Field(description="Number of items failed", default=0)
    items_skipped: int = Field(description="Number of items skipped", default=0)

    duration_ms: Optional[int] = Field(description="Duration of the sync in milliseconds", default=0)
    error_message: Optional[str] = Field(description="Error message if the sync failed", default="")
    metadata: Dict[str, Any] = Field(description="Metadata about the sync")
    timestamp: datetime = Field(description="Timestamp of the sync", default=datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class SyncStatusResponse(BaseModel):
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable message about the operation")
    user_email: str = Field(description="User email ")
    setup_status: SetupStatus = Field(description="User setup completion status")
    sync_history: SyncHistory = Field(description="Sync history")
    sync_data: SyncData = Field(description="Sync data")
    courses: List[NotionCourseInfo] = Field(
        description="Synced courses, most likely only contains notion_page_id, canvas_course_id, title and course_code "
    )
    assignments: List[NotionAssignmentInfo] = Field(
        description="Synced assignments, most likely only contains notion_page_id, canvas_assignment_id, title"
    )
    recent_sync_logs: List[SyncLog] = Field(description="Recent sync logs")
    note: str = Field(description="Additional information about the response")


# Specific Response Models for Individual Endpoints
class SyncedCoursesResponse(BaseModel):
    success: bool
    message: str
    courses_count: int
    courses: List[NotionCourseInfo]
    note: str


class SyncedAssignmentsResponse(BaseModel):
    success: bool
    message: str
    assignments_count: int
    assignments: List[NotionAssignmentInfo]
    note: str


# Sync Log Models
class SyncLogResponse(BaseModel):
    success: bool
    message: str
    logs_count: int
    logs: List[Dict[str, Any]]
    note: str


class AuditLogResponse(BaseModel):
    success: bool
    message: str
    logs_count: int
    logs: List[Dict[str, Any]]
    note: str
