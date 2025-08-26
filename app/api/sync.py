from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from loguru import logger

from app.db import get_db
from app.models import UserSettings
from app.schemas import SyncStartRequest, CanvasSyncResponse, AssignmentSyncRequest, AssignmentSyncResponse
from app.services.sync.coordinator import SyncCoordinator

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/start", response_model=CanvasSyncResponse)
async def start_canvas_notion_sync(request: SyncStartRequest, db: Session = Depends(get_db)):
    """🚀 START: Fetch your enrolled Canvas courses and create them in Notion for the current semester."""
    try:
        # Get user settings
        user = db.query(UserSettings).filter(UserSettings.user_email == request.user_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        # Validate required settings
        if not user.canvas_base_url or not user.canvas_pat:
            raise HTTPException(
                status_code=400, detail="Canvas credentials not configured. Please set Canvas base URL and PAT."
            )

        if not user.notion_token or not user.notion_parent_page_id:
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Create sync coordinator and perform the sync
        logger.info(f"Starting Canvas to Notion sync for user: {request.user_email}")

        sync_coordinator = SyncCoordinator(
            canvas_base_url=user.canvas_base_url,
            canvas_token=user.canvas_pat,
            notion_token=user.notion_token,
            notion_parent_page_id=user.notion_parent_page_id,
        )

        sync_result = await sync_coordinator.sync_current_semester_courses()

        # Update last sync time if successful
        if sync_result.get("success"):
            user.last_canvas_sync = datetime.now(timezone.utc)
            user.last_notion_sync = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Canvas sync completed for user: {request.user_email}")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start Canvas sync for {request.user_email}: {e}")
        raise HTTPException(status_code=500, detail=f"Canvas sync failed: {str(e)}")


@router.post("/assignments", response_model=AssignmentSyncResponse)
async def sync_canvas_assignments(request: AssignmentSyncRequest, db: Session = Depends(get_db)):
    """📝 ASSIGNMENTS: Fetch all assignments from previously synced Canvas courses and create them in Notion."""
    try:
        # Get user settings
        user = db.query(UserSettings).filter(UserSettings.user_email == request.user_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        # Validate required settings
        if not user.canvas_base_url or not user.canvas_pat:
            raise HTTPException(
                status_code=400, detail="Canvas credentials not configured. Please set Canvas base URL and PAT."
            )

        if not user.notion_token or not user.notion_parent_page_id:
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Create sync coordinator and perform assignment sync
        logger.info(f"Starting assignment sync for user: {request.user_email}")

        sync_coordinator = SyncCoordinator(
            canvas_base_url=user.canvas_base_url,
            canvas_token=user.canvas_pat,
            notion_token=user.notion_token,
            notion_parent_page_id=user.notion_parent_page_id,
        )

        sync_result = await sync_coordinator.sync_assignments_for_courses()

        # Update last sync time if successful
        if sync_result["success"] and sync_result["assignments_created"] > 0:
            user.last_assignment_sync = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Updated last assignment sync time for user: {request.user_email}")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during assignment sync: {e}")
        raise HTTPException(status_code=500, detail=f"Assignment sync failed: {str(e)}")
