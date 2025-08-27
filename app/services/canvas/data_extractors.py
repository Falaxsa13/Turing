"""
Data extraction utilities for Canvas API responses.

This module contains utility classes for extracting and parsing data from Canvas
course and assignment objects, providing clean separation of data extraction logic
from business logic.
"""

from typing import Dict, Any, Optional, Tuple, List
from loguru import logger

from .constants import EXAM_KEYWORDS, DEFAULT_POINTS


class CourseDataExtractor:
    """
    Utility class for extracting and parsing data from Canvas course objects.

    This class provides static methods for extracting specific pieces of information
    from Canvas course data, handling edge cases and providing sensible defaults.
    """

    @staticmethod
    def parse_course_name(full_course_name: str, canvas_course: Dict[str, Any]) -> Tuple[str, str]:
        """
        Parse course title and course code from Canvas course name.

        Canvas typically formats course names as: "Course Title - COURSE-CODE"
        e.g., "Computer Networking I - CS-3251-A"

        Args:
            full_course_name: Full course name from Canvas
            canvas_course: Canvas course data for fallback

        Returns:
            Tuple of (course_title, course_code)
        """
        if " - " in full_course_name:
            # Split on " - " to separate title from course code
            parts = full_course_name.split(" - ", 1)  # Split only on first occurrence
            course_title = parts[0].strip()
            course_code = parts[1].strip()
        else:
            # If no " - " separator, use full name as title and check for course_code field
            course_title = full_course_name
            course_code = canvas_course.get("course_code", "")

        # Fallback: if still no course code, try to extract from Canvas course_code field
        if not course_code:
            course_code = canvas_course.get("course_code", "")

        return course_title, course_code

    @staticmethod
    def extract_professor_name(canvas_course: Dict[str, Any], professors: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Extract instructor name using priority system.

        Priority:
        1. Professors from sections (most accurate - actual TeacherEnrollments)
        2. Embedded professors in course data
        3. Teachers from basic course data
        4. Fallback to all_instructors with TA marking

        Args:
            canvas_course: Canvas course data
            professors: Optional list of professor objects from sections

        Returns:
            Professor name or empty string if none found
        """
        course_title = canvas_course.get("name", "Unknown Course")

        # Priority 1: Use professors found through sections (actual TeacherEnrollments)
        if professors and len(professors) > 0:
            first_professor = professors[0]
            professor_name = first_professor.get("display_name", "")
            logger.info(f"Found professor via sections: {professor_name} for course {course_title}")
            return professor_name

        # Priority 2: Check if professors are embedded in course data
        embedded_professors = canvas_course.get("professors", [])
        if embedded_professors:
            first_professor = embedded_professors[0]
            professor_name = first_professor.get("display_name", "")
            logger.info(f"Found professor via embedded data: {professor_name} for course {course_title}")
            return professor_name

        # Priority 3: Check basic teachers array (from course data)
        teachers = canvas_course.get("teachers", [])
        if teachers:
            professor_name = teachers[0].get("display_name", "")
            logger.info(f"Found professor via basic teachers: {professor_name} for course {course_title}")
            return professor_name

        # Priority 4: Fall back to the old approach (all_instructors with TAs)
        all_instructors = canvas_course.get("all_instructors", [])
        if all_instructors:
            # Prefer Teachers over TAs
            main_teachers = [inst for inst in all_instructors if inst.get("role") == "Teacher"]
            if main_teachers:
                professor_name = main_teachers[0].get("display_name", "")
                logger.info(f"Found professor via enrollments (Teacher): {professor_name} for course {course_title}")
                return professor_name
            else:
                # If no main teachers, use first TA as fallback
                tas = [inst for inst in all_instructors if inst.get("role") == "Ta"]
                if tas:
                    professor_name = f"{tas[0].get('display_name', '')} (TA)"
                    logger.info(f"Using TA as fallback: {professor_name} for course {course_title}")
                    return professor_name

        logger.warning(f"No professor found for course {course_title}")
        return ""


class AssignmentDataExtractor:
    """
    Utility class for extracting and parsing data from Canvas assignment objects.

    This class provides static methods for extracting specific pieces of information
    from Canvas assignment data, with proper validation and error handling.
    """

    @staticmethod
    def determine_assignment_type(canvas_assignment: Dict[str, Any]) -> str:
        """
        Determine whether this is an Assignment or Exam based on Canvas data.

        Analyzes the assignment name and description for exam-related keywords
        to classify the assignment type.

        Args:
            canvas_assignment: Canvas assignment data

        Returns:
            "Assignment" or "Exam"
        """
        assignment_name = canvas_assignment.get("name", "").lower()
        assignment_description = canvas_assignment.get("description") or ""
        assignment_description = assignment_description.lower()

        # Look for exam/test keywords in name or description
        for keyword in EXAM_KEYWORDS:
            if keyword in assignment_name or keyword in assignment_description:
                return "Exam"

        # Default to Assignment
        return "Assignment"

    @staticmethod
    def extract_points_possible(canvas_assignment: Dict[str, Any]) -> float:
        """
        Extract and validate points possible from Canvas assignment.

        Handles None values and invalid data types gracefully, providing
        appropriate defaults and logging warnings for invalid data.

        Args:
            canvas_assignment: Canvas assignment data

        Returns:
            Points possible as float, defaults to 0.0 if None or invalid
        """
        points_possible = canvas_assignment.get("points_possible")
        if points_possible is None:
            return DEFAULT_POINTS

        try:
            return float(points_possible)
        except (ValueError, TypeError):
            assignment_name = canvas_assignment.get("name", "Unknown Assignment")
            logger.warning(
                f"Invalid points_possible value: {points_possible} for assignment '{assignment_name}', "
                f"defaulting to {DEFAULT_POINTS}"
            )
            return DEFAULT_POINTS

    @staticmethod
    def extract_canvas_id(canvas_assignment: Dict[str, Any]) -> int:
        """
        Extract Canvas assignment ID with proper validation.

        Args:
            canvas_assignment: Canvas assignment data

        Returns:
            Assignment ID as integer, defaults to 0 if invalid
        """
        assignment_id = canvas_assignment.get("id", 0)
        try:
            return int(assignment_id)
        except (ValueError, TypeError):
            assignment_name = canvas_assignment.get("name", "Unknown Assignment")
            logger.warning(f"Invalid assignment ID: {assignment_id} for assignment '{assignment_name}'")
            return 0
