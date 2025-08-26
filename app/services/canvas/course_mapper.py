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
            # Add Canvas-specific metadata for reference
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
