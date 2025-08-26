from typing import List, Dict
from loguru import logger
from app.services.canvas.client import CanvasAPIClient


class ProfessorDetector:
    """
    Service for detecting actual professors (not TAs) for Canvas courses.
    Uses the sections-based approach for accurate professor identification.
    """

    def __init__(self, canvas_client: CanvasAPIClient):
        """
        Initialize the professor detector.

        Args:
            canvas_client: Configured Canvas API client
        """
        self.canvas_client = canvas_client

    async def get_professors_from_sections(self, course_id: str) -> List[Dict]:
        """
        Get actual professors (TeacherEnrollment) for a course by checking sections.

        This is the preferred method as it finds actual professors rather than TAs.

        Canvas API approach:
        1. GET /api/v1/courses/:course_id/sections
        2. GET /api/v1/sections/:section_id/enrollments?type[]=TeacherEnrollment&state[]=active&include[]=user

        Args:
            course_id: Canvas course ID

        Returns:
            List of professor objects with display_name, role, etc.
        """
        try:
            # Step 1: Get all sections for this course
            sections = await self.canvas_client.get_course_sections(course_id)

            if not sections:
                logger.warning(f"No sections found for course {course_id}")
                return []

            professors = []

            # Step 2: For each section, get TeacherEnrollments
            for section in sections:
                section_id = section.get("id")
                if not section_id:
                    continue

                try:
                    # Get only active TeacherEnrollments for this section
                    enrollments = await self.canvas_client.get_section_enrollments(
                        str(section_id), enrollment_types=["TeacherEnrollment"]
                    )

                    for enrollment in enrollments:
                        if enrollment.get("type") == "TeacherEnrollment":
                            user = enrollment.get("user", {})
                            if user:
                                professor = {
                                    "id": user.get("id"),
                                    "display_name": user.get("name", ""),
                                    "login_id": user.get("login_id", ""),
                                    "role": "Teacher",  # This is a real teacher, not TA
                                    "section_name": section.get("name", ""),
                                    "section_id": section_id,
                                }

                                # Avoid duplicates (same professor teaching multiple sections)
                                if not any(p.get("id") == professor["id"] for p in professors):
                                    professors.append(professor)

                except Exception as e:
                    logger.warning(f"Failed to get enrollments for section {section_id}: {e}")
                    continue

            if professors:
                professor_names = [p["display_name"] for p in professors]
                logger.info(f"Found {len(professors)} professors for course {course_id}: {professor_names}")
            else:
                logger.warning(f"No professors found for course {course_id}")

            return professors

        except Exception as e:
            logger.error(f"Failed to get professors for course {course_id}: {e}")
            return []

    async def get_professors_fallback(self, course_id: str) -> List[Dict]:
        """
        Fallback method to get instructors using course enrollments.

        This method gets both teachers and TAs, marking TAs clearly.
        Use this only when the sections approach fails.

        Args:
            course_id: Canvas course ID

        Returns:
            List of instructor objects (including TAs)
        """
        try:
            course_details = await self.canvas_client.get_course_details(course_id)
            if not course_details:
                return []

            # Get enrollments to find teachers and TAs
            params = {"type": ["TeacherEnrollment", "TaEnrollment"], "include": ["user"]}

            enrollments_result = await self.canvas_client._make_request(f"courses/{course_id}/enrollments", params)
            enrollments = enrollments_result if isinstance(enrollments_result, list) else []

            # Extract teachers from enrollments
            instructors = []
            for enrollment in enrollments:
                if enrollment.get("type") in ["TeacherEnrollment", "TaEnrollment"]:
                    user = enrollment.get("user", {})
                    if user:
                        instructors.append(
                            {
                                "id": user.get("id"),
                                "display_name": user.get("name", ""),
                                "avatar_image_url": user.get("avatar_url"),
                                "role": enrollment.get("type", "").replace("Enrollment", ""),
                            }
                        )

            if instructors:
                instructor_names = [i["display_name"] for i in instructors]
                logger.info(
                    f"Found {len(instructors)} instructors (fallback) for course {course_id}: {instructor_names}"
                )

            return instructors

        except Exception as e:
            logger.error(f"Failed to get instructors (fallback) for course {course_id}: {e}")
            return []

    def get_primary_professor(self, professors: List[Dict]) -> str:
        """
        Get the primary professor name from a list of professors.

        Args:
            professors: List of professor dictionaries

        Returns:
            Primary professor's display name or empty string
        """
        if not professors:
            return ""

        # For now, just return the first professor
        # In the future, could implement logic to determine the "primary" instructor
        return professors[0].get("display_name", "")
