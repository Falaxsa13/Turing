"""
Professor detection service for Canvas courses.

This module provides utilities for detecting actual professors (not TAs) in Canvas courses
using the sections-based approach for maximum accuracy.
"""

from typing import List, Dict, Any, Optional, Set
from loguru import logger
from app.services.canvas.client import CanvasAPIClient, CanvasAPIError

# Constants for enrollment types
TEACHER_ENROLLMENT = "TeacherEnrollment"
TA_ENROLLMENT = "TaEnrollment"
VALID_ENROLLMENT_TYPES = [TEACHER_ENROLLMENT, TA_ENROLLMENT]

# Role constants
TEACHER_ROLE = "Teacher"
TA_ROLE = "Ta"


class ProfessorDetectionError(Exception):
    """Custom exception for professor detection errors."""

    pass


class ProfessorDetector:
    """
    Service for detecting actual professors (not TAs) for Canvas courses.

    Uses the sections-based approach for accurate professor identification,
    with a fallback method when sections are not available.
    """

    def __init__(self, canvas_client: CanvasAPIClient):
        """
        Initialize the professor detector.

        Args:
            canvas_client: Configured Canvas API client

        Raises:
            ValueError: If canvas_client is None
        """
        if canvas_client is None:
            raise ValueError("canvas_client cannot be None")
        self.canvas_client = canvas_client

    async def get_professors_from_sections(self, course_id: str) -> List[Dict[str, Any]]:
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

        Raises:
            ValueError: If course_id is empty
            ProfessorDetectionError: If there's an error in the detection process
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        try:
            # Step 1: Get all sections for this course
            sections = await self.canvas_client.get_course_sections(course_id)

            if not sections:
                logger.warning(f"No sections found for course {course_id}")
                return []

            professors = await self._extract_professors_from_sections(sections, course_id)

            self._log_professor_results(professors, course_id, "sections-based")
            return professors

        except CanvasAPIError as e:
            error_msg = f"Canvas API error while getting professors for course {course_id}: {e}"
            logger.error(error_msg)
            raise ProfessorDetectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error while getting professors for course {course_id}: {e}"
            logger.error(error_msg)
            raise ProfessorDetectionError(error_msg) from e

    async def _extract_professors_from_sections(
        self, sections: List[Dict[str, Any]], course_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract professors from a list of course sections.

        Args:
            sections: List of section dictionaries
            course_id: Canvas course ID (for logging)

        Returns:
            List of unique professor objects
        """
        professors: List[Dict[str, Any]] = []
        seen_professor_ids: Set[int] = set()

        # Step 2: For each section, get TeacherEnrollments
        for section in sections:
            section_id = section.get("id")
            if not section_id:
                continue

            try:
                section_professors = await self._get_professors_from_section(section, course_id)

                # Add unique professors (avoid duplicates across sections)
                for professor in section_professors:
                    prof_id = professor.get("id")
                    if prof_id and prof_id not in seen_professor_ids:
                        professors.append(professor)
                        seen_professor_ids.add(prof_id)

            except Exception as e:
                logger.warning(f"Failed to get enrollments for section {section_id}: {e}")
                continue

        return professors

    async def _get_professors_from_section(self, section: Dict[str, Any], course_id: str) -> List[Dict[str, Any]]:
        """
        Get professors from a single section.

        Args:
            section: Section dictionary
            course_id: Canvas course ID (for logging)

        Returns:
            List of professor objects from this section
        """
        section_id = section.get("id")
        section_name = section.get("name", "")

        # Get only active TeacherEnrollments for this section
        enrollments = await self.canvas_client.get_section_enrollments(
            str(section_id), enrollment_types=[TEACHER_ENROLLMENT]
        )

        professors = []
        for enrollment in enrollments:
            if enrollment.get("type") == TEACHER_ENROLLMENT:
                professor = self._create_professor_from_enrollment(enrollment, section_name, section_id)
                if professor:
                    professors.append(professor)

        return professors

    def _create_professor_from_enrollment(
        self, enrollment: Dict[str, Any], section_name: str, section_id: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Create a professor object from an enrollment record.

        Args:
            enrollment: Enrollment dictionary
            section_name: Name of the section
            section_id: ID of the section

        Returns:
            Professor dictionary or None if user data is missing
        """
        user = enrollment.get("user", {})
        if not user:
            return None

        return {
            "id": user.get("id"),
            "display_name": user.get("name", ""),
            "login_id": user.get("login_id", ""),
            "role": TEACHER_ROLE,  # This is a real teacher, not TA
            "section_name": section_name,
            "section_id": section_id,
        }

    async def get_professors_fallback(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Fallback method to get instructors using course enrollments.

        This method gets both teachers and TAs, marking TAs clearly.
        Use this only when the sections approach fails.

        Args:
            course_id: Canvas course ID

        Returns:
            List of instructor objects (including TAs)

        Raises:
            ValueError: If course_id is empty
            ProfessorDetectionError: If there's an error in the detection process
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        try:
            course_details = await self.canvas_client.get_course_details(course_id)
            if not course_details:
                logger.warning(f"No course details found for course {course_id}")
                return []

            instructors = await self._get_instructors_from_enrollments(course_id)

            self._log_professor_results(instructors, course_id, "fallback")
            return instructors

        except CanvasAPIError as e:
            error_msg = f"Canvas API error in fallback method for course {course_id}: {e}"
            logger.error(error_msg)
            raise ProfessorDetectionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error in fallback method for course {course_id}: {e}"
            logger.error(error_msg)
            raise ProfessorDetectionError(error_msg) from e

    async def _get_instructors_from_enrollments(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get instructors from course enrollments.

        Args:
            course_id: Canvas course ID

        Returns:
            List of instructor objects
        """
        # Get enrollments to find teachers and TAs
        params = {"type": VALID_ENROLLMENT_TYPES, "include": ["user"]}

        enrollments_result = await self.canvas_client._make_request(f"courses/{course_id}/enrollments", params)
        enrollments = enrollments_result if isinstance(enrollments_result, list) else []

        # Extract teachers from enrollments
        instructors = []
        for enrollment in enrollments:
            enrollment_type = enrollment.get("type")
            if enrollment_type in VALID_ENROLLMENT_TYPES:
                instructor = self._create_instructor_from_enrollment(enrollment)
                if instructor:
                    instructors.append(instructor)

        return instructors

    def _create_instructor_from_enrollment(self, enrollment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create an instructor object from an enrollment record.

        Args:
            enrollment: Enrollment dictionary

        Returns:
            Instructor dictionary or None if user data is missing
        """
        user = enrollment.get("user", {})
        if not user:
            return None

        enrollment_type = enrollment.get("type", "")
        role = enrollment_type.replace("Enrollment", "") if enrollment_type else ""

        return {
            "id": user.get("id"),
            "display_name": user.get("name", ""),
            "avatar_image_url": user.get("avatar_url"),
            "role": role,
        }

    def get_primary_professor(self, professors: List[Dict[str, Any]]) -> str:
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
        primary_prof = professors[0]
        return primary_prof.get("display_name", "")

    def _log_professor_results(self, professors: List[Dict[str, Any]], course_id: str, method: str) -> None:
        """
        Log the results of professor detection.

        Args:
            professors: List of found professors
            course_id: Canvas course ID
            method: Detection method used ("sections-based" or "fallback")
        """
        if professors:
            professor_names = [p.get("display_name", "Unknown") for p in professors]
            logger.info(
                f"Found {len(professors)} professors using {method} method "
                f"for course {course_id}: {professor_names}"
            )
        else:
            logger.warning(f"No professors found using {method} method for course {course_id}")
