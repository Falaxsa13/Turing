from fastapi import APIRouter, Depends, HTTPException
from app.firebase import get_firebase_db
from app.core.exceptions import ValidationError, DatabaseError
from app.schemas.sync import (
    CanvasSyncResponse,
    AssignmentSyncRequest,
    AssignmentSyncResponse,
    SyncStatusResponse,
    SyncedCoursesResponse,
    SyncedAssignmentsResponse,
    SyncLogResponse,
    AuditLogResponse,
)
from app.schemas.setup import SyncStartRequest
from app.services.sync import CourseSyncService, AssignmentSyncService, SyncStatusService, SyncLogService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/start", response_model=CanvasSyncResponse)
async def start_canvas_notion_sync(request: SyncStartRequest, firebase_db=Depends(get_firebase_db)):
    """Fetch your enrolled Canvas courses and create them in Notion for the current semester."""
    try:
        course_sync_service = CourseSyncService(firebase_db)
        sync_result = await course_sync_service.sync_courses(request.user_email)

        return CanvasSyncResponse(
            success=sync_result["success"],
            message=sync_result["message"],
            courses_found=sync_result["courses_found"],
            courses_created=sync_result["courses_created"],
            courses_failed=sync_result["courses_failed"],
            courses_skipped=sync_result["courses_skipped"],
            created_courses=sync_result["created_courses"],
            failed_courses=sync_result["failed_courses"],
            note=sync_result["note"],
        )

    except (DatabaseError, ValidationError) as e:
        if isinstance(e, DatabaseError):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during Canvas sync: {e}")
        raise HTTPException(status_code=500, detail=f"Canvas sync failed: {str(e)}")


@router.post("/assignments", response_model=AssignmentSyncResponse)
async def sync_canvas_assignments(request: AssignmentSyncRequest, firebase_db=Depends(get_firebase_db)):
    """Fetch all assignments from previously synced Canvas courses and create them in Notion."""
    try:
        assignment_sync_service = AssignmentSyncService(firebase_db)
        sync_result = await assignment_sync_service.sync_assignments(request.user_email)

        return AssignmentSyncResponse(
            success=sync_result["success"],
            message=sync_result["message"],
            courses_processed=sync_result["courses_processed"],
            assignments_found=sync_result["assignments_found"],
            assignments_created=sync_result["assignments_created"],
            assignments_failed=sync_result["assignments_failed"],
            assignments_skipped=sync_result["assignments_skipped"],
            created_assignments=sync_result["created_assignments"],
            failed_assignments=sync_result["failed_assignments"],
            note=sync_result["note"],
        )

    except (DatabaseError, ValidationError) as e:
        if isinstance(e, DatabaseError):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during assignment sync: {e}")
        raise HTTPException(status_code=500, detail=f"Assignment sync failed: {str(e)}")


@router.get("/courses", response_model=SyncedCoursesResponse)
async def get_synced_courses(user_email: str, firebase_db=Depends(get_firebase_db)):
    """Get all courses that have been synced from Canvas to Notion."""
    try:
        status_service = SyncStatusService(firebase_db)
        return await status_service.get_synced_courses(user_email)

    except (DatabaseError, ValidationError) as e:
        if isinstance(e, DatabaseError):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get synced courses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get synced courses: {str(e)}")


@router.get("/assignments", response_model=SyncedAssignmentsResponse)
async def get_synced_assignments(user_email: str, firebase_db=Depends(get_firebase_db)):
    """Get all assignments that have been synced from Canvas to Notion."""
    try:
        status_service = SyncStatusService(firebase_db)
        return await status_service.get_synced_assignments(user_email)

    except (DatabaseError, ValidationError) as e:
        if isinstance(e, DatabaseError):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get synced assignments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get synced assignments: {str(e)}")


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(user_email: str, firebase_db=Depends(get_firebase_db)):
    """Get overall sync status including course and assignment counts."""
    try:
        status_service = SyncStatusService(firebase_db)
        return await status_service.get_sync_status(user_email)

    except (DatabaseError, ValidationError) as e:
        if isinstance(e, DatabaseError):
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.get("/logs", response_model=SyncLogResponse)
async def get_sync_logs(user_email: str, limit: int = 20, firebase_db=Depends(get_firebase_db)):
    """Get sync logs for the user."""
    try:
        log_service = SyncLogService(firebase_db)
        return await log_service.get_sync_logs(user_email, limit)

    except Exception as e:
        logger.error(f"Failed to get sync logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync logs: {str(e)}")


@router.get("/audit", response_model=AuditLogResponse)
async def get_audit_logs(user_email: str, limit: int = 50, firebase_db=Depends(get_firebase_db)):
    """Get audit logs for the user."""
    try:
        log_service = SyncLogService(firebase_db)
        return await log_service.get_audit_logs(user_email, limit)

    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")
