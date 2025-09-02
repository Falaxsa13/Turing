"""
Comprehensive sync API endpoints for Canvas to Notion synchronization.

This module provides endpoints for both course synchronization and enhanced assignment
synchronization with rich formatting and comprehensive Canvas assignment details.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from loguru import logger

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
from app.services.sync import CourseSyncService, SyncStatusService, SyncLogService
from app.services.sync.assignment_sync import AssignmentSyncService

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
    try:  # Initialize enhanced sync service
        assignment_sync_service = AssignmentSyncService(firebase_db)

        # Perform assignment sync
        sync_result: AssignmentSyncResponse = await assignment_sync_service.sync_assignments(
            user_email=request.user_email,
            include_submissions=request.include_submissions,
            include_statistics=request.include_statistics,
            include_rubrics=request.include_rubrics,
            include_assignment_groups=request.include_assignment_groups,
        )

        return sync_result
    except Exception as e:
        logger.error(f"Unexpected error in assignment sync: {e}")
        raise HTTPException(status_code=500, detail=f"Assignment sync failed: {str(e)}")


@router.get("/assignments/preview")
async def preview_assignment_formatting(
    user_email: str, assignment_id: str, course_id: str, firebase_db=Depends(get_firebase_db)
):
    """Preview how an assignment will be formatted in Notion."""
    try:
        logger.info(f"Assignment formatting preview requested for assignment {assignment_id}")

        return {
            "success": True,
            "message": "Assignment formatting preview",
            "assignment_id": assignment_id,
            "course_id": course_id,
            "preview": {
                "title": "Assignment Title",
                "type": "Assignment",
                "content_blocks": [
                    "Header with assignment title and type badge",
                    "Quick info callout with key details",
                    "Description section with cleaned HTML",
                    "Timing and due dates",
                    "Submission information",
                    "Assignment group details",
                    "Grading and statistics",
                    "Rubric with collapsible criteria",
                    "Canvas metadata and links",
                ],
                "note": "This is a preview of the rich formatting that would be applied.",
            },
        }

    except Exception as e:
        logger.error(f"Failed to create assignment preview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create assignment preview: {str(e)}")


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


@router.get("/get-assignments", response_model=SyncedAssignmentsResponse)
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
