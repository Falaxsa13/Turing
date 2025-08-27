"""
Assignment mapping service for Canvas to Notion data transformation.

This module handles the conversion of Canvas assignment data into Notion-compatible
format, including proper type validation, date formatting, and metadata handling.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.utils.date_utils import format_canvas_due_date_for_notion_est
from .data_extractors import AssignmentDataExtractor
from .constants import DEFAULT_DESCRIPTION_MAX_LENGTH


class AssignmentMapper:
    """
    Service for mapping Canvas assignment data to Notion-compatible format.

    This class handles the transformation of Canvas assignment objects into the format
    expected by Notion, including proper validation, type conversion, and metadata handling.
    """

    def __init__(self):
        """Initialize the assignment mapper with data extractor."""
        self.data_extractor = AssignmentDataExtractor()

    def map_canvas_assignment_to_notion(
        self, canvas_assignment: Dict[str, Any], course_notion_id: str
    ) -> Dict[str, Any]:
        """
        Map Canvas assignment data to Notion assignment format.

        Args:
            canvas_assignment: Raw Canvas assignment data
            course_notion_id: Notion page ID of the course this assignment belongs to

        Returns:
            Dictionary formatted for Notion assignment creation

        Raises:
            ValueError: If required assignment data is missing or invalid
        """
        if not canvas_assignment:
            raise ValueError("Canvas assignment data cannot be empty")

        # Extract assignment name
        assignment_name = canvas_assignment.get("name", "Untitled Assignment")

        # Determine assignment type based on Canvas data
        assignment_type = self.data_extractor.determine_assignment_type(canvas_assignment)

        # Format due date for Notion (fix linter error by handling None properly)
        due_at = canvas_assignment.get("due_at")
        due_date = self._format_due_date(due_at) if due_at is not None else ""

        # Extract points possible
        points_possible = self.data_extractor.extract_points_possible(canvas_assignment)

        # Get Canvas assignment ID for duplicate detection
        canvas_assignment_id = self.data_extractor.extract_canvas_id(canvas_assignment)
        logger.debug(f"Mapping assignment '{assignment_name}' with Canvas ID: {canvas_assignment_id}")

        # Build Notion assignment data
        notion_assignment = {
            "title": assignment_name,
            "type": assignment_type,
            "due_date": due_date,
            "total_score": points_possible,
            # Store Canvas assignment ID in weighting field for duplicate detection
            "weighting": float(canvas_assignment_id),
            # Note: raw_score will be empty initially since students haven't submitted yet
            # Course relation will be set by the sync process
        }

        # Add Canvas-specific metadata for reference
        self._add_canvas_metadata(notion_assignment, canvas_assignment)

        # Clean up empty fields
        return {k: v for k, v in notion_assignment.items() if v is not None and v != ""}

    def _format_due_date(self, due_at_string: str) -> str:
        """
        Format Canvas due date for Notion.

        Args:
            due_at_string: Canvas due_at timestamp string (ISO format)

        Returns:
            Formatted date string for Notion (YYYY-MM-DD) or empty string if parsing fails
        """
        if not due_at_string:
            return ""

        try:
            # Canvas returns ISO format: "2025-08-29T23:59:00Z"
            # Use the EST timezone-aware function to prevent date shifting
            return format_canvas_due_date_for_notion_est(due_at_string)
        except Exception as e:
            logger.warning(f"Failed to format due date '{due_at_string}': {e}")
            return ""

    def _add_canvas_metadata(self, notion_assignment: Dict[str, Any], canvas_assignment: Dict[str, Any]) -> None:
        """
        Add Canvas-specific metadata to the Notion assignment.

        Args:
            notion_assignment: Notion assignment data to update (modified in place)
            canvas_assignment: Original Canvas assignment data
        """
        canvas_metadata = {
            "canvas_assignment_id": str(canvas_assignment.get("id", "")),
            "canvas_url": canvas_assignment.get("html_url", ""),
            "canvas_description": self._truncate_description(
                canvas_assignment.get("description"), DEFAULT_DESCRIPTION_MAX_LENGTH
            ),
        }

        # Only add non-empty metadata
        filtered_metadata = {k: v for k, v in canvas_metadata.items() if v}
        notion_assignment.update(filtered_metadata)

    @staticmethod
    def _truncate_description(description: Optional[str], max_length: int = DEFAULT_DESCRIPTION_MAX_LENGTH) -> str:
        """
        Truncate assignment description to specified length.

        Args:
            description: Canvas assignment description
            max_length: Maximum length for truncated description

        Returns:
            Truncated description or empty string if description is None/empty
        """
        if not description:
            return ""

        if len(description) <= max_length:
            return description

        # Truncate at word boundary when possible
        truncated = description[:max_length]
        last_space = truncated.rfind(" ")

        if last_space > max_length * 0.8:  # If last space is reasonably close to the end
            truncated = truncated[:last_space]

        return f"{truncated.rstrip()}..."
