"""
Course mapping service for Canvas to Notion data transformation.

This module handles the conversion of Canvas course data into Notion-compatible
format, including proper type validation, date formatting, and metadata handling.
"""

from typing import Dict, Any, Optional, List
from loguru import logger

from app.utils.date_utils import determine_semester_from_date, format_date_for_notion
from .data_extractors import CourseDataExtractor


class CourseMapper:
    """
    Service for mapping Canvas course data to Notion-compatible format.

    This class handles the transformation of Canvas course objects into the format
    expected by Notion, including proper validation, type conversion, and metadata handling.
    """

    def __init__(self):
        """Initialize the course mapper with data extractor."""
        self.data_extractor = CourseDataExtractor()

    def map_canvas_course_to_notion(
        self, canvas_course: Dict[str, Any], professors: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Map Canvas course data to Notion course format.

        Args:
            canvas_course: Raw Canvas course data
            professors: Optional list of professor objects from sections

        Returns:
            Dictionary formatted for Notion course creation

        Raises:
            ValueError: If required course data is missing or invalid
        """
        if not canvas_course:
            raise ValueError("Canvas course data cannot be empty")

        # Extract course name from Canvas
        full_course_name = canvas_course.get("name", "Untitled Course")

        # Parse course title and course code from Canvas course name
        course_title, course_code = self.data_extractor.parse_course_name(full_course_name, canvas_course)

        # Extract instructor name using priority system
        professor = self.data_extractor.extract_professor_name(canvas_course, professors or [])

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

        # Clean up empty fields and return
        return {k: v for k, v in notion_course.items() if v}
