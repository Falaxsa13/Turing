"""
Enhanced Notion assignment manager for creating rich assignment pages.

This service creates beautiful, well-formatted Notion assignment pages with:
- Rich content blocks and formatting
- Canvas metadata and links
- Assignment details and descriptions
- Submission information and grades
- Rubrics and statistics
- Beautiful visual hierarchy
"""

from typing import List, Dict, Any, Optional, Union, Sequence
from loguru import logger

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from app.schemas.notion import (
    NotionAssignmentFormatting,
    NotionBlockContent,
    NotionRichTextBuilder,
    NotionParagraphBlock,
    NotionHeadingBlock,
    NotionCalloutBlock,
    NotionToggleBlock,
    NotionDividerBlock,
    NotionBulletedListBlock,
    NotionNumberedListBlock,
    NotionCodeBlock,
    NotionBookmarkBlock,
)
from app.schemas.canvas import CanvasAssignmentDetails

# Type alias for content block types
ContentBlockType = Union[
    NotionParagraphBlock,
    NotionHeadingBlock,
    NotionCalloutBlock,
    NotionToggleBlock,
    NotionDividerBlock,
    NotionBulletedListBlock,
    NotionNumberedListBlock,
    NotionCodeBlock,
    NotionBookmarkBlock,
]


class EnhancedAssignmentManager:
    """
    Enhanced Notion assignment manager for rich content creation.

    This service handles the creation of beautiful assignment pages in Notion
    with proper formatting, rich content blocks, and organized information.
    """

    def __init__(self, notion_token: str, parent_page_id: str):
        """
        Initialize the enhanced assignment manager.

        Args:
            notion_token: Notion integration token
            parent_page_id: Parent page ID where assignments will be created
        """
        self.notion_token = notion_token
        self.client = AsyncClient(auth=notion_token)
        self.parent_page_id = parent_page_id
        self.text_builder = NotionRichTextBuilder()

    async def create_rich_assignment_page(
        self, assignment_formatting: NotionAssignmentFormatting, assignments_database_id: str
    ) -> Optional[str]:
        """
        Create a rich assignment page in Notion with beautiful formatting.

        Args:
            assignment_formatting: Formatted assignment data with content blocks
            assignments_database_id: ID of the assignments database

        Returns:
            Created page ID or None if failed
        """
        try:
            # logger.info(f"Creating rich assignment page for '{assignment_formatting.title}'")

            # Create the database entry with rich content directly embedded
            database_entry_id = await self._create_database_entry_with_content(
                assignment_formatting, assignments_database_id
            )

            if database_entry_id:
                return database_entry_id
            else:
                logger.error(f"Failed to create database entry for assignment: {assignment_formatting.title}")
                return None

        except Exception as e:
            logger.error(f"Failed to create rich assignment page: {e}")
            return None

    async def _create_database_entry(
        self, assignment_formatting: NotionAssignmentFormatting, database_id: str
    ) -> Optional[str]:
        """Create a basic database entry for the assignment."""
        try:
            properties = await self._build_database_properties(assignment_formatting)

            # Create the database entry
            response = await self.client.pages.create(parent={"database_id": database_id}, properties=properties)
            return response["id"]

        except APIResponseError as e:
            logger.error(f"Notion API error creating database entry: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating database entry: {e}")
            return None

    async def _create_database_entry_with_content(
        self, assignment_formatting: NotionAssignmentFormatting, database_id: str
    ) -> Optional[str]:
        """Create a database entry with rich content directly embedded."""
        try:
            properties = await self._build_database_properties(assignment_formatting)

            # Convert content blocks to Notion format
            notion_blocks = self._convert_content_blocks_to_notion(assignment_formatting.content_blocks)

            # Create the database entry with embedded content
            response = await self.client.pages.create(
                parent={"database_id": database_id}, properties=properties, children=notion_blocks
            )

            return response["id"]

        except APIResponseError as e:
            logger.error(f"Notion API error creating assignment '{assignment_formatting.title}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating assignment '{assignment_formatting.title}': {e}")
            return None

    async def _build_database_properties(self, assignment_formatting: NotionAssignmentFormatting) -> Dict:
        """Build database properties from assignment data and schema."""
        try:
            # Get the actual database schema to build properties correctly
            from app.utils.notion_helper import NotionWorkspaceManager

            # Create a temporary manager to get the schema
            temp_manager = NotionWorkspaceManager(self.notion_token, self.parent_page_id)
            schema = await temp_manager.get_database_schema("Assignments/Exams")

            if not schema:
                logger.warning("Could not retrieve database schema, using fallback properties")
                return {"Name": {"title": [{"text": {"content": assignment_formatting.title}}]}}

            # Build properties based on actual schema
            properties = self._build_properties_from_schema(schema, assignment_formatting)

            # Ensure we have at least a title
            if not properties:
                title_prop = self._find_title_property(schema)
                if title_prop:
                    properties[title_prop] = {"title": [{"text": {"content": assignment_formatting.title}}]}

            return properties

        except Exception as e:
            logger.warning(f"Failed to build database properties: {e}")
            return {"Name": {"title": [{"text": {"content": assignment_formatting.title}}]}}

    def _find_title_property(self, schema: Dict) -> Optional[str]:
        """Find the title property in the database schema."""
        for prop_name, prop_info in schema.get("properties", {}).items():
            if prop_info.get("type") == "title":
                return prop_name
        return None

    def _build_properties_from_schema(self, schema: Dict, data: NotionAssignmentFormatting) -> Dict:
        """Helper to build Notion properties based on database schema and assignment data."""
        properties = {}

        # Convert assignment formatting to a dictionary for property mapping
        assignment_data = {
            "title": data.title,
            "type": data.type,
            "total_score": data.total_score,
            "raw_score": data.raw_score,
            "weighting": data.weighting,
            "due_date": data.due_date,
            "course": data.course_relation,
        }

        for prop_name, prop_info in schema.get("properties", {}).items():
            prop_type = prop_info.get("type")

            # Special handling for title properties
            if prop_type == "title":
                title_value = assignment_data.get("title", "")
                if title_value:
                    properties[prop_name] = {"title": [{"text": {"content": str(title_value)}}]}
                    logger.debug(f"Mapped title property '{prop_name}' to '{title_value}'")
                continue

            # Handle other properties with flexible key matching
            data_key = prop_name.lower().replace(" ", "_")

            # Try multiple key variations to find the data
            possible_keys = [
                data_key,  # "course_code" for "Course Code"
                prop_name,  # "Course Code" exactly
                prop_name.lower(),  # "course code"
            ]

            value = None
            for key in possible_keys:
                if key in assignment_data:
                    value = assignment_data[key]
                    break

            if value is None:
                continue

            # Build property based on type
            if prop_type == "rich_text":
                if value:  # Only add if value exists
                    properties[prop_name] = {"rich_text": [{"text": {"content": str(value)}}]}
            elif prop_type == "number":
                if value is not None:  # Only add if value exists and is not None
                    try:
                        properties[prop_name] = {"number": float(value)}
                        # Store Canvas assignment ID in weighting field for duplicate detection
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid number value for {prop_name}: {value}")
            elif prop_type == "select":
                if value:  # Only add if value exists
                    properties[prop_name] = {"select": {"name": str(value)}}
            elif prop_type == "multi_select":
                if value:  # Only add if value exists
                    if isinstance(value, list):
                        properties[prop_name] = {"multi_select": [{"name": str(v)} for v in value]}
                    else:
                        properties[prop_name] = {"multi_select": [{"name": str(value)}]}
            elif prop_type == "date":
                if value:  # Only add if value exists and is not empty
                    properties[prop_name] = {"date": {"start": str(value)}}
            elif prop_type == "checkbox":
                if value is not None:  # Only add if value exists
                    properties[prop_name] = {"checkbox": bool(value)}
            elif prop_type == "url":
                if value:  # Only add if value exists
                    properties[prop_name] = {"url": str(value)}
            elif prop_type == "email":
                if value:  # Only add if value exists
                    properties[prop_name] = {"email": str(value)}
            elif prop_type == "phone_number":
                if value:  # Only add if value exists
                    properties[prop_name] = {"phone_number": str(value)}
            elif prop_type == "relation":
                if value:  # Only add if value exists
                    # Handle relation properties properly
                    if isinstance(value, list):
                        if all(isinstance(v, dict) and "id" in v for v in value):
                            properties[prop_name] = {"relation": value}
                        else:
                            properties[prop_name] = {"relation": [{"id": str(v)} for v in value]}
                    elif isinstance(value, dict) and "id" in value:
                        properties[prop_name] = {"relation": [value]}
                    elif isinstance(value, str):
                        properties[prop_name] = {"relation": [{"id": value}]}
                    else:
                        properties[prop_name] = {"relation": [{"id": str(value)}]}

        return properties

    async def _create_content_page(
        self, assignment_formatting: NotionAssignmentFormatting, database_entry_id: str
    ) -> Optional[str]:
        """Create a rich content page for the assignment."""
        try:
            # Convert content blocks to Notion format
            notion_blocks = self._convert_content_blocks_to_notion(assignment_formatting.content_blocks)

            # Create the page with rich content
            response = await self.client.pages.create(
                parent={"page_id": database_entry_id},
                properties={"title": {"title": [{"text": {"content": f"📋 {assignment_formatting.title} - Details"}}]}},
                children=notion_blocks,
            )

            return response["id"]

        except APIResponseError as e:
            logger.error(f"Notion API error creating content page: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating content page: {e}")
            return None

    def _convert_content_blocks_to_notion(self, content_blocks: Sequence[NotionBlockContent]) -> List[Dict[str, Any]]:
        """Convert our content blocks to Notion API format."""
        notion_blocks = []

        for block in content_blocks:
            try:
                notion_block = self._convert_single_block(block)
                if notion_block:
                    notion_blocks.append(notion_block)
            except Exception as e:
                logger.warning(f"Failed to convert block {getattr(block, 'type', 'unknown')}: {e}")
                continue

        return notion_blocks

    def _convert_single_block(self, block: NotionBlockContent) -> Optional[Dict[str, Any]]:
        """Convert a single content block to Notion format."""

        if isinstance(block, NotionParagraphBlock):
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": self._convert_rich_text_list(block.paragraph["rich_text"])},
            }

        elif isinstance(block, NotionHeadingBlock):
            if block.heading_1:
                return {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": self._convert_rich_text_list(block.heading_1["rich_text"])},
                }
            elif block.heading_2:
                return {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": self._convert_rich_text_list(block.heading_2["rich_text"])},
                }
            elif block.heading_3:
                return {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": self._convert_rich_text_list(block.heading_3["rich_text"])},
                }

        elif isinstance(block, NotionCalloutBlock):
            return {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": self._convert_rich_text_list(block.callout["rich_text"]),
                    "icon": block.callout["icon"],
                    "color": block.callout["color"],
                },
            }

        elif isinstance(block, NotionToggleBlock):
            toggle_data = {
                "object": "block",
                "type": "toggle",
                "toggle": {"rich_text": self._convert_rich_text_list(block.toggle["rich_text"])},
            }

            # Add children if available
            if block.toggle.get("children"):
                children = []
                for child in block.toggle["children"]:
                    child_block = self._convert_single_block(child)
                    if child_block:
                        children.append(child_block)
                if children:
                    toggle_data["toggle"]["children"] = children

            return toggle_data

        elif isinstance(block, NotionDividerBlock):
            return {"object": "block", "type": "divider", "divider": {}}

        elif isinstance(block, NotionBulletedListBlock):
            return {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": self._convert_rich_text_list(block.bulleted_list_item["rich_text"])
                },
            }

        elif isinstance(block, NotionNumberedListBlock):
            return {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": self._convert_rich_text_list(block.numbered_list_item["rich_text"])
                },
            }

        elif isinstance(block, NotionBookmarkBlock):
            return {"object": "block", "type": "bookmark", "bookmark": {"url": block.bookmark["url"]}}

        elif isinstance(block, NotionCodeBlock):
            return {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": self._convert_rich_text_list(block.code.get("rich_text", [])),
                    "language": block.code.get("language", "plain_text"),
                },
            }

        else:
            block_type = getattr(block, "type", None)
            type_value = getattr(block_type, "value", "unknown") if block_type else "unknown"
            logger.warning(f"Unsupported block type: {type_value}")
            return None

    def _convert_rich_text_list(self, rich_text_list: List[Any]) -> List[Dict[str, Any]]:
        """Convert rich text objects to Notion format."""
        notion_rich_text = []

        for rich_text in rich_text_list:
            try:
                notion_text = {"type": "text", "text": {"content": rich_text.text["content"]}}

                # Add annotations if available
                if hasattr(rich_text, "annotations") and rich_text.annotations:
                    notion_text["annotations"] = rich_text.annotations

                # Add link if available
                if hasattr(rich_text, "href") and rich_text.href:
                    notion_text["text"]["link"] = {"url": rich_text.href}

                notion_rich_text.append(notion_text)

            except Exception as e:
                logger.warning(f"Failed to convert rich text: {e}")
                continue

        return notion_rich_text

    async def update_assignment_page(self, page_id: str, assignment_formatting: NotionAssignmentFormatting) -> bool:
        """
        Update an existing assignment page with new content.

        Args:
            page_id: ID of the page to update
            assignment_formatting: New formatted assignment data

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Updating assignment page: {page_id}")

            # Convert content blocks to Notion format
            notion_blocks = self._convert_content_blocks_to_notion(assignment_formatting.content_blocks)

            # Update the page content
            await self.client.blocks.children.append(block_id=page_id, children=notion_blocks)

            logger.info(f"Successfully updated assignment page: {page_id}")
            return True

        except APIResponseError as e:
            logger.error(f"Notion API error updating page: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating page: {e}")
            return False

    async def get_assignment_page_content(self, page_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get the content blocks from an assignment page.

        Args:
            page_id: ID of the page to retrieve

        Returns:
            List of content blocks or None if failed
        """
        try:
            response = await self.client.blocks.children.list(block_id=page_id)
            return response.get("results", [])

        except APIResponseError as e:
            logger.error(f"Notion API error retrieving page content: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving page content: {e}")
            return None

    async def delete_assignment_page(self, page_id: str) -> bool:
        """
        Delete an assignment page.

        Args:
            page_id: ID of the page to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.client.pages.update(page_id=page_id, archived=True)

            logger.info(f"Successfully archived assignment page: {page_id}")
            return True

        except APIResponseError as e:
            logger.error(f"Notion API error deleting page: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting page: {e}")
            return False
