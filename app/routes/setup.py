from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.db import get_db
from app.models import UserSettings

router = APIRouter(prefix="/setup", tags=["setup"])


# Request models
class InitSetupRequest(BaseModel):
    user_email: EmailStr
    canvas_base_url: str
    notion_token: str
    notion_parent_page_id: str


class CanvasPATRequest(BaseModel):
    canvas_pat: str


class NotionTestRequest(BaseModel):
    notion_token: str
    notion_parent_page_id: str


class NotionEntryRequest(BaseModel):
    notion_token: str
    notion_parent_page_id: str
    entry_data: Dict[str, Any]


# Response models
class SetupStatusResponse(BaseModel):
    has_canvas: bool
    has_notion: bool
    has_google: bool
    calendar_id: Optional[str] = None
    last_canvas_sync: Optional[datetime] = None
    last_notion_sync: Optional[datetime] = None
    last_google_sync: Optional[datetime] = None


class SetupResponse(BaseModel):
    message: str
    user_email: str


@router.post("/init", response_model=SetupResponse)
async def init_setup(request: InitSetupRequest, db: Session = Depends(get_db)):
    """Initialize user setup with basic configuration"""
    try:
        # Check if user already exists
        existing_user = db.query(UserSettings).filter(UserSettings.user_email == request.user_email).first()

        if existing_user:
            # Update existing user
            setattr(existing_user, "canvas_base_url", request.canvas_base_url)
            setattr(existing_user, "notion_token", request.notion_token)
            setattr(existing_user, "notion_parent_page_id", request.notion_parent_page_id)
            setattr(existing_user, "updated_at", datetime.utcnow())

            db.commit()
            db.refresh(existing_user)

            logger.info(f"Updated setup for user: {request.user_email}")
            return SetupResponse(message="Setup updated successfully", user_email=request.user_email)
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
            db.refresh(new_user)

            logger.info(f"Created setup for user: {request.user_email}")
            return SetupResponse(message="Setup initialized successfully", user_email=request.user_email)

    except Exception as e:
        logger.error(f"Failed to initialize setup for {request.user_email}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to initialize setup")


@router.post("/canvas/pat", response_model=dict)
async def save_canvas_pat(
    request: CanvasPATRequest,
    user_email: str,  # This would typically come from authentication
    db: Session = Depends(get_db),
):
    """Save Canvas Personal Access Token"""
    try:
        # For MVP, we'll use a query parameter for user_email
        # In production, this would come from authenticated user session
        user = db.query(UserSettings).filter(UserSettings.user_email == user_email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Save the Canvas PAT
        setattr(user, "canvas_pat", request.canvas_pat)
        setattr(user, "updated_at", datetime.utcnow())

        db.commit()

        logger.info(f"Saved Canvas PAT for user: {user_email}")
        return {"message": "Canvas PAT saved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save Canvas PAT for {user_email}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save Canvas PAT")


@router.post("/notion/test")
async def test_notion_workspace(request: NotionTestRequest):
    """Test access to your existing 3 Notion databases"""
    try:
        from app.utils.notion_helper import test_existing_databases

        workspace_info = await test_existing_databases(request.notion_token, request.notion_parent_page_id)

        return workspace_info

    except Exception as e:
        logger.error(f"Failed to test Notion workspace: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to access Notion workspace: {str(e)}")


@router.post("/notion/schemas")
async def get_notion_database_schemas(request: NotionTestRequest):
    """Get the complete schemas/structures for all 3 databases (Courses, Notes, Assignments/Exams)"""
    try:
        from app.utils.notion_helper import get_database_schemas

        schemas_info = await get_database_schemas(request.notion_token, request.notion_parent_page_id)

        return schemas_info

    except Exception as e:
        logger.error(f"Failed to get database schemas: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to retrieve database schemas: {str(e)}")


@router.post("/notion/demo")
async def demo_notion_entries(request: NotionTestRequest):
    """Add demo entries to all 3 existing databases (Courses, Notes, Assignments/Exams)"""
    try:
        from app.utils.notion_helper import demo_add_entries

        result = await demo_add_entries(request.notion_token, request.notion_parent_page_id)

        return result

    except Exception as e:
        logger.error(f"Failed to add demo entries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add demo entries: {str(e)}")


@router.post("/notion/add-course")
async def add_course_entry(request: NotionEntryRequest):
    """Add a course entry to your Courses database"""
    try:
        from app.utils.notion_helper import NotionWorkspaceManager

        manager = NotionWorkspaceManager(request.notion_token, request.notion_parent_page_id)
        result = await manager.add_course_entry(request.entry_data)

        if result:
            return {
                "success": True,
                "message": "Course entry added successfully",
                "page_id": result,
                "note": "TODO: Update course properties in notion_helper.py to match your database structure",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add course entry")

    except Exception as e:
        logger.error(f"Failed to add course entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add course: {str(e)}")


@router.post("/notion/add-assignment")
async def add_assignment_entry(request: NotionEntryRequest):
    """Add an assignment entry to your Assignments/Exams database"""
    try:
        from app.utils.notion_helper import NotionWorkspaceManager

        manager = NotionWorkspaceManager(request.notion_token, request.notion_parent_page_id)
        result = await manager.add_assignment_entry(request.entry_data)

        if result:
            return {
                "success": True,
                "message": "Assignment entry added successfully",
                "page_id": result,
                "note": "TODO: Update assignment properties in notion_helper.py to match your database structure",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add assignment entry")

    except Exception as e:
        logger.error(f"Failed to add assignment entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add assignment: {str(e)}")


@router.post("/notion/add-note")
async def add_note_entry(request: NotionEntryRequest):
    """Add a note entry to your Notes database"""
    try:
        from app.utils.notion_helper import NotionWorkspaceManager

        manager = NotionWorkspaceManager(request.notion_token, request.notion_parent_page_id)
        result = await manager.add_note_entry(request.entry_data)

        if result:
            return {
                "success": True,
                "message": "Note entry added successfully",
                "page_id": result,
                "note": "TODO: Update note properties in notion_helper.py to match your database structure",
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add note entry")

    except Exception as e:
        logger.error(f"Failed to add note entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add note: {str(e)}")


# Legacy endpoints (updated to work with existing databases)
@router.post("/notion/initialize")
async def initialize_notion_workspace(request: NotionTestRequest):
    """Demo: Add sample entries to your existing 3 databases"""
    return await demo_notion_entries(request)


@router.get("/me", response_model=SetupStatusResponse)
async def get_setup_status(
    user_email: str, db: Session = Depends(get_db)  # This would typically come from authentication
):
    """Get current user setup status"""
    try:
        user = db.query(UserSettings).filter(UserSettings.user_email == user_email).first()

        if not user:
            # Return default status for non-existent user
            return SetupStatusResponse(has_canvas=False, has_notion=False, has_google=False)

        # Check what integrations are configured
        has_canvas = bool(user.canvas_base_url) and bool(user.canvas_pat)
        has_notion = bool(user.notion_token) and bool(user.notion_parent_page_id)
        has_google = bool(user.google_credentials)

        return SetupStatusResponse(
            has_canvas=has_canvas,
            has_notion=has_notion,
            has_google=has_google,
            calendar_id=user.google_calendar_id,
            last_canvas_sync=user.last_canvas_sync,
            last_notion_sync=user.last_notion_sync,
            last_google_sync=user.last_google_sync,
        )

    except Exception as e:
        logger.error(f"Failed to get setup status for {user_email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get setup status")
