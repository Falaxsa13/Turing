from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class AssignmentSubmissionType(str, Enum):
    """Canvas assignment submission types."""

    ONLINE_UPLOAD = "online_upload"
    ONLINE_TEXT_ENTRY = "online_text_entry"
    ONLINE_URL = "online_url"
    MEDIA_RECORDING = "media_recording"
    STUDENT_ANNOTATION = "student_annotation"
    NONE = "none"
    ON_PAPER = "on_paper"
    EXTERNAL_TOOL = "external_tool"
    DISCUSSION_TOPIC = "discussion_topic"
    QUIZ = "quiz"
    ONLINE_QUIZ = "online_quiz"
    ATTENDANCE = "attendance"
    NOT_GRADED = "not_graded"


class AssignmentWorkflowState(str, Enum):
    """Canvas assignment workflow states."""

    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    DELETED = "deleted"


class AssignmentGradingType(str, Enum):
    """Canvas assignment grading types."""

    POINTS = "points"
    PERCENTAGE = "percentage"
    PERCENT = "percent"
    LETTER_GRADE = "letter_grade"
    GPA_SCALE = "gpa_scale"
    PASS_FAIL = "pass_fail"
    NOT_GRADED = "not_graded"


class CanvasAssignmentDetails(BaseModel):
    """Comprehensive Canvas assignment details for rich Notion formatting."""

    # Basic Information (Required)
    id: int = Field(description="Canvas assignment ID")
    name: str = Field(description="Assignment name")
    course_id: int = Field(description="Canvas course ID")

    # Basic Information (Optional)
    description: Optional[str] = Field(default=None, description="Assignment description (HTML)")
    description_plain: Optional[str] = Field(default=None, description="Plain text description")

    # Dates and Timing (Optional)
    due_at: Optional[datetime] = Field(default=None, description="Assignment due date")
    lock_at: Optional[datetime] = Field(default=None, description="Assignment lock date")
    unlock_at: Optional[datetime] = Field(default=None, description="Assignment unlock date")
    created_at: Optional[datetime] = Field(default=None, description="Assignment creation date")
    updated_at: Optional[datetime] = Field(default=None, description="Assignment last update date")

    # Grading Information (Optional)
    points_possible: Optional[float] = Field(default=None, description="Total points possible")
    grading_type: Optional[AssignmentGradingType] = Field(default=None, description="Grading type")
    grading_standard_id: Optional[int] = Field(default=None, description="Grading standard ID")

    # Submission Details (Optional)
    submission_types: List[AssignmentSubmissionType] = Field(
        default_factory=list, description="Allowed submission types"
    )
    allowed_attempts: Optional[int] = Field(default=None, description="Number of allowed attempts (-1 = unlimited)")
    submission_downloads: Optional[bool] = Field(default=None, description="Allow submission downloads")

    # Assignment Settings (Optional with defaults)
    workflow_state: AssignmentWorkflowState = Field(
        default=AssignmentWorkflowState.UNPUBLISHED, description="Assignment workflow state"
    )
    published: bool = Field(default=False, description="Whether assignment is published")
    muted: Optional[bool] = Field(default=None, description="Whether notifications are muted")
    anonymous_grading: Optional[bool] = Field(default=None, description="Whether grading is anonymous")
    moderated_grading: Optional[bool] = Field(default=None, description="Whether grading is moderated")

    # Group and Peer Review (Optional)
    group_category_id: Optional[int] = Field(default=None, description="Group category ID for group assignments")
    peer_reviews: Optional[bool] = Field(default=None, description="Whether peer reviews are required")
    anonymous_peer_reviews: Optional[bool] = Field(default=None, description="Whether peer reviews are anonymous")
    peer_review_count: Optional[int] = Field(default=None, description="Number of peer reviews required")

    # External Tools and Integrations (Optional)
    external_tool_tag_attributes: Optional[Dict[str, Any]] = Field(
        default=None, description="External tool configuration"
    )
    lti_resource_link_id: Optional[str] = Field(default=None, description="LTI resource link ID")
    is_quiz_assignment: Optional[bool] = Field(default=None, description="Whether this is a quiz assignment")

    # Assignment Group and Position (Optional)
    assignment_group_id: Optional[int] = Field(default=None, description="Assignment group ID")
    position: Optional[int] = Field(default=None, description="Position in assignment group")

    # URLs and Links (Optional)
    html_url: Optional[str] = Field(default=None, description="Canvas assignment URL")
    quiz_id: Optional[int] = Field(default=None, description="Quiz ID if this is a quiz assignment")

    # Course Context (Optional)
    course_name: Optional[str] = Field(default=None, description="Course name for context")

    # Statistics and Analytics (Optional)
    score_statistics: Optional[Dict[str, Any]] = Field(default=None, description="Score statistics if available")
    rubric: Optional[List[Dict[str, Any]]] = Field(default=None, description="Assignment rubric if available")

    # Overrides and Special Cases (Optional)
    assignment_overrides: Optional[List[Dict[str, Any]]] = Field(default=None, description="Assignment overrides")
    omit_from_final_grade: Optional[bool] = Field(default=None, description="Whether to omit from final grade")
    hide_in_gradebook: Optional[bool] = Field(default=None, description="Whether to hide in gradebook")

    # Additional Metadata (Optional)
    important_dates: Optional[bool] = Field(default=None, description="Whether assignment has important dates")
    require_lockdown_browser: Optional[bool] = Field(default=None, description="Whether LockDown Browser is required")
    can_duplicate: Optional[bool] = Field(default=None, description="Whether assignment can be duplicated")

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class CanvasAssignmentGroup(BaseModel):
    """Canvas assignment group information."""

    id: int = Field(description="Assignment group ID")
    name: str = Field(description="Assignment group name")
    group_weight: Optional[float] = Field(default=None, description="Group weight in final grade")
    assignments_count: Optional[int] = Field(default=None, description="Number of assignments in group")
    assignment_visibility: Optional[List[int]] = Field(default=None, description="Student IDs who can see this group")


class CanvasSubmissionInfo(BaseModel):
    """Canvas submission information for the current user."""

    id: int = Field(description="Submission ID")
    user_id: int = Field(description="User ID")
    assignment_id: int = Field(description="Assignment ID")
    score: Optional[float] = Field(default=None, description="Submission score")
    grade: Optional[str] = Field(default=None, description="Submission grade")
    submitted_at: Optional[datetime] = Field(default=None, description="Submission timestamp")
    workflow_state: str = Field(description="Submission workflow state")
    late: Optional[bool] = Field(default=None, description="Whether submission was late")
    excused: Optional[bool] = Field(default=None, description="Whether submission was excused")
    attempt: Optional[int] = Field(default=None, description="Submission attempt number")
    body: Optional[str] = Field(default=None, description="Submission content")
    submission_type: Optional[str] = Field(default=None, description="Type of submission")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class EnhancedAssignmentData(BaseModel):
    """Enhanced assignment data combining Canvas details with Notion formatting."""

    canvas_details: CanvasAssignmentDetails = Field(description="Raw Canvas assignment data")
    assignment_group: Optional[CanvasAssignmentGroup] = Field(default=None, description="Assignment group info")
    submission_info: Optional[CanvasSubmissionInfo] = Field(default=None, description="User's submission info")
    notion_formatting: Dict[str, Any] = Field(description="Notion-specific formatting data")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}
