from loguru import logger
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user_email
from app.core.exceptions import DatabaseError, ExternalServiceError, ValidationError
from app.firebase import get_firebase_db
from app.schemas.notion import (
    NotionEntryRequest,
    NotionEntryResponse,
    NotionSchemaResponse,
    NotionWorkspaceResponse,
)
from app.utils.notion_helper import (
    get_database_schemas,
    test_existing_databases,
    NotionWorkspaceManager,
)

router = APIRouter(prefix="/notion", tags=["notion"])


async def get_notion_credentials(
    user_email: str = Depends(get_current_user_email), firebase_db=Depends(get_firebase_db)
) -> Dict[str, Any]:
    """Get validated Notion credentials for authenticated user"""
    settings = await firebase_db.get_user_settings(user_email)
    if not settings:
        raise DatabaseError("User not found. Please run /setup/init first.", operation="get_user")

    if not (settings.get("notion_token") and settings.get("notion_parent_page_id")):
        raise ValidationError(
            "Notion credentials not configured. Please set Notion token and parent page ID.",
            field="notion_credentials",
        )

    return {"notion_token": settings["notion_token"], "notion_parent_page_id": settings["notion_parent_page_id"]}


@router.post("/test", response_model=NotionWorkspaceResponse)
async def test_notion_workspace(credentials: Dict[str, Any] = Depends(get_notion_credentials)):
    """Test access to your existing 3 Notion databases."""
    try:
        workspace_info = await test_existing_databases(
            credentials["notion_token"], credentials["notion_parent_page_id"]
        )

        return NotionWorkspaceResponse(
            success=workspace_info["success"],
            parent_page_id=workspace_info["parent_page_id"],
            databases_found=workspace_info["databases_found"],
            databases=workspace_info["databases"],
            message=workspace_info["message"],
        )
    except Exception as e:
        logger.error(f"Failed to test Notion workspace: {e}")
        raise ExternalServiceError(
            message=f"Failed to access Notion workspace: {str(e)}", service="notion", status_code=400
        )


@router.post("/schemas", response_model=NotionSchemaResponse)
async def get_notion_database_schemas(credentials: Dict[str, Any] = Depends(get_notion_credentials)):
    """Get the complete schemas/structures for all 3 databases (Courses, Notes, Assignments/Exams)."""
    try:
        schemas_info = await get_database_schemas(credentials["notion_token"], credentials["notion_parent_page_id"])

        return NotionSchemaResponse(
            success=schemas_info["success"],
            databases_found=schemas_info["databases_found"],
            schemas=schemas_info["schemas"],
            message=schemas_info["message"],
        )

    except Exception as e:
        logger.error(f"Failed to get database schemas: {e}")
        raise ExternalServiceError(
            message=f"Failed to retrieve database schemas: {str(e)}", service="notion", status_code=400
        )


@router.post("/add-course", response_model=NotionEntryResponse)
async def add_course_entry(request: NotionEntryRequest, credentials: Dict[str, Any] = Depends(get_notion_credentials)):
    """Add a course entry to your Courses database."""
    try:
        manager = NotionWorkspaceManager(credentials["notion_token"], credentials["notion_parent_page_id"])
        result = await manager.add_course_entry(request.entry_data)

        if result:
            return NotionEntryResponse(
                success=True,
                message="Course entry added successfully",
                page_id=result,
                note="Course created using actual database schema",
            )
        else:
            raise ValidationError("Failed to add course entry", field="entry_data")

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add course entry: {e}")
        raise ExternalServiceError(message=f"Failed to add course: {str(e)}", service="notion", status_code=500)


@router.post("/add-assignment", response_model=NotionEntryResponse)
async def add_assignment_entry(
    request: NotionEntryRequest, credentials: Dict[str, Any] = Depends(get_notion_credentials)
):
    """Add an assignment entry to your Assignments/Exams database."""
    try:
        manager = NotionWorkspaceManager(credentials["notion_token"], credentials["notion_parent_page_id"])
        result = await manager.add_assignment_entry(request.entry_data)

        if result:
            return NotionEntryResponse(
                success=True,
                message="Assignment entry added successfully",
                page_id=result,
                note="Assignment created using actual database schema",
            )
        else:
            raise ValidationError("Failed to add assignment entry", field="entry_data")

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add assignment entry: {e}")
        raise ExternalServiceError(message=f"Failed to add assignment: {str(e)}", service="notion", status_code=500)


@router.post("/add-note", response_model=NotionEntryResponse)
async def add_note_entry(request: NotionEntryRequest, credentials: Dict[str, Any] = Depends(get_notion_credentials)):
    """Add a note entry to your Notes database."""
    try:
        manager = NotionWorkspaceManager(credentials["notion_token"], credentials["notion_parent_page_id"])
        result = await manager.add_note_entry(request.entry_data)

        if result:
            return NotionEntryResponse(
                success=True,
                message="Note entry added successfully",
                page_id=result,
                note="Note created using actual database schema",
            )
        else:
            raise ValidationError("Failed to add note entry", field="entry_data")

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add note entry: {e}")
        raise ExternalServiceError(message=f"Failed to add note: {str(e)}", service="notion", status_code=500)
