from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.firebase import get_firebase_db
from app.schemas import CanvasTestRequest, CanvasTestResponse, CanvasInspectionResponse
from app.services.canvas import CanvasSyncService

router = APIRouter(prefix="/canvas", tags=["canvas"])


@router.post("/test", response_model=CanvasTestResponse)
async def test_canvas_connection(request: CanvasTestRequest):
    """🔍 Test Canvas API connection with provided credentials."""
    try:
        canvas_service = CanvasSyncService(request.canvas_base_url, request.canvas_pat)
        test_result = await canvas_service.test_connection()

        return CanvasTestResponse(
            success=test_result["success"],
            message=test_result["message"],
            user_info=test_result.get("user_info", {}),
        )

    except Exception as e:
        logger.error(f"Canvas connection test failed: {e}")
        raise HTTPException(status_code=400, detail=f"Canvas connection test failed: {str(e)}")


@router.post("/inspect")
async def inspect_canvas_courses(user_email: str, firebase_db=Depends(get_firebase_db)):
    """🔍 INSPECT: Get detailed Canvas course structure including professor information."""
    try:
        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found. Please run /setup/init first.")

        # Validate required settings
        if not user_settings.get("canvas_base_url") or not user_settings.get("canvas_pat"):
            raise HTTPException(
                status_code=400, detail="Canvas credentials not configured. Please set Canvas base URL and PAT."
            )

        # Create Canvas service and get inspection data
        canvas_service = CanvasSyncService(user_settings["canvas_base_url"], user_settings["canvas_pat"])
        inspection_data = await canvas_service.get_course_inspection_data()

        return CanvasInspectionResponse(
            success=inspection_data["success"],
            message=inspection_data["message"],
            courses_found=inspection_data["courses_found"],
            courses=inspection_data["courses"],
            note=inspection_data.get("note", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Canvas course inspection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Canvas course inspection failed: {str(e)}")


@router.post("/course-details")
async def get_canvas_course_details(course_id: int, user_email: str, firebase_db=Depends(get_firebase_db)):
    """🔍 Get detailed Canvas course information including sections and instructors."""
    try:
        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise HTTPException(status_code=404, detail="User not found")

        if not user_settings.get("canvas_base_url") or not user_settings.get("canvas_pat"):
            raise HTTPException(status_code=400, detail="Canvas credentials not configured")

        # Create Canvas service and get professor detection comparison (reuse for detailed info)
        canvas_service = CanvasSyncService(user_settings["canvas_base_url"], user_settings["canvas_pat"])
        detailed_info = await canvas_service.get_professor_detection_comparison(str(course_id))

        if not detailed_info["success"]:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

        return {
            "success": True,
            "course_id": course_id,
            "detailed_info": detailed_info,
            "instructor_summary": {
                "from_sections": detailed_info["professors_via_sections"]["count"],
                "from_enrollments": detailed_info["instructors_via_enrollments"]["count"],
                "total_unique": detailed_info["professors_via_sections"]["count"],
                "instructor_names": [
                    inst.get("display_name", "") for inst in detailed_info["professors_via_sections"]["professors"]
                ],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get course details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get course details: {str(e)}")
