"""
Enhanced assignment formatter service for creating beautiful Notion content.

This service transforms Canvas assignment data into rich, well-organized Notion pages
with proper formatting, callouts, and structured information.
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from loguru import logger

from app.schemas.canvas import CanvasAssignmentDetails, CanvasAssignmentGroup, CanvasSubmissionInfo
from app.schemas.notion import (
    NotionAssignmentFormatting,
    NotionRichTextBuilder,
    NotionBlockContent,
    NotionHeadingBlock,
    NotionParagraphBlock,
    NotionCalloutBlock,
    NotionToggleBlock,
    NotionDividerBlock,
    NotionBulletedListBlock,
    NotionNumberedListBlock,
    NotionCodeBlock,
    NotionBookmarkBlock,
)


class AssignmentFormatter:
    """
    Service for formatting Canvas assignments into beautiful Notion content.

    This service creates rich, well-structured Notion pages with:
    - Clear headings and organization
    - Important information in callouts
    - Collapsible sections for detailed info
    - Proper formatting and visual hierarchy
    - Canvas metadata and links
    """

    def __init__(self):
        """Initialize the assignment formatter."""
        self.text_builder = NotionRichTextBuilder()

    def format_assignment_for_notion(
        self,
        canvas_assignment: CanvasAssignmentDetails,
        assignment_group: Optional[CanvasAssignmentGroup] = None,
        submission_info: Optional[CanvasSubmissionInfo] = None,
        course_notion_id: str = "",
        include_rubric: bool = True,
        include_statistics: bool = True,
        include_submission_details: bool = True,
        include_assignment_group: bool = True,
    ) -> NotionAssignmentFormatting:
        """
        Format a Canvas assignment into beautiful Notion content.

        Args:
            canvas_assignment: Canvas assignment details
            assignment_group: Assignment group information
            submission_info: User's submission information
            course_notion_id: Notion course page ID for relation
            include_rubric: Whether to include rubric information
            include_statistics: Whether to include score statistics
            include_submission_details: Whether to include submission info
            include_assignment_group: Whether to include assignment group info

        Returns:
            Formatted Notion assignment with rich content blocks
        """
        try:
            # logger.info(f"Formatting assignment '{canvas_assignment.name}' for Notion")

            # Create the main content blocks
            content_blocks = self._create_assignment_content_blocks(
                canvas_assignment,
                assignment_group,
                submission_info,
                include_rubric,
                include_statistics,
                include_submission_details,
                include_assignment_group,
            )

            # Create the formatted assignment
            formatted_assignment = NotionAssignmentFormatting(
                title=canvas_assignment.name,
                type=self._determine_assignment_type(canvas_assignment),
                due_date=self._format_due_date_iso(canvas_assignment.due_at),
                total_score=canvas_assignment.points_possible or 0.0,
                raw_score=submission_info.score if submission_info else None,
                weighting=self._calculate_weighting(canvas_assignment, assignment_group),
                content_blocks=content_blocks,
                canvas_assignment_id=str(canvas_assignment.id),
                canvas_url=canvas_assignment.html_url,
                course_relation=course_notion_id,
                include_rubric=include_rubric,
                include_statistics=include_statistics,
                include_submission_details=include_submission_details,
                include_assignment_group=include_assignment_group,
            )

            return formatted_assignment

        except Exception as e:
            logger.error(f"Failed to format assignment '{canvas_assignment.name}': {e}")
            raise

    def _create_assignment_content_blocks(
        self,
        canvas_assignment: CanvasAssignmentDetails,
        assignment_group: Optional[CanvasAssignmentGroup],
        submission_info: Optional[CanvasSubmissionInfo],
        include_rubric: bool,
        include_statistics: bool,
        include_submission_details: bool,
        include_assignment_group: bool,
    ) -> List[NotionBlockContent]:
        """Create all content blocks for the assignment page."""
        blocks = []

        # Header section
        blocks.extend(self._create_header_section(canvas_assignment))

        # Quick info callout
        blocks.append(self._create_quick_info_callout(canvas_assignment))

        # Description section
        if canvas_assignment.description:
            blocks.extend(self._create_description_section(canvas_assignment))

        # Due date and timing section
        blocks.extend(self._create_timing_section(canvas_assignment))

        # Submission details section
        if include_submission_details and submission_info:
            blocks.extend(self._create_submission_section(submission_info))

        # Assignment group section
        if include_assignment_group and assignment_group:
            blocks.extend(self._create_assignment_group_section(assignment_group))

        # Grading and statistics section
        if include_statistics:
            blocks.extend(self._create_grading_section(canvas_assignment))

        # Rubric section
        if include_rubric and canvas_assignment.rubric:
            blocks.extend(self._create_rubric_section(canvas_assignment.rubric))

        # Canvas metadata section
        blocks.extend(self._create_canvas_metadata_section(canvas_assignment))

        return blocks

    def _create_header_section(self, canvas_assignment: CanvasAssignmentDetails) -> List[NotionBlockContent]:
        """Create the main header section with assignment title and type."""
        blocks = []

        # Main title
        blocks.append(self.text_builder.create_heading(canvas_assignment.name, level=1))

        # Assignment type badge
        assignment_type = self._determine_assignment_type(canvas_assignment)
        type_color = "red_background" if assignment_type == "Exam" else "blue_background"
        type_icon = "📝" if assignment_type == "Assignment" else "📚"

        blocks.append(
            self.text_builder.create_callout(f"{type_icon} {assignment_type}", icon=type_icon, color=type_color)
        )

        return blocks

    def _create_quick_info_callout(self, canvas_assignment: CanvasAssignmentDetails) -> NotionBlockContent:
        """Create a quick info callout with key assignment details."""
        info_lines = []

        # Points
        if canvas_assignment.points_possible:
            info_lines.append(f"**Points:** {canvas_assignment.points_possible}")

        # Due date
        if canvas_assignment.due_at:
            due_date = self._format_due_date(canvas_assignment.due_at)
            info_lines.append(f"**Due:** {due_date}")

        # Submission types
        if canvas_assignment.submission_types:
            submission_types = ", ".join(canvas_assignment.submission_types)
            info_lines.append(f"**Submission:** {submission_types}")

        # Attempts
        if canvas_assignment.allowed_attempts:
            attempts = (
                "Unlimited" if canvas_assignment.allowed_attempts == -1 else str(canvas_assignment.allowed_attempts)
            )
            info_lines.append(f"**Attempts:** {attempts}")

        info_text = " | ".join(info_lines)
        return self.text_builder.create_callout(info_text, icon="ℹ️", color="gray_background")

    def _create_description_section(self, canvas_assignment: CanvasAssignmentDetails) -> List[NotionBlockContent]:
        """Create the assignment description section."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Assignment Description", level=2))

        # Clean and format the description
        description = self._clean_html_description(canvas_assignment.description)
        if description:
            # Split into paragraphs and create blocks
            paragraphs = description.split("\n\n")
            for paragraph in paragraphs:
                if paragraph.strip():
                    # Split very long paragraphs to stay within Notion's 2000 character limit
                    if len(paragraph.strip()) > 2000:
                        # Split into chunks of 1900 characters (leaving room for safety)
                        chunk_size = 1900
                        chunks = [paragraph[i : i + chunk_size] for i in range(0, len(paragraph), chunk_size)]
                        for i, chunk in enumerate(chunks):
                            if i > 0:
                                chunk = "..." + chunk
                            if i < len(chunks) - 1:
                                chunk = chunk + "..."
                            blocks.append(self.text_builder.create_paragraph(chunk.strip()))
                        logger.info(
                            f"Split long description paragraph into {len(chunks)} chunks for Notion compatibility"
                        )
                    else:
                        blocks.append(self.text_builder.create_paragraph(paragraph.strip()))

        return blocks

    def _create_timing_section(self, canvas_assignment: CanvasAssignmentDetails) -> List[NotionBlockContent]:
        """Create the timing and due date section."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Timing & Due Dates", level=2))

        timing_info = []

        if canvas_assignment.due_at:
            due_date = self._format_due_date(canvas_assignment.due_at)
            timing_info.append(f"**Due Date:** {due_date}")

        if canvas_assignment.unlock_at:
            unlock_date = self._format_due_date(canvas_assignment.unlock_at)
            timing_info.append(f"**Available From:** {unlock_date}")

        if canvas_assignment.lock_at:
            lock_date = self._format_due_date(canvas_assignment.lock_at)
            timing_info.append(f"**Available Until:** {lock_date}")

        if timing_info:
            for info in timing_info:
                blocks.append(self.text_builder.create_bullet_item(info))
        else:
            blocks.append(self.text_builder.create_paragraph("No specific timing information available."))

        return blocks

    def _create_submission_section(self, submission_info: CanvasSubmissionInfo) -> List[NotionBlockContent]:
        """Create the submission information section."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Your Submission", level=2))

        submission_details = []

        if submission_info.score is not None:
            submission_details.append(f"**Score:** {submission_info.score}")

        if submission_info.grade:
            submission_details.append(f"**Grade:** {submission_info.grade}")

        if submission_info.submitted_at:
            submitted_date = self._format_due_date(submission_info.submitted_at)
            submission_details.append(f"**Submitted:** {submitted_date}")

        if submission_info.attempt:
            submission_details.append(f"**Attempt:** {submission_info.attempt}")

        if submission_info.late:
            submission_details.append("**Status:** Late submission")

        if submission_info.excused:
            submission_details.append("**Status:** Excused")

        if submission_details:
            for detail in submission_details:
                blocks.append(self.text_builder.create_bullet_item(detail))
        else:
            blocks.append(self.text_builder.create_paragraph("No submission information available."))

        return blocks

    def _create_assignment_group_section(self, assignment_group: CanvasAssignmentGroup) -> List[NotionBlockContent]:
        """Create the assignment group information section."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Assignment Group", level=2))

        group_info = []
        group_info.append(f"**Name:** {assignment_group.name}")

        if assignment_group.group_weight:
            group_info.append(f"**Weight:** {assignment_group.group_weight}%")

        if assignment_group.assignments_count:
            group_info.append(f"**Total Assignments:** {assignment_group.assignments_count}")

        for info in group_info:
            blocks.append(self.text_builder.create_bullet_item(info))

        return blocks

    def _create_grading_section(self, canvas_assignment: CanvasAssignmentDetails) -> List[NotionBlockContent]:
        """Create the grading and statistics section."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Grading & Statistics", level=2))

        grading_info = []

        if canvas_assignment.grading_type:
            grading_info.append(f"**Grading Type:** {canvas_assignment.grading_type}")

        if canvas_assignment.points_possible:
            grading_info.append(f"**Points Possible:** {canvas_assignment.points_possible}")

        if canvas_assignment.score_statistics:
            stats = canvas_assignment.score_statistics
            if stats.get("min") is not None:
                grading_info.append(f"**Class Range:** {stats.get('min')} - {stats.get('max')}")
            if stats.get("mean"):
                grading_info.append(f"**Class Average:** {stats.get('mean'):.1f}")

        if grading_info:
            for info in grading_info:
                blocks.append(self.text_builder.create_bullet_item(info))
        else:
            blocks.append(self.text_builder.create_paragraph("No grading information available."))

        return blocks

    def _create_rubric_section(self, rubric: List[Dict[str, Any]]) -> List[NotionBlockContent]:
        """Create the rubric section with collapsible criteria."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Rubric", level=2))

        for i, criterion in enumerate(rubric, 1):
            criterion_name = criterion.get("description", f"Criterion {i}")
            criterion_points = criterion.get("points", 0)

            # Create toggle for each rubric criterion
            criterion_text = f"{criterion_name} ({criterion_points} points)"

            # Get rating levels
            ratings = criterion.get("ratings", [])
            rating_blocks = []

            for rating in ratings:
                rating_description = rating.get("description", "")
                rating_points = rating.get("points", 0)
                rating_text = f"{rating_description} - {rating_points} points"
                rating_blocks.append(self.text_builder.create_bullet_item(rating_text))

            if rating_blocks:
                blocks.append(NotionToggleBlock.create_toggle(criterion_text, rating_blocks))
            else:
                blocks.append(self.text_builder.create_paragraph(criterion_text))

        return blocks

    def _create_canvas_metadata_section(self, canvas_assignment: CanvasAssignmentDetails) -> List[NotionBlockContent]:
        """Create the Canvas metadata and links section."""
        blocks = []

        blocks.append(self.text_builder.create_heading("Canvas Information", level=2))

        metadata_items = []

        if canvas_assignment.html_url:
            metadata_items.append(f"**Canvas URL:** [View in Canvas]({canvas_assignment.html_url})")

        if canvas_assignment.workflow_state:
            status_emoji = "✅" if canvas_assignment.workflow_state == "published" else "⏳"
            metadata_items.append(f"**Status:** {status_emoji} {canvas_assignment.workflow_state.title()}")

        if canvas_assignment.created_at:
            created_date = self._format_due_date(canvas_assignment.created_at)
            metadata_items.append(f"**Created:** {created_date}")

        if canvas_assignment.updated_at:
            updated_date = self._format_due_date(canvas_assignment.updated_at)
            metadata_items.append(f"**Last Updated:** {updated_date}")

        for item in metadata_items:
            blocks.append(self.text_builder.create_bullet_item(item))

        # Add Canvas link as bookmark
        if canvas_assignment.html_url:
            blocks.append(self.text_builder.create_bookmark(canvas_assignment.html_url))

        return blocks

    def _determine_assignment_type(self, canvas_assignment: CanvasAssignmentDetails) -> str:
        """Determine if this is an Assignment or Exam."""
        if canvas_assignment.is_quiz_assignment:
            return "Exam"

        # Check for exam keywords in name and description
        exam_keywords = ["exam", "test", "midterm", "final", "quiz", "assessment"]
        assignment_text = f"{canvas_assignment.name} {canvas_assignment.description or ''}".lower()

        for keyword in exam_keywords:
            if keyword in assignment_text:
                return "Exam"

        return "Assignment"

    def _format_due_date(self, date: Union[str, datetime, None]) -> str:
        """Format a datetime object for display."""
        if not date:
            return "Not specified"

        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            except:
                return date

        return date.strftime("%B %d, %Y at %I:%M %p")

    def _format_due_date_iso(self, date: Union[str, datetime, None]) -> Optional[str]:
        """Format a datetime object for Notion's internal use (ISO 8601)."""
        if not date:
            return None

        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            except:
                return None

        return date.isoformat()

    def _calculate_weighting(
        self, canvas_assignment: CanvasAssignmentDetails, assignment_group: Optional[CanvasAssignmentGroup]
    ) -> float:
        """
        Store Canvas assignment ID as weighting for duplicate detection.

        This is a workaround to maintain compatibility with existing duplicate detection logic
        that looks for Canvas assignment IDs in the weighting field.
        """
        # Store Canvas assignment ID in weighting field for duplicate detection
        # This ensures compatibility with get_existing_assignments() method
        return float(canvas_assignment.id)

    def _clean_html_description(self, html_description: Optional[str]) -> str:
        """Clean HTML description and convert to plain text."""
        if not html_description:
            return ""

        import re

        # HTML entity replacements
        html_entities = {
            r"&nbsp;": " ",
            r"&amp;": "&",
            r"&lt;": "<",
            r"&gt;": ">",
            r"&quot;": '"',
        }

        # Remove HTML tags and clean entities
        clean_text = re.sub(r"<[^>]+>", "", html_description)
        for entity, replacement in html_entities.items():
            clean_text = re.sub(entity, replacement, clean_text)

        # Clean up whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        # Ensure Notion compatibility (2000 character limit)
        return self._truncate_for_notion(clean_text, len(html_description))

    def _truncate_for_notion(self, text: str, original_length: int) -> str:
        """Truncate text for Notion's 2000 character limit."""
        if len(text) <= 2000:
            return text

        truncated = text[:1997] + "..."
        # logger.info(
        #     f"Description truncated from {original_length} to {len(truncated)} characters for Notion compatibility"
        # )
        return truncated
