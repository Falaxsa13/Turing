from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column
from datetime import datetime, timezone
from loguru import logger

from app.db import get_db
from app.models import UserSettings
from app.schemas import (
    InitSetupRequest,
    CanvasPATRequest,
    SetupResponse,
    SetupStatusResponse,
)

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post("/init", response_model=SetupResponse)
async def init_setup(request: InitSetupRequest, db: Session = Depends(get_db)):
    """Initialize user setup with Canvas and Notion credentials."""
    try:
        # Check if user already exists
        existing_user = db.query(UserSettings).filter(UserSettings.user_email == request.user_email).first()

        if existing_user:
            # Update existing user
            existing_user.canvas_base_url = request.canvas_base_url
            existing_user.notion_token = request.notion_token
            existing_user.notion_parent_page_id = request.notion_parent_page_id
            existing_user.updated_at = datetime.now(timezone.utc)

            db.commit()

            logger.info(f"Updated settings for user: {request.user_email}")
            return SetupResponse(message="User settings updated successfully", user_email=request.user_email)
        else:
            # Create new user
            new_user = UserSettings(
                user_email=request.user_email,
                canvas_base_url=request.canvas_base_url,
                notion_token=request.notion_token,
                notion_parent_page_id=request.notion_parent_page_id,
            )

            db.add(new_user)
            db.commit()

            logger.info(f"Created new user: {request.user_email}")
            return SetupResponse(message="User settings created successfully", user_email=request.user_email)

    except Exception as e:
        logger.error(f"Failed to init setup for {request.user_email}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Setup initialization failed: {str(e)}")


@router.post("/canvas/pat")
async def save_canvas_pat(request: CanvasPATRequest, user_email: str, db: Session = Depends(get_db)):
    """Save Canvas Personal Access Token for a user."""
    try:
        user = db.query(UserSettings).filter(UserSettings.user_email == user_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        # Update Canvas PAT
        user.canvas_pat = request.canvas_pat
        user.updated_at = datetime.now(timezone.utc)

        db.commit()

        logger.info(f"Updated Canvas PAT for user: {user_email}")
        return {"message": "Canvas Personal Access Token saved successfully", "user_email": user_email}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save Canvas PAT for {user_email}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save Canvas PAT: {str(e)}")


@router.get("/me", response_model=SetupStatusResponse)
async def get_setup_status(user_email: str, db: Session = Depends(get_db)):
    """Get current setup status for a user."""
    try:
        user = db.query(UserSettings).filter(UserSettings.user_email == user_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        return SetupStatusResponse(
            has_canvas=(user.canvas_base_url is not None and user.canvas_pat is not None),
            has_notion=(user.notion_token is not None and user.notion_parent_page_id is not None),
            has_google=(user.google_credentials is not None),
            calendar_id=user.google_calendar_id,
            last_canvas_sync=user.last_canvas_sync,
            last_notion_sync=user.last_notion_sync,
            last_google_sync=user.last_google_sync,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get setup status for {user_email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get setup status: {str(e)}")
