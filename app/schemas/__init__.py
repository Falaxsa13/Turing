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
]
