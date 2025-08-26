from typing import Dict, Any, List
from datetime import datetime, timezone
from loguru import logger

from app.services.canvas.client import CanvasAPIClient
from app.services.canvas.professor_detector import ProfessorDetector
from app.services.canvas.course_mapper import CourseMapper
from app.utils.date_utils import determine_semester_from_date


class CanvasSyncService:
    """
    Orchestrates the synchronization of Canvas courses to Notion.
    """

    def __init__(self, canvas_base_url: str, canvas_token: str):
        """
        Initialize the Canvas sync service.

        Args:
            canvas_base_url: Canvas instance base URL
            canvas_token: Canvas Personal Access Token
        """
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
            else:
                return {"success": False, "message": "Failed to connect to Canvas - check your credentials"}

        except Exception as e:
            logger.error(f"Canvas connection test failed: {e}")
            return {"success": False, "message": f"Canvas connection test failed: {str(e)}"}

    async def get_current_semester_courses(self) -> List[Dict]:
        """
        Get courses for the current semester.

        Returns:
            List of current semester course dictionaries
        """
        try:
            all_courses = await self.canvas_client.get_enrolled_courses()

            # Determine current semester
            current_date = datetime.now(timezone.utc)
            current_semester = determine_semester_from_date(current_date.isoformat())

            # Also consider the next semester (for transition periods)
            next_year = current_date.year
            next_semester = ""

            # Logic for determining next semester
            if current_date.month >= 10:  # Oct-Dec: Look for Spring of next year
                next_year = current_date.year + 1
                next_semester = f"Spring {next_year}"
            elif current_date.month <= 2:  # Jan-Feb: Look for Fall of same year
                next_semester = f"Fall {current_date.year}"
            elif current_date.month <= 5:  # Mar-May: Look for Summer of same year
                next_semester = f"Summer {current_date.year}"
            else:  # Jun-Sep: Look for Fall of same year
                next_semester = f"Fall {current_date.year}"

            logger.info(f"Current semester: {current_semester}, Next semester: {next_semester}")

            # Filter courses for current or next semester using enhanced detection
            current_semester_courses = []
            for course in all_courses:
                start_date = course.get("start_at", "")
                course_semester = determine_semester_from_date(start_date)

                if course_semester == current_semester:
                    current_semester_courses.append(course)

            logger.info(f"Found {len(current_semester_courses)} courses for {current_semester}")
            return current_semester_courses

        except Exception as e:
            logger.error(f"Failed to get current semester courses: {e}")
            return []

    async def enhance_course_with_professors(self, course: Dict) -> Dict:
        """
        Enhance a course with detailed professor information.

        Args:
            course: Canvas course dictionary

        Returns:
            Enhanced course with professor information
        """
        try:
            course_id = str(course.get("id", ""))
            if course_id:
                # Use the new approach to get actual professors
                professors = await self.professor_detector.get_professors_from_sections(course_id)
                if professors:
                    course["professors"] = professors
                    logger.info(f"Enhanced course {course.get('name')} with {len(professors)} professors via sections")
                else:
                    # Fallback: get detailed info with all instructors (old approach)
                    instructors = await self.professor_detector.get_professors_fallback(course_id)
                    if instructors:
                        course["all_instructors"] = instructors
                        logger.info(
                            f"Enhanced course {course.get('name')} with {len(instructors)} instructors via fallback"
                        )

            return course

        except Exception as e:
            logger.warning(f"Could not enhance course {course.get('id')} with professor info: {e}")
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
                return {
                    "success": False,
                    "message": "No enrolled courses found in Canvas",
                    "courses_found": 0,
                    "courses": [],
                }

            # Process each course to show detailed structure
            detailed_courses = []

            for course in canvas_courses:
                # Extract key information
                course_info = {
                    "canvas_id": course.get("id"),
                    "name": course.get("name"),
                    "course_code": course.get("course_code"),
                    "start_at": course.get("start_at"),
                    "end_at": course.get("end_at"),
                    "teachers": course.get("teachers", []),
                    "teacher_names": [teacher.get("display_name", "") for teacher in course.get("teachers", [])],
                    "total_students": course.get("total_students"),
                    "term": course.get("term"),
                    # Our parsed version
                    "parsed_info": self.course_mapper.map_canvas_course_to_notion(course),
                }

                detailed_courses.append(course_info)

            return {
                "success": True,
                "message": f"Retrieved detailed information for {len(detailed_courses)} courses",
                "courses_found": len(detailed_courses),
                "courses": detailed_courses,
                "note": "This shows the complete Canvas course structure",
            }

        except Exception as e:
            logger.error(f"Failed to get course inspection data: {e}")
            return {
                "success": False,
                "message": f"Failed to inspect courses: {str(e)}",
                "courses_found": 0,
                "courses": [],
            }

    async def get_professor_detection_comparison(self, course_id: str) -> Dict[str, Any]:
        """
        Compare different professor detection methods for a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            Dictionary comparing different detection methods
        """
        try:
            # Test the NEW sections approach
            professors_via_sections = await self.professor_detector.get_professors_from_sections(course_id)

            # Test the OLD enrollments approach for comparison
            instructors_via_enrollments = await self.professor_detector.get_professors_fallback(course_id)

            # Get basic course info too
            basic_courses = await self.canvas_client.get_enrolled_courses()
            target_course = None
            for course in basic_courses:
                if course.get("id") == int(course_id):
                    target_course = course
                    break

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
                    "count": len(target_course.get("teachers", [])) if target_course else 0,
                    "teachers": target_course.get("teachers", []) if target_course else [],
                    "method": "GET /courses (include[]=teachers)",
                },
                "recommendation": "Use professors_via_sections for best results - actual professors, not TAs",
            }

        except Exception as e:
            logger.error(f"Failed to compare professor detection methods: {e}")
            return {"success": False, "message": f"Professor detection comparison failed: {str(e)}"}
