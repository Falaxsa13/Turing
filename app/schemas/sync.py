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
