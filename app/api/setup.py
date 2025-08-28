"""
Setup and configuration API endpoints for the Turing Project.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user_email
from app.core.exceptions import DatabaseError, ExternalServiceError, ValidationError
from app.core.responses import error_response, success_response
from app.firebase import get_firebase_db
from app.schemas.setup import CanvasPATRequest, InitSetupRequest, SetupResponse, SetupStatusResponse

# Module-level logger (industry standard)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/init", response_model=SetupResponse)
async def init_setup(request: InitSetupRequest, firebase_db=Depends(get_firebase_db)):
    """🚀 Initialize user setup with Canvas and Notion credentials."""
    try:
        user_email = request.user_email

        # Prepare user settings data
        now = datetime.now(timezone.utc)
        user_data = {
            "canvas_base_url": request.canvas_base_url,
            "notion_token": request.notion_token,
            "notion_parent_page_id": request.notion_parent_page_id,
            "updated_at": now,
        }

        # Check if user already exists
        existing_user = await firebase_db.get_user_settings(user_email)
        if not existing_user:
            user_data["created_at"] = now
            logger.info(f"Creating new user: {user_email}")
        else:
            logger.info(f"Updating existing user: {user_email}")

        # Create or update user settings
        success = await firebase_db.create_or_update_user_settings(user_email, user_data)

        if not success:
            raise DatabaseError("Failed to save user settings", operation="save_user", collection="user_settings")

        # Log the setup action
        await firebase_db.add_audit_log(
            user_email=user_email,
            action="setup_init",
            target_id=user_email,
            metadata={
                "canvas_base_url": request.canvas_base_url,
                "has_notion_token": bool(request.notion_token),
                "has_notion_parent_page": bool(request.notion_parent_page_id),
            },
        )

        logger.info(f"Setup initialized for user: {user_email}")

        return SetupResponse(
            success=True,
            message="Setup initialized successfully",
            user_email=user_email,
            next_step="Save your Canvas Personal Access Token using /setup/canvas/pat",
        )

    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Setup initialization failed: {e}")
        raise ExternalServiceError(message=f"Setup initialization failed: {str(e)}", service="setup", status_code=500)


@router.post("/canvas/pat")
async def save_canvas_pat(request: CanvasPATRequest, user_email: str, firebase_db=Depends(get_firebase_db)):
    """🔑 Save Canvas Personal Access Token for the user."""
    try:
        # Get existing user settings
        user_settings = await firebase_db.get_user_settings(user_email)
        if not user_settings:
            raise DatabaseError(
                "User not found. Please run /setup/init first.", operation="get_user", collection="user_settings"
            )

        # Update Canvas PAT
        user_data = {
            "canvas_pat": request.canvas_pat,
            "updated_at": datetime.now(timezone.utc),
        }

        success = await firebase_db.create_or_update_user_settings(user_email, user_data)

        if not success:
            raise DatabaseError("Failed to save Canvas PAT", operation="save_canvas_pat", collection="user_settings")

        # Log the action
        await firebase_db.add_audit_log(
            user_email=user_email, action="canvas_pat_saved", target_id=user_email, metadata={"has_canvas_pat": True}
        )

        logger.info(f"Canvas PAT saved for user: {user_email}")

        return {
            "success": True,
            "message": "Canvas PAT saved successfully",
            "next_step": "Test your Canvas connection using /canvas/test",
        }

    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to save Canvas PAT: {e}")
        raise ExternalServiceError(message=f"Failed to save Canvas PAT: {str(e)}", service="setup", status_code=500)


@router.get("/me", response_model=SetupStatusResponse)
async def get_setup_status(user_email: str, firebase_db=Depends(get_firebase_db)):
    """📊 Get setup status for the user."""
    try:
        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            # Return default status for new user
            return SetupStatusResponse(
                user_email=user_email,
                has_canvas=False,
                has_notion=False,
                has_google=False,
                last_canvas_sync=None,
                last_notion_sync=None,
                last_google_sync=None,
                last_assignment_sync=None,
                setup_complete=False,
                next_steps=[
                    "Run /setup/init to initialize your account",
                    "Save Canvas credentials",
                    "Test Canvas connection",
                    "Start syncing with /sync/start",
                ],
            )

        # Check what's configured
        has_canvas = bool(user_settings.get("canvas_base_url") and user_settings.get("canvas_pat"))
        has_notion = bool(user_settings.get("notion_token") and user_settings.get("notion_parent_page_id"))
        has_google = bool(user_settings.get("google_credentials"))

        setup_complete = has_canvas and has_notion

        # Determine next steps
        next_steps = []
        if not has_canvas:
            next_steps.append("Save Canvas credentials using /setup/canvas/pat")
        if not has_notion:
            next_steps.append("Configure Notion workspace using /setup/init")
        if setup_complete:
            next_steps.append("Start syncing with /sync/start")

        return SetupStatusResponse(
            user_email=user_email,
            has_canvas=has_canvas,
            has_notion=has_notion,
            has_google=has_google,
            last_canvas_sync=user_settings.get("last_canvas_sync"),
            last_notion_sync=user_settings.get("last_notion_sync"),
            last_google_sync=user_settings.get("last_google_sync"),
            last_assignment_sync=user_settings.get("last_assignment_sync"),
            setup_complete=setup_complete,
            next_steps=next_steps,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get setup status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setup status: {str(e)}")
