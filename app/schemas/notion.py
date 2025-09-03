from pydantic import BaseModel, Field, computed_field
from typing import List, Dict, Any, Optional, Union, Sequence
from datetime import datetime
from enum import Enum


class NotionBlockType(str, Enum):
    """Notion block types for rich content formatting."""

    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"
    TOGGLE = "toggle"
    QUOTE = "quote"
    DIVIDER = "divider"
    CALLOUT = "callout"
    CODE = "code"
    BOOKMARK = "bookmark"
    EQUATION = "equation"
    TABLE_OF_CONTENTS = "table_of_contents"
    COLUMN_LIST = "column_list"
    COLUMN = "column"


class NotionRichText(BaseModel):
    """Notion rich text object for formatted text content."""

    type: str = "text"
    text: Dict[str, Union[str, Dict[str, str]]] = Field(description="Text content with href")
    annotations: Optional[Dict[str, Union[bool, str]]] = Field(
        description="Text formatting (bold, italic, etc.) and color"
    )
    href: Optional[str] = Field(description="URL link")


class NotionBlockContent(BaseModel):
    """Base Notion block content."""

    object: str = "block"


class NotionParagraphBlock(NotionBlockContent):
    """Notion paragraph block."""

    type: NotionBlockType = NotionBlockType.PARAGRAPH
    paragraph: Dict[str, List[NotionRichText]] = Field(description="Paragraph content")


class NotionHeadingBlock(NotionBlockContent):
    """Notion heading block."""

    heading_1: Optional[Dict[str, List[NotionRichText]]] = Field(default=None, description="Heading 1 content")
    heading_2: Optional[Dict[str, List[NotionRichText]]] = Field(default=None, description="Heading 2 content")
    heading_3: Optional[Dict[str, List[NotionRichText]]] = Field(default=None, description="Heading 3 content")

    @computed_field
    @property
    def type(self) -> NotionBlockType:
        """Compute the type based on which heading field is provided."""
        if self.heading_1:
            return NotionBlockType.HEADING_1
        elif self.heading_2:
            return NotionBlockType.HEADING_2
        elif self.heading_3:
            return NotionBlockType.HEADING_3
        else:
            # Default to heading_1 if none specified
            return NotionBlockType.HEADING_1


class NotionCalloutBlock(NotionBlockContent):
    """Notion callout block for highlighting important information."""

    type: NotionBlockType = NotionBlockType.CALLOUT
    callout: Dict[str, Any] = Field(description="Callout content with icon and text")


class NotionToggleBlock(NotionBlockContent):
    """Notion toggle block for collapsible content."""

    type: NotionBlockType = NotionBlockType.TOGGLE
    toggle: Dict[str, Any] = Field(description="Toggle content with rich_text and optional children")

    @staticmethod
    def create_toggle(text: str, children: Optional[List[Any]] = None) -> "NotionToggleBlock":
        """Create a Notion toggle block with proper structure."""
        toggle_data = {"rich_text": [NotionRichTextBuilder.create_text(text)]}
        if children:
            toggle_data["children"] = children
        return NotionToggleBlock(toggle=toggle_data)


class NotionDividerBlock(NotionBlockContent):
    """Notion divider block."""

    type: NotionBlockType = NotionBlockType.DIVIDER
    divider: Dict[str, Any] = Field(description="Divider content")


class NotionBulletedListBlock(NotionBlockContent):
    """Notion bulleted list item."""

    type: NotionBlockType = NotionBlockType.BULLETED_LIST_ITEM
    bulleted_list_item: Dict[str, List[NotionRichText]] = Field(description="List item content")


class NotionNumberedListBlock(NotionBlockContent):
    """Notion numbered list item."""

    type: NotionBlockType = NotionBlockType.NUMBERED_LIST_ITEM
    numbered_list_item: Dict[str, List[NotionRichText]] = Field(description="List item content")


class NotionCodeBlock(NotionBlockContent):
    """Notion code block."""

    type: NotionBlockType = NotionBlockType.CODE
    code: Dict[str, Any] = Field(description="Code content with language")


class NotionBookmarkBlock(NotionBlockContent):
    """Notion bookmark block for URLs."""

    type: NotionBlockType = NotionBlockType.BOOKMARK
    bookmark: Dict[str, str] = Field(description="Bookmark URL")


class NotionAssignmentFormatting(BaseModel):
    """Enhanced Notion formatting for assignments with rich content."""

    # Basic assignment properties (for database entry)
    title: str = Field(description="Assignment title")
    type: str = Field(description="Assignment type (Assignment/Exam)")
    due_date: Optional[str] = Field(description="Due date in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)")
    total_score: float = Field(description="Total points possible")
    raw_score: Optional[float] = Field(description="Points earned")
    weighting: float = Field(description="Canvas assignment ID stored as float for duplicate detection")

    # Rich content blocks for the assignment page
    content_blocks: Sequence[NotionBlockContent] = Field(description="Rich content blocks for the assignment page")

    # Canvas metadata for reference
    canvas_assignment_id: str = Field(description="Canvas assignment ID")
    canvas_url: Optional[str] = Field(description="Canvas assignment URL")
    course_relation: str = Field(description="Notion course page ID")

    # Additional formatting options
    include_rubric: bool = Field(default=True, description="Whether to include rubric information")
    include_statistics: bool = Field(default=True, description="Whether to include score statistics")
    include_submission_details: bool = Field(default=True, description="Whether to include submission info")
    include_assignment_group: bool = Field(default=True, description="Whether to include assignment group info")


class NotionRichTextBuilder:
    """Utility class for building Notion rich text objects."""

    @staticmethod
    def create_text(
        text: str,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        strikethrough: bool = False,
        code: bool = False,
        color: str = "default",
        href: Optional[str] = None,
    ) -> NotionRichText:
        """Create a Notion rich text object with specified formatting."""
        # Truncate text if it's too long for Notion (2000 character limit)
        if len(text) > 2000:
            text = text[:1997] + "..."

        return NotionRichText(
            text={"content": text, "link": {"url": href}} if href else {"content": text},
            annotations={
                "bold": bold,
                "italic": italic,
                "underline": underline,
                "strikethrough": strikethrough,
                "code": code,
                "color": color,
            },
            href=href,
        )

    @staticmethod
    def create_truncated_text(
        text: str,
        max_length: int = 2000,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        strikethrough: bool = False,
        code: bool = False,
        color: str = "default",
        href: Optional[str] = None,
    ) -> NotionRichText:
        """Create a Notion rich text object with custom truncation."""
        if len(text) > max_length:
            text = text[: max_length - 3] + "..."

        return NotionRichText(
            text={"content": text, "link": {"url": href}} if href else {"content": text},
            annotations={
                "bold": bold,
                "italic": italic,
                "underline": underline,
                "strikethrough": strikethrough,
                "code": code,
                "color": color,
            },
            href=href,
        )

    @staticmethod
    def create_heading(text: str, level: int = 1) -> NotionHeadingBlock:
        """Create a Notion heading block."""
        rich_text = [NotionRichTextBuilder.create_text(text, bold=True)]

        if level == 1:
            return NotionHeadingBlock(heading_1={"rich_text": rich_text})
        elif level == 2:
            return NotionHeadingBlock(heading_2={"rich_text": rich_text})
        else:
            return NotionHeadingBlock(heading_3={"rich_text": rich_text})

    @staticmethod
    def create_paragraph(text: str, bold: bool = False, italic: bool = False) -> NotionParagraphBlock:
        """Create a Notion paragraph block."""
        rich_text = [NotionRichTextBuilder.create_text(text, bold=bold, italic=italic)]
        return NotionParagraphBlock(paragraph={"rich_text": rich_text})

    @staticmethod
    def create_callout(text: str, icon: str = "💡", color: str = "blue_background") -> NotionCalloutBlock:
        """Create a Notion callout block."""
        rich_text = [NotionRichTextBuilder.create_text(text)]
        return NotionCalloutBlock(
            callout={"rich_text": rich_text, "icon": {"type": "emoji", "emoji": icon}, "color": color}
        )

    @staticmethod
    def create_bullet_item(text: str) -> NotionBulletedListBlock:
        """Create a Notion bulleted list item."""
        rich_text = [NotionRichTextBuilder.create_text(text)]
        return NotionBulletedListBlock(bulleted_list_item={"rich_text": rich_text})

    @staticmethod
    def create_numbered_item(text: str) -> NotionNumberedListBlock:
        """Create a Notion numbered list item."""
        rich_text = [NotionRichTextBuilder.create_text(text)]
        return NotionNumberedListBlock(numbered_list_item={"rich_text": rich_text})

    @staticmethod
    def create_divider() -> NotionDividerBlock:
        """Create a Notion divider block."""
        return NotionDividerBlock(divider={})

    @staticmethod
    def create_bookmark(url: str) -> NotionBookmarkBlock:
        """Create a Notion bookmark block."""
        return NotionBookmarkBlock(bookmark={"url": url})


class NotionEntryRequest(BaseModel):
    notion_token: str = Field(description="Notion token")
    notion_parent_page_id: str = Field(description="Notion parent page ID")
    entry_data: Dict[str, Any] = Field(description="Entry data")


# Response Models
class NotionDatabaseInfo(BaseModel):
    id: str = Field(description="Database ID")
    name: str = Field(description="Database name")
    found: bool = Field(description="Whether the database was found")
    properties_count: int = Field(description="Number of properties in the database")


class NotionWorkspaceResponse(BaseModel):
    success: bool = Field(description="Whether the workspace was found")
    parent_page_id: str = Field(description="Notion parent page ID")
    databases_found: int = Field(description="Number of databases found")
    databases: List[NotionDatabaseInfo] = Field(description="List of databases")
    message: str = Field(description="Message")


class NotionSchemaResponse(BaseModel):
    success: bool = Field(description="Whether the workspace was found")
    databases_found: int = Field(description="Number of databases found")
    schemas: Dict[str, Any] = Field(description="List of databases")
    message: str = Field(description="Message")


class NotionEntryResponse(BaseModel):
    success: bool = Field(description="Whether the entry was added")
    message: str = Field(description="Message")
    page_id: str = Field(description="Page ID")
    note: str = Field(description="Note")
