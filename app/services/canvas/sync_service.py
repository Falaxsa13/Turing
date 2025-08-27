"""
Canvas synchronization service for orchestrating Canvas to Notion data flow.

This module provides services for testing Canvas connections, retrieving course data,
and coordinating the synchronization process with proper error handling and logging.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from loguru import logger

from app.services.canvas.client import CanvasAPIClient, CanvasAPIError
from app.services.canvas.professor_detector import ProfessorDetector, ProfessorDetectionError
from app.services.canvas.course_mapper import CourseMapper
from app.utils.date_utils import determine_semester_from_date

# Constants
CURRENT_YEAR = datetime.now().year
CURRENT_SEMESTER_MONTHS = {"Spring": [1, 2, 3, 4, 5], "Summer": [6, 7], "Fall": [8, 9, 10, 11, 12]}


class CanvasSyncError(Exception):
    """Custom exception for Canvas sync operations."""

    pass


class CanvasSyncService:
    """
    Orchestrates the synchronization of Canvas courses to Notion.

    This service provides methods for testing Canvas connections, retrieving
    course data, and coordinating the synchronization process with proper
    error handling and progress reporting.
    """

    def __init__(self, canvas_base_url: str, canvas_token: str):
        """
        Initialize the Canvas sync service.

        Args:
            canvas_base_url: Canvas instance base URL
            canvas_token: Canvas Personal Access Token

        Raises:
            ValueError: If required parameters are missing
        """
        if not canvas_base_url or not canvas_token:
            raise ValueError("Both canvas_base_url and canvas_token are required")

        self.canvas_client = CanvasAPIClient(canvas_base_url, canvas_token)
        self.professor_detector = ProfessorDetector(self.canvas_client)
        self.course_mapper = CourseMapper()

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the Canvas API connection.

        Returns:
            Dictionary with connection test results
        """
        try:
            user_info = await self.canvas_client.get_user_info()

            if user_info:
                return self._create_success_response(user_info)
            else:
                return {"success": False, "message": "Failed to connect to Canvas - check your credentials"}

        except CanvasAPIError as e:
            error_msg = f"Canvas API error during connection test: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during Canvas connection test: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    def _create_success_response(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a successful connection response.

        Args:
            user_info: Canvas user information

        Returns:
            Formatted success response
        """
        return {
            "success": True,
            "message": "Canvas connection successful",
            "user_info": {
                "id": user_info.get("id"),
                "name": user_info.get("name"),
                "email": user_info.get("email"),
                "login_id": user_info.get("login_id"),
            },
        }

    async def get_current_semester_courses(self) -> List[Dict[str, Any]]:
        """
        Get courses for the current semester.

        Returns:
            List of current semester course dictionaries
        """
        try:
            canvas_courses = await self.canvas_client.get_enrolled_courses()
            current_courses = []

            for course in canvas_courses:
                if self._is_current_semester_course(course):
                    enhanced_course = await self.enhance_course_with_professors(course)
                    current_courses.append(enhanced_course)

            logger.info(f"Found {len(current_courses)} current semester courses")
            return current_courses

        except CanvasAPIError as e:
            error_msg = f"Canvas API error getting current semester courses: {e}"
            logger.error(error_msg)
            raise CanvasSyncError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error getting current semester courses: {e}"
            logger.error(error_msg)
            raise CanvasSyncError(error_msg) from e

    def _is_current_semester_course(self, course: Dict[str, Any]) -> bool:
        """
        Determine if a course belongs to the current semester.

        Args:
            course: Canvas course dictionary

        Returns:
            True if course is from current semester, False otherwise
        """
        start_date = course.get("start_at")
        if not start_date:
            return True  # Assume current if no date

        term = determine_semester_from_date(start_date)
        return str(CURRENT_YEAR) in term

    async def enhance_course_with_professors(self, course: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance a course with detailed professor information.

        Args:
            course: Canvas course dictionary

        Returns:
            Enhanced course with professor information
        """
        try:
            course_id = str(course.get("id", ""))
            if not course_id:
                return course

            # Try sections-based approach first
            professors = await self._get_professors_via_sections(course, course_id)
            if professors:
                return course

            # Fallback to enrollments approach
            return await self._get_professors_via_fallback(course, course_id)

        except ProfessorDetectionError:
            logger.warning(f"Professor detection failed for course {course.get('id')}")
            return course
        except Exception as e:
            logger.warning(f"Could not enhance course {course.get('id')} with professor info: {e}")
            return course

    async def _get_professors_via_sections(self, course: Dict[str, Any], course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get professors using the sections-based approach.

        Args:
            course: Canvas course dictionary to enhance
            course_id: Canvas course ID

        Returns:
            Enhanced course or None if no professors found
        """
        professors = await self.professor_detector.get_professors_from_sections(course_id)
        if professors:
            course["professors"] = professors
            logger.info(f"Enhanced course {course.get('name')} with {len(professors)} professors via sections")
            return course
        return None

    async def _get_professors_via_fallback(self, course: Dict[str, Any], course_id: str) -> Dict[str, Any]:
        """
        Get professors using the fallback enrollments approach.

        Args:
            course: Canvas course dictionary to enhance
            course_id: Canvas course ID

        Returns:
            Enhanced course
        """
        instructors = await self.professor_detector.get_professors_fallback(course_id)
        if instructors:
            course["all_instructors"] = instructors
            logger.info(f"Enhanced course {course.get('name')} with {len(instructors)} instructors via fallback")
        return course

    async def get_course_inspection_data(self) -> Dict[str, Any]:
        """
        Get detailed inspection data for all enrolled courses.

        Returns:
            Dictionary with detailed course inspection information
        """
        try:
            canvas_courses = await self.canvas_client.get_enrolled_courses()

            if not canvas_courses:
                return self._create_empty_inspection_response()

            detailed_courses = await self._process_courses_for_inspection(canvas_courses)

            return {
                "success": True,
                "message": f"Retrieved detailed information for {len(detailed_courses)} courses",
                "courses_found": len(detailed_courses),
                "courses": detailed_courses,
                "note": "This shows the complete Canvas course structure",
            }

        except CanvasAPIError as e:
            error_msg = f"Canvas API error during course inspection: {e}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "courses_found": 0, "courses": []}
        except Exception as e:
            error_msg = f"Failed to inspect courses: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg, "courses_found": 0, "courses": []}

    def _create_empty_inspection_response(self) -> Dict[str, Any]:
        """Create response for when no courses are found."""
        return {
            "success": False,
            "message": "No enrolled courses found in Canvas",
            "courses_found": 0,
            "courses": [],
        }

    async def _process_courses_for_inspection(self, canvas_courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process courses for detailed inspection.

        Args:
            canvas_courses: List of Canvas course dictionaries

        Returns:
            List of detailed course information
        """
        detailed_courses = []

        for course in canvas_courses:
            course_info = self._extract_course_inspection_info(course)
            detailed_courses.append(course_info)

        return detailed_courses

    def _extract_course_inspection_info(self, course: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract detailed information for course inspection.

        Args:
            course: Canvas course dictionary

        Returns:
            Dictionary with extracted course information
        """
        teachers = course.get("teachers", [])

        return {
            "canvas_id": course.get("id"),
            "name": course.get("name"),
            "course_code": course.get("course_code"),
            "start_at": course.get("start_at"),
            "end_at": course.get("end_at"),
            "teachers": teachers,
            "teacher_names": [teacher.get("display_name", "") for teacher in teachers],
            "total_students": course.get("total_students"),
            "term": course.get("term"),
            # Our parsed version
            "parsed_info": self.course_mapper.map_canvas_course_to_notion(course),
        }

    async def get_professor_detection_comparison(self, course_id: str) -> Dict[str, Any]:
        """
        Compare different professor detection methods for a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            Dictionary comparing different detection methods

        Raises:
            ValueError: If course_id is empty
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        try:
            # Get data using different approaches
            professors_via_sections = await self.professor_detector.get_professors_from_sections(course_id)
            instructors_via_enrollments = await self.professor_detector.get_professors_fallback(course_id)
            target_course = await self._find_course_by_id(course_id)

            return self._build_comparison_response(
                course_id, target_course, professors_via_sections, instructors_via_enrollments
            )

        except (CanvasAPIError, ProfessorDetectionError) as e:
            error_msg = f"Professor detection comparison failed: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during professor detection comparison: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}

    async def _find_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a course by its ID.

        Args:
            course_id: Canvas course ID

        Returns:
            Course dictionary or None if not found
        """
        basic_courses = await self.canvas_client.get_enrolled_courses()
        for course in basic_courses:
            if course.get("id") == int(course_id):
                return course
        return None

    def _build_comparison_response(
        self,
        course_id: str,
        target_course: Optional[Dict[str, Any]],
        professors_via_sections: List[Dict[str, Any]],
        instructors_via_enrollments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build the comparison response structure.

        Args:
            course_id: Canvas course ID
            target_course: Course information or None
            professors_via_sections: Professors found via sections
            instructors_via_enrollments: Instructors found via enrollments

        Returns:
            Formatted comparison response
        """
        teachers_from_course = target_course.get("teachers", []) if target_course else []

        return {
            "success": True,
            "course_id": int(course_id),
            "course_name": target_course.get("name") if target_course else "Course not found",
            # NEW APPROACH: Sections-based professor detection
            "professors_via_sections": {
                "count": len(professors_via_sections),
                "professors": professors_via_sections,
                "method": "GET /sections/:id/enrollments?type[]=TeacherEnrollment",
            },
            # OLD APPROACH: Course enrollments (includes TAs)
            "instructors_via_enrollments": {
                "count": len(instructors_via_enrollments),
                "instructors": instructors_via_enrollments,
                "method": "GET /courses/:id/enrollments?type[]=TeacherEnrollment,TaEnrollment",
            },
            # BASIC APPROACH: Teachers from course data (often empty)
            "teachers_from_course": {
                "count": len(teachers_from_course),
                "teachers": teachers_from_course,
                "method": "GET /courses (include[]=teachers)",
            },
            "recommendation": "Use professors_via_sections for best results - actual professors, not TAs",
        }
