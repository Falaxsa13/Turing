"""
Notion API endpoints for course management and synchronization.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.firebase import get_firebase_db
from app.core.exceptions import ExternalServiceError, ValidationError
from app.core.responses import success_response, error_response
from app.schemas.notion import (
    NotionTestRequest,
    NotionEntryRequest,
    NotionWorkspaceResponse,
    NotionSchemaResponse,
    NotionEntryResponse,
)
import logging

# Module-level logger (industry standard)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notion", tags=["notion"])


@router.post("/test", response_model=NotionWorkspaceResponse)
async def test_notion_workspace(request: NotionTestRequest):
    """Test access to your existing 3 Notion databases."""
    try:
        from app.utils.notion_helper import test_existing_databases

        workspace_info = await test_existing_databases(request.notion_token, request.notion_parent_page_id)

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
async def get_notion_database_schemas(request: NotionTestRequest):
    """Get the complete schemas/structures for all 3 databases (Courses, Notes, Assignments/Exams)."""
    try:
        from app.utils.notion_helper import get_database_schemas

        schemas_info = await get_database_schemas(request.notion_token, request.notion_parent_page_id)

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


@router.post("/demo")
async def demo_notion_entries(request: NotionTestRequest):
    """Add demo entries to all 3 existing databases (Courses, Notes, Assignments/Exams)."""
    try:
        from app.utils.notion_helper import demo_add_entries

        result = await demo_add_entries(request.notion_token, request.notion_parent_page_id)
        return result
    except Exception as e:
        logger.error(f"Failed to add demo entries: {e}")
        raise ExternalServiceError(message=f"Failed to add demo entries: {str(e)}", service="notion", status_code=500)


@router.post("/add-course", response_model=NotionEntryResponse)
async def add_course_entry(request: NotionEntryRequest):
    """Add a course entry to your Courses database."""
    try:
        from app.utils.notion_helper import NotionWorkspaceManager

        manager = NotionWorkspaceManager(request.notion_token, request.notion_parent_page_id)
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
async def add_assignment_entry(request: NotionEntryRequest):
    """Add an assignment entry to your Assignments/Exams database."""
    try:
        from app.utils.notion_helper import NotionWorkspaceManager

        manager = NotionWorkspaceManager(request.notion_token, request.notion_parent_page_id)
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
async def add_note_entry(request: NotionEntryRequest):
    """Add a note entry to your Notes database."""
    try:
        from app.utils.notion_helper import NotionWorkspaceManager

        manager = NotionWorkspaceManager(request.notion_token, request.notion_parent_page_id)
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


# Legacy endpoint for backward compatibility
@router.post("/initialize")
async def initialize_notion_workspace(request: NotionTestRequest):
    """Demo: Add sample entries to your existing 3 databases."""
    return await demo_notion_entries(request)
