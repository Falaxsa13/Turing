from pydantic import BaseModel
from typing import List, Dict, Any, Optional


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
