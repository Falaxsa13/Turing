from loguru import logger
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_firebase_services, FirebaseServices
from app.auth import get_current_user_email
from app.core.exceptions import ExternalServiceError, ValidationError, DatabaseError
from app.core.responses import success_response
from app.schemas.sync import CanvasInspectionResponse
from app.schemas.setup import CanvasTestRequest, CanvasTestResponse
from app.services.canvas import CanvasSyncService

router = APIRouter(prefix="/canvas", tags=["canvas"])


def _handle_known_errors(e: Exception):
    if isinstance(e, DatabaseError):
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, ValidationError):
        raise HTTPException(status_code=400, detail=str(e))
    raise e


def _require_credentials(settings: dict):
    if not (settings.get("canvas_base_url") and settings.get("canvas_pat")):
        raise ValidationError(
            "Canvas credentials not configured. Please set Canvas base URL and PAT.",
            field="canvas_credentials",
        )


@router.post("/test", response_model=CanvasTestResponse)
async def test_canvas_connection(request: CanvasTestRequest):
    """Test Canvas API connection with provided credentials."""
    try:
        service = CanvasSyncService(request.canvas_base_url, request.canvas_pat)
        result = await service.test_connection()

        return CanvasTestResponse(
            success=result["success"],
            message=result["message"],
            user_info=result.get("user_info", {}),
        )
    except Exception:
        logger.exception("Canvas connection test failed")
        raise ExternalServiceError(
            message="Canvas connection test failed",
            service="canvas",
            status_code=400,
        )


@router.post("/inspect", response_model=CanvasInspectionResponse)
async def inspect_canvas_courses(
    user_email: str = Depends(get_current_user_email),
    firebase_services: FirebaseServices = Depends(get_firebase_services),
):
    """Get detailed Canvas course structure including professor information."""
    try:
        try:
            settings_obj = await firebase_services.get_user_settings(user_email)
            settings = settings_obj.model_dump()

        except ValueError:
            raise DatabaseError("User not found. Please run /setup/init first.", operation="get_user")

        _require_credentials(settings)

        service = CanvasSyncService(settings["canvas_base_url"], settings["canvas_pat"])
        data = await service.get_course_inspection_data()

        return CanvasInspectionResponse(
            success=data["success"],
            message=data["message"],
            courses_found=data["courses_found"],
            courses=data["courses"],
            note=data.get("note", ""),
        )

    except (DatabaseError, ValidationError) as e:
        _handle_known_errors(e)
    except Exception:
        logger.exception("Canvas course inspection failed")
        raise ExternalServiceError(
            message="Canvas course inspection failed",
            service="canvas",
            status_code=500,
        )


@router.get("/course-details/{course_id}")
async def get_canvas_course_details(
    course_id: int,
    user_email: str = Depends(get_current_user_email),
    firebase_services: FirebaseServices = Depends(get_firebase_services),
):
    """Get detailed Canvas course information including sections and instructors."""
    try:
        try:
            settings_obj = await firebase_services.get_user_settings(user_email)
            settings = settings_obj.model_dump()
        except ValueError:
            raise DatabaseError("User not found", operation="get_user")

        _require_credentials(settings)

        service = CanvasSyncService(settings["canvas_base_url"], settings["canvas_pat"])
        detailed = await service.get_professor_detection_comparison(str(course_id))

        if not detailed["success"]:
            raise DatabaseError(f"Course {course_id} not found", operation="get_course")

        return success_response(
            data={
                "course_id": course_id,
                "detailed_info": detailed,
                "instructor_summary": {
                    "from_sections": detailed["professors_via_sections"]["count"],
                    "from_enrollments": detailed["instructors_via_enrollments"]["count"],
                    "total_unique": detailed["professors_via_sections"]["count"],
                    "instructor_names": [
                        inst.get("display_name", "") for inst in detailed["professors_via_sections"]["professors"]
                    ],
                },
            },
            message="Course details retrieved successfully",
        )

    except (DatabaseError, ValidationError) as e:
        _handle_known_errors(e)
    except Exception:
        logger.exception("Canvas course details retrieval failed")
        raise ExternalServiceError(
            message="Canvas course details retrieval failed",
            service="canvas",
            status_code=500,
        )
