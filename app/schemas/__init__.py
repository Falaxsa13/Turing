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

from app.schemas.canvas import (
    AssignmentSubmissionType,
    AssignmentWorkflowState,
    AssignmentGradingType,
    CanvasAssignmentDetails,
    CanvasAssignmentGroup,
    CanvasSubmissionInfo,
    EnhancedAssignmentData,
)

from app.schemas.notion import (
    NotionEntryRequest,
    NotionDatabaseInfo,
    NotionWorkspaceResponse,
    NotionSchemaResponse,
    NotionEntryResponse,
)

from app.schemas.notion import (
    NotionBlockType,
    NotionRichText,
    NotionBlockContent,
    NotionParagraphBlock,
    NotionHeadingBlock,
    NotionCalloutBlock,
    NotionToggleBlock,
    NotionDividerBlock,
    NotionBulletedListBlock,
    NotionNumberedListBlock,
    NotionCodeBlock,
    NotionBookmarkBlock,
    NotionAssignmentFormatting,
    NotionRichTextBuilder,
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
    # Enhanced Canvas schemas
    "AssignmentSubmissionType",
    "AssignmentWorkflowState",
    "AssignmentGradingType",
    "CanvasAssignmentDetails",
    "CanvasAssignmentGroup",
    "CanvasSubmissionInfo",
    "EnhancedAssignmentData",
    "NotionEntryRequest",
    "NotionDatabaseInfo",
    "NotionWorkspaceResponse",
    "NotionSchemaResponse",
    "NotionEntryResponse",
    # Enhanced Notion schemas
    "NotionBlockType",
    "NotionRichText",
    "NotionBlockContent",
    "NotionParagraphBlock",
    "NotionHeadingBlock",
    "NotionCalloutBlock",
    "NotionToggleBlock",
    "NotionDividerBlock",
    "NotionBulletedListBlock",
    "NotionNumberedListBlock",
    "NotionCodeBlock",
    "NotionBookmarkBlock",
    "NotionAssignmentFormatting",
    "NotionRichTextBuilder",
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
