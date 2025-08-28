from app.schemas.setup import (
    InitSetupRequest,
    CanvasPATRequest,
    CanvasTestRequest,
    SyncStartRequest,
    SetupResponse,
    SetupStatusResponse,
    CanvasTestResponse,
    ProfessorDetectionResponse,
)

from app.schemas.notion import (
    NotionTestRequest,
    NotionEntryRequest,
    NotionDatabaseInfo,
    NotionWorkspaceResponse,
    NotionSchemaResponse,
    NotionEntryResponse,
)

from app.schemas.sync import (
    SyncCourseInfo,
    SyncFailedCourse,
    CanvasSyncResponse,
    CourseInspectionInfo,
    CanvasInspectionResponse,
    SyncAssignmentInfo,
    SyncFailedAssignment,
    AssignmentSyncResponse,
    AssignmentSyncRequest,
)

from app.schemas.auth import (
    FirebaseLoginRequest,
    LoginResponse,
    LogoutRequest,
)

__all__ = [
    # Setup schemas
    "InitSetupRequest",
    "CanvasPATRequest",
    "CanvasTestRequest",
    "SyncStartRequest",
    "SetupResponse",
    "SetupStatusResponse",
    "CanvasTestResponse",
    "ProfessorDetectionResponse",
    # Notion schemas
    "NotionTestRequest",
    "NotionEntryRequest",
    "NotionDatabaseInfo",
    "NotionWorkspaceResponse",
    "NotionSchemaResponse",
    "NotionEntryResponse",
    # Sync schemas
    "SyncCourseInfo",
    "SyncFailedCourse",
    "CanvasSyncResponse",
    "CourseInspectionInfo",
    "CanvasInspectionResponse",
    # Assignment sync schemas
    "SyncAssignmentInfo",
    "SyncFailedAssignment",
    "AssignmentSyncResponse",
    "AssignmentSyncRequest",
    # Auth schemas
    "FirebaseLoginRequest",
    "LoginResponse",
    "LogoutRequest",
]
