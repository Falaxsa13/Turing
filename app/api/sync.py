from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from loguru import logger

from app.firebase import get_firebase_db
from app.auth import get_current_user_email
from app.schemas import SyncStartRequest, CanvasSyncResponse, AssignmentSyncRequest, AssignmentSyncResponse
from app.services.sync.coordinator import SyncCoordinator
from app.utils.notion_helper import NotionWorkspaceManager

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/start", response_model=CanvasSyncResponse)
async def start_canvas_notion_sync(request: SyncStartRequest, firebase_db=Depends(get_firebase_db)):
    """🚀 START: Fetch your enrolled Canvas courses and create them in Notion for the current semester."""
    try:
        user_email = request.user_email

        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        # Validate required settings
        if not user_settings.get("canvas_base_url") or not user_settings.get("canvas_pat"):
            raise HTTPException(
                status_code=400, detail="Canvas credentials not configured. Please set Canvas base URL and PAT."
            )

        if not user_settings.get("notion_token") or not user_settings.get("notion_parent_page_id"):
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Create sync coordinator and perform the sync
        logger.info(f"Starting Canvas to Notion sync for user: {user_email}")

        sync_coordinator = SyncCoordinator(
            canvas_base_url=user_settings["canvas_base_url"],
            canvas_token=user_settings["canvas_pat"],
            notion_token=user_settings["notion_token"],
            notion_parent_page_id=user_settings["notion_parent_page_id"],
        )

        sync_result = await sync_coordinator.sync_current_semester_courses()

        # Update last sync time if successful and log sync
        if sync_result["success"]:
            now = datetime.now(timezone.utc)
            await firebase_db.create_or_update_user_settings(
                user_email,
                {
                    "last_canvas_sync": now,
                    "last_notion_sync": now,
                    "updated_at": now,
                },
            )

            # Add sync log
            await firebase_db.add_sync_log(
                user_email,
                {
                    "sync_type": "courses",
                    "status": "success",
                    "items_processed": sync_result["courses_found"],
                    "items_created": sync_result["courses_created"],
                    "items_failed": sync_result["courses_failed"],
                    "items_skipped": sync_result["courses_skipped"],
                    "metadata": {"courses": sync_result["created_courses"][:5]},  # Limit logged data
                },
            )

            logger.info(f"Canvas sync completed for user: {user_email}")

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
        logger.error(f"Unexpected error during Canvas sync: {e}")

        # Log failed sync
        try:
            await firebase_db.add_sync_log(
                request.user_email,
                {
                    "sync_type": "courses",
                    "status": "failed",
                    "error_message": str(e),
                    "items_processed": 0,
                    "items_created": 0,
                    "items_failed": 0,
                    "items_skipped": 0,
                },
            )
        except:
            pass  # Don't fail if logging fails

        raise HTTPException(status_code=500, detail=f"Canvas sync failed: {str(e)}")


@router.post("/assignments", response_model=AssignmentSyncResponse)
async def sync_canvas_assignments(request: AssignmentSyncRequest, firebase_db=Depends(get_firebase_db)):
    """📝 ASSIGNMENTS: Fetch all assignments from previously synced Canvas courses and create them in Notion."""
    try:
        user_email = request.user_email

        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        # Validate required settings
        if not user_settings.get("canvas_base_url") or not user_settings.get("canvas_pat"):
            raise HTTPException(
                status_code=400, detail="Canvas credentials not configured. Please set Canvas base URL and PAT."
            )

        if not user_settings.get("notion_token") or not user_settings.get("notion_parent_page_id"):
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Create sync coordinator and perform assignment sync
        logger.info(f"Starting assignment sync for user: {user_email}")

        sync_coordinator = SyncCoordinator(
            canvas_base_url=user_settings["canvas_base_url"],
            canvas_token=user_settings["canvas_pat"],
            notion_token=user_settings["notion_token"],
            notion_parent_page_id=user_settings["notion_parent_page_id"],
        )

        sync_result = await sync_coordinator.sync_assignments_for_courses()

        # Update last sync time if successful and log sync
        if sync_result["success"] and sync_result["assignments_created"] > 0:
            now = datetime.now(timezone.utc)
            await firebase_db.create_or_update_user_settings(
                user_email,
                {
                    "last_assignment_sync": now,
                    "updated_at": now,
                },
            )

        # Add sync log
        status = "success" if sync_result["success"] else "failed"
        await firebase_db.add_sync_log(
            user_email,
            {
                "sync_type": "assignments",
                "status": status,
                "items_processed": sync_result["assignments_found"],
                "items_created": sync_result["assignments_created"],
                "items_failed": sync_result["assignments_failed"],
                "items_skipped": sync_result["assignments_skipped"],
                "metadata": {
                    "courses_processed": sync_result["courses_processed"],
                    "assignments": sync_result["created_assignments"][:10],  # Limit logged data
                },
            },
        )

        logger.info(f"Updated last assignment sync time for user: {user_email}")

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

        # Log failed sync
        try:
            await firebase_db.add_sync_log(
                request.user_email,
                {
                    "sync_type": "assignments",
                    "status": "failed",
                    "error_message": str(e),
                    "items_processed": 0,
                    "items_created": 0,
                    "items_failed": 0,
                    "items_skipped": 0,
                },
            )
        except:
            pass  # Don't fail if logging fails

        raise HTTPException(status_code=500, detail=f"Assignment sync failed: {str(e)}")


@router.get("/courses")
async def get_synced_courses(user_email: str, firebase_db=Depends(get_firebase_db)):
    """📚 Get all courses that have been synced from Canvas to Notion."""
    try:
        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        if not user_settings.get("notion_token") or not user_settings.get("notion_parent_page_id"):
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Get synced courses
        notion_manager = NotionWorkspaceManager(user_settings["notion_token"], user_settings["notion_parent_page_id"])
        synced_courses = await notion_manager.get_synced_courses()

        return {
            "success": True,
            "message": f"Found {len(synced_courses)} synced courses",
            "courses_count": len(synced_courses),
            "courses": synced_courses,
            "note": "These courses have Canvas IDs and were synced from Canvas",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get synced courses: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get synced courses: {str(e)}")


@router.get("/assignments")
async def get_synced_assignments(user_email: str, firebase_db=Depends(get_firebase_db)):
    """📝 Get all assignments that have been synced from Canvas to Notion."""
    try:
        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        if not user_settings.get("notion_token") or not user_settings.get("notion_parent_page_id"):
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Get synced assignments
        notion_manager = NotionWorkspaceManager(user_settings["notion_token"], user_settings["notion_parent_page_id"])
        synced_assignments = await notion_manager.get_existing_assignments()

        return {
            "success": True,
            "message": f"Found {len(synced_assignments)} synced assignments",
            "assignments_count": len(synced_assignments),
            "assignments": synced_assignments,
            "note": "These assignments have Canvas IDs and were synced from Canvas",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get synced assignments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get synced assignments: {str(e)}")


@router.get("/status")
async def get_sync_status(user_email: str, firebase_db=Depends(get_firebase_db)):
    """📊 Get overall sync status including course and assignment counts."""
    try:
        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        if not user_settings.get("notion_token") or not user_settings.get("notion_parent_page_id"):
            raise HTTPException(
                status_code=400, detail="Notion credentials not configured. Please set Notion token and parent page ID."
            )

        # Get sync data
        notion_manager = NotionWorkspaceManager(user_settings["notion_token"], user_settings["notion_parent_page_id"])
        synced_courses = await notion_manager.get_synced_courses()
        synced_assignments = await notion_manager.get_existing_assignments()

        # Get recent sync logs
        recent_sync_logs = await firebase_db.get_sync_logs(user_email, limit=5)

        return {
            "success": True,
            "user_email": user_email,
            "setup_status": {
                "has_canvas": bool(user_settings.get("canvas_base_url") and user_settings.get("canvas_pat")),
                "has_notion": bool(user_settings.get("notion_token") and user_settings.get("notion_parent_page_id")),
            },
            "sync_history": {
                "last_course_sync": user_settings.get("last_canvas_sync"),
                "last_assignment_sync": user_settings.get("last_assignment_sync"),
            },
            "sync_data": {
                "courses_synced": len(synced_courses),
                "assignments_synced": len(synced_assignments),
            },
            "courses": synced_courses,
            "assignments": synced_assignments[:10],  # Limit to first 10 for overview
            "recent_sync_logs": recent_sync_logs,
            "note": "Complete overview of your Canvas-to-Notion sync status",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")


@router.get("/logs")
async def get_sync_logs(user_email: str, limit: int = 20, firebase_db=Depends(get_firebase_db)):
    """📜 Get sync logs for the user."""
    try:
        # Get sync logs
        sync_logs = await firebase_db.get_sync_logs(user_email, limit)

        return {
            "success": True,
            "message": f"Found {len(sync_logs)} sync logs",
            "logs_count": len(sync_logs),
            "logs": sync_logs,
            "note": "Recent sync activity logs",
        }

    except Exception as e:
        logger.error(f"Failed to get sync logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sync logs: {str(e)}")


@router.get("/audit")
async def get_audit_logs(user_email: str, limit: int = 50, firebase_db=Depends(get_firebase_db)):
    """🔍 Get audit logs for the user."""
    try:
        # Get audit logs
        audit_logs = await firebase_db.get_audit_logs(user_email, limit)

        return {
            "success": True,
            "message": f"Found {len(audit_logs)} audit logs",
            "logs_count": len(audit_logs),
            "logs": audit_logs,
            "note": "Recent user activity audit logs",
        }

    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")
