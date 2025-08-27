from typing import Dict, Any
from loguru import logger
from app.utils.date_utils import determine_semester_from_date, format_date_for_notion


class CourseMapper:
    """
    Service for mapping Canvas course data to Notion-compatible format.
    """

    def map_canvas_course_to_notion(self, canvas_course: Dict, professors: list = []) -> Dict[str, Any]:
        """
        Map Canvas course data to Notion course format.

        Args:
            canvas_course: Raw Canvas course data
            professors: Optional list of professor objects from sections

        Returns:
            Dictionary formatted for Notion course creation
        """
        # Extract course name from Canvas
        full_course_name = canvas_course.get("name", "Untitled Course")

        # Parse course title and course code from Canvas course name
        course_title, course_code = self._parse_course_name(full_course_name, canvas_course)

        # Extract instructor name using priority system
        professor = self._extract_professor_name(canvas_course, professors)

        # Determine semester from start date
        start_date = canvas_course.get("start_at")
        term = determine_semester_from_date(start_date or "")

        # Format start date for Notion
        formatted_date = format_date_for_notion(start_date or "")

        # Build Notion course data
        notion_course = {
            "title": course_title,  # Clean title: "Computer Networking I"
            "course_code": course_code,  # Course code: "CS-3251-A"
            "professor": professor,
            "term": term,
            "date": formatted_date,
            # Store Canvas course ID in the contact field for reference
            "contact": f"Canvas ID: {canvas_course.get('id', '')}",
            # Add Canvas-specific metadata for reference (these won't be stored unless schema supports them)
            "canvas_course_id": str(canvas_course.get("id", "")),
            "canvas_url": canvas_course.get("html_url", ""),
            "canvas_full_name": full_course_name,  # Keep original for reference
        }

        # Clean up empty fields
        return {k: v for k, v in notion_course.items() if v}

    def _parse_course_name(self, full_course_name: str, canvas_course: Dict) -> tuple[str, str]:
        """
        Parse course title and course code from Canvas course name.

        Args:
            full_course_name: Full course name from Canvas
            canvas_course: Canvas course data for fallback

        Returns:
            Tuple of (course_title, course_code)
        """
        # Canvas typically formats as: "Course Title - COURSE-CODE"
        # e.g., "Computer Networking I - CS-3251-A"
        if " - " in full_course_name:
            # Split on " - " to separate title from course code
            parts = full_course_name.split(" - ", 1)  # Split only on first occurrence
            course_title = parts[0].strip()  # "Computer Networking I"
            course_code = parts[1].strip()  # "CS-3251-A"
        else:
            # If no " - " separator, use full name as title and check for course_code field
            course_title = full_course_name
            course_code = canvas_course.get("course_code", "")

        # Fallback: if still no course code, try to extract from Canvas course_code field
        if not course_code:
            course_code = canvas_course.get("course_code", "")

        return course_title, course_code

    def _extract_professor_name(self, canvas_course: Dict, professors: list = []) -> str:
        """
        Extract instructor name using priority system.

        Priority:
        1. Professors from sections (most accurate)
        2. Teachers from basic course data
        3. Fallback to all_instructors with TA marking

        Args:
            canvas_course: Canvas course data
            professors: Optional list of professor objects from sections

        Returns:
            Professor name or empty string
        """
        course_title = canvas_course.get("name", "Unknown Course")

        # Priority 1: Use professors found through sections (actual TeacherEnrollments)
        if professors:
            first_professor = professors[0]
            professor_name = first_professor.get("display_name", "")
            logger.info(f"Found professor via sections: {professor_name} for course {course_title}")
            return professor_name

        # Check if professors are embedded in course data
        embedded_professors = canvas_course.get("professors", [])
        if embedded_professors:
            first_professor = embedded_professors[0]
            professor_name = first_professor.get("display_name", "")
            logger.info(f"Found professor via embedded data: {professor_name} for course {course_title}")
            return professor_name

        # Priority 2: Check basic teachers array (from course data)
        teachers = canvas_course.get("teachers", [])
        if teachers:
            professor_name = teachers[0].get("display_name", "")
            logger.info(f"Found professor via basic teachers: {professor_name} for course {course_title}")
            return professor_name

        # Priority 3: Fall back to the old approach (all_instructors with TAs)
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


class AssignmentMapper:
    """
    Service for mapping Canvas assignment data to Notion-compatible format.
    """

    def map_canvas_assignment_to_notion(self, canvas_assignment: Dict, course_notion_id: str) -> Dict[str, Any]:
        """
        Map Canvas assignment data to Notion assignment format.

        Args:
            canvas_assignment: Raw Canvas assignment data
            course_notion_id: Notion page ID of the course this assignment belongs to

        Returns:
            Dictionary formatted for Notion assignment creation
        """
        # Extract assignment name
        assignment_name = canvas_assignment.get("name", "Untitled Assignment")

        # Determine assignment type based on Canvas data
        assignment_type = self._determine_assignment_type(canvas_assignment)

        # Format due date for Notion
        due_date = self._format_due_date(canvas_assignment.get("due_at"))

        # Extract points possible
        points_possible = canvas_assignment.get("points_possible", 0)
        if points_possible is None:
            points_possible = 0

        # Get Canvas assignment ID for duplicate detection
        canvas_assignment_id = canvas_assignment.get("id", 0)
        logger.debug(f"Mapping assignment '{assignment_name}' with Canvas ID: {canvas_assignment_id}")

        # Build Notion assignment data
        notion_assignment = {
            "title": assignment_name,
            "type": assignment_type,
            "due_date": due_date,
            "total_score": float(points_possible),
            # Store Canvas assignment ID in weighting field for duplicate detection
            "weighting": float(canvas_assignment_id),
            # Note: raw_score will be empty initially since students haven't submitted yet
            # Course relation will be set by the sync process
        }

        # Add Canvas-specific metadata for reference
        notion_assignment.update(
            {
                "canvas_assignment_id": str(canvas_assignment.get("id", "")),
                "canvas_url": canvas_assignment.get("html_url", ""),
                "canvas_description": (
                    canvas_assignment.get("description", "")[:100] if canvas_assignment.get("description") else ""
                ),  # Truncate description
            }
        )

        # Clean up empty fields
        return {k: v for k, v in notion_assignment.items() if v is not None and v != ""}

    def _determine_assignment_type(self, canvas_assignment: Dict) -> str:
        """
        Determine whether this is an Assignment or Exam based on Canvas data.

        Args:
            canvas_assignment: Canvas assignment data

        Returns:
            "Assignment" or "Exam"
        """
        assignment_name = canvas_assignment.get("name", "").lower()
        assignment_description = canvas_assignment.get("description") or ""
        assignment_description = assignment_description.lower()

        # Look for exam/test keywords in name or description
        exam_keywords = ["exam", "test", "midterm", "final", "quiz"]

        for keyword in exam_keywords:
            if keyword in assignment_name or keyword in assignment_description:
                return "Exam"

        # Default to Assignment
        return "Assignment"

    def _format_due_date(self, due_at_string: str) -> str:
        """
        Format Canvas due date for Notion.

        Args:
            due_at_string: Canvas due_at timestamp string

        Returns:
            Formatted date string for Notion (YYYY-MM-DD) or empty string
        """
        if not due_at_string:
            return ""

        try:
            # Canvas returns ISO format: "2024-12-15T23:59:00Z"
            # Notion expects: "2024-12-15"
            from datetime import datetime

            due_date = datetime.fromisoformat(due_at_string.replace("Z", "+00:00"))
            return due_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Failed to format due date '{due_at_string}': {e}")
            return ""
