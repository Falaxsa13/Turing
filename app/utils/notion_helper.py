"""
Notion Helper Utilities for working with existing Canvas sync databases.
Works with user's existing 3 databases: Courses, Notes, Assignments/Exams
"""

from notion_client import AsyncClient
from typing import List, Dict, Optional, Any
from loguru import logger
import asyncio
from app.schemas.sync import NotionCourseInfo, NotionAssignmentInfo


class NotionWorkspaceManager:
    """Manages existing Notion databases under a parent page"""

    def __init__(self, notion_token: str, parent_page_id: str):
        self.client = AsyncClient(auth=notion_token)
        self.parent_page_id = parent_page_id
        self._database_cache = {}

    async def list_all_databases(self) -> List[Dict]:
        """List all databases in the workspace (not just under parent page)"""
        try:
            # Search for all databases in the workspace
            response = await self.client.search(filter={"property": "object", "value": "database"})

            databases = []
            for result in response.get("results", []):
                if result["object"] == "database":
                    databases.append(
                        {
                            "id": result["id"],
                            "title": result.get("title", [{}])[0].get("plain_text", "Untitled"),
                            "url": result["url"],
                            "created_time": result["created_time"],
                            "last_edited_time": result["last_edited_time"],
                        }
                    )

            return databases

        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            return []

    async def list_databases_in_parent(self) -> List[Dict]:
        """List all databases under the parent page"""
        try:
            # Query for databases that are children of the parent page
            response = await self.client.search(
                filter={"property": "object", "value": "database"},
                parent={"type": "page_id", "page_id": self.parent_page_id},
            )

            databases = []
            for result in response.get("results", []):
                if result["object"] == "database":
                    databases.append(
                        {
                            "id": result["id"],
                            "title": result.get("title", [{}])[0].get("plain_text", "Untitled"),
                            "url": result["url"],
                            "created_time": result["created_time"],
                            "last_edited_time": result["last_edited_time"],
                        }
                    )

            return databases

        except Exception as e:
            logger.error(f"Failed to list databases: {e}")
            return []

    async def get_database_by_name(self, name: str) -> Optional[str]:
        """Get database ID by name from your existing databases (searches globally)"""
        try:
            if name in self._database_cache:
                return self._database_cache[name]

            # Try finding in all workspace databases first
            databases = await self.list_all_databases()
            for db in databases:
                if db["title"].lower() == name.lower():
                    self._database_cache[name] = db["id"]
                    # logger.info(f"Found existing database: {name} -> {db['id']}")
                    return db["id"]

            logger.warning(f"Database '{name}' not found in workspace")
            return None

        except Exception as e:
            logger.error(f"Failed to get database '{name}': {e}")
            return None

    async def get_database_schema(self, database_name: str) -> Optional[Dict]:
        """Retrieve the full schema/properties of a database"""
        try:
            database_id = await self.get_database_by_name(database_name)
            if not database_id:
                logger.error(f"Database '{database_name}' not found")
                return None

            # Get database details including properties
            response = await self.client.databases.retrieve(database_id=database_id)

            # Extract properties information
            properties = {}
            for prop_name, prop_data in response.get("properties", {}).items():
                prop_type = prop_data.get("type", "unknown")

                # Extract additional details based on property type
                prop_info = {
                    "type": prop_type,
                    "id": prop_data.get("id"),
                }

                # Add type-specific information
                if prop_type == "select":
                    prop_info["options"] = [opt.get("name") for opt in prop_data.get("select", {}).get("options", [])]
                elif prop_type == "multi_select":
                    prop_info["options"] = [
                        opt.get("name") for opt in prop_data.get("multi_select", {}).get("options", [])
                    ]
                elif prop_type == "relation":
                    prop_info["database_id"] = prop_data.get("relation", {}).get("database_id")
                elif prop_type == "formula":
                    prop_info["expression"] = prop_data.get("formula", {}).get("expression")
                elif prop_type == "rollup":
                    prop_info["relation_property_name"] = prop_data.get("rollup", {}).get("relation_property_name")
                    prop_info["rollup_property_name"] = prop_data.get("rollup", {}).get("rollup_property_name")

                properties[prop_name] = prop_info

            return {
                "database_id": database_id,
                "title": response.get("title", [{}])[0].get("plain_text", "Untitled"),
                "properties": properties,
                "url": response.get("url"),
                "created_time": response.get("created_time"),
                "last_edited_time": response.get("last_edited_time"),
            }

        except Exception as e:
            logger.error(f"Failed to get schema for '{database_name}': {e}")
            return None

    async def get_all_database_schemas(self) -> Dict[str, Dict]:
        """Get schemas for all 3 required databases"""
        required_databases = ["Courses", "Notes", "Assignments/Exams"]
        schemas = {}

        for db_name in required_databases:
            schema = await self.get_database_schema(db_name)
            if schema:
                schemas[db_name] = schema
            else:
                logger.warning(f"Could not retrieve schema for '{db_name}'")

        return schemas

    def _build_properties_from_schema(self, schema: Dict, data: Dict[str, Any]) -> Dict:
        """Helper to build Notion properties based on database schema and input data"""
        properties = {}

        for prop_name, prop_info in schema.get("properties", {}).items():
            prop_type = prop_info.get("type")

            # Special handling for title properties - they need the course title
            if prop_type == "title":
                # For title fields, always try to use the 'title' field from Canvas data
                title_value = data.get("title", "")
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
                if key in data:
                    value = data[key]
                    break

            if value is None:
                continue

            # Build property based on type
            if prop_type == "rich_text":
                properties[prop_name] = {"rich_text": [{"text": {"content": str(value)}}]}
            elif prop_type == "number":
                try:
                    properties[prop_name] = {"number": float(value)}
                except (ValueError, TypeError):
                    logger.warning(f"Invalid number value for {prop_name}: {value}")
            elif prop_type == "select":
                properties[prop_name] = {"select": {"name": str(value)}}
            elif prop_type == "multi_select":
                if isinstance(value, list):
                    properties[prop_name] = {"multi_select": [{"name": str(v)} for v in value]}
                else:
                    properties[prop_name] = {"multi_select": [{"name": str(value)}]}
            elif prop_type == "date":
                properties[prop_name] = {"date": {"start": str(value)}}
            elif prop_type == "checkbox":
                properties[prop_name] = {"checkbox": bool(value)}
            elif prop_type == "url":
                properties[prop_name] = {"url": str(value)}
            elif prop_type == "email":
                properties[prop_name] = {"email": str(value)}
            elif prop_type == "phone_number":
                properties[prop_name] = {"phone_number": str(value)}
            elif prop_type == "relation":
                # Handle relation properties properly
                logger.debug(
                    f"Processing relation property '{prop_name}' with value: {repr(value)} (type: {type(value)})"
                )
                if isinstance(value, list):
                    # If it's already a list of relation objects, use as-is
                    if all(isinstance(v, dict) and "id" in v for v in value):
                        properties[prop_name] = {"relation": value}
                        logger.debug(f"Using relation objects as-is for '{prop_name}': {value}")
                    else:
                        # If it's a list of IDs, convert to relation objects
                        properties[prop_name] = {"relation": [{"id": str(v)} for v in value]}
                        logger.debug(
                            f"Converted ID list to relation objects for '{prop_name}': {properties[prop_name]}"
                        )
                elif isinstance(value, dict) and "id" in value:
                    # If it's already a relation object, wrap in list
                    properties[prop_name] = {"relation": [value]}
                    logger.debug(f"Wrapped relation object in list for '{prop_name}': {properties[prop_name]}")
                elif isinstance(value, str):
                    # If it's a string ID, create relation object
                    properties[prop_name] = {"relation": [{"id": value}]}
                    logger.debug(f"Created relation object from string ID for '{prop_name}': {properties[prop_name]}")
                else:
                    # Fallback: convert to string ID
                    properties[prop_name] = {"relation": [{"id": str(value)}]}
                    logger.debug(f"Fallback string conversion for '{prop_name}': {properties[prop_name]}")
            # Note: formula and rollup properties are computed, so we skip them

        return properties

    async def add_course_entry(self, course_data: Dict[str, Any]) -> Optional[str]:
        """Add a course entry to the Courses database using actual schema"""
        try:
            database_id = await self.get_database_by_name("Courses")
            if not database_id:
                raise Exception("Courses database not found")

            # Get the actual schema
            schema = await self.get_database_schema("Courses")
            if not schema:
                # Fallback to basic title if schema retrieval fails
                properties = {"Name": {"title": [{"text": {"content": course_data.get("title", "Untitled Course")}}]}}
            else:
                # Use schema-based property building
                properties = self._build_properties_from_schema(schema, course_data)

                # Ensure we have at least a title
                if not properties:
                    title_prop = None
                    for prop_name, prop_info in schema.get("properties", {}).items():
                        if prop_info.get("type") == "title":
                            title_prop = prop_name
                            break

                    if title_prop:
                        properties[title_prop] = {
                            "title": [{"text": {"content": course_data.get("title", "Untitled Course")}}]
                        }

            response = await self.client.pages.create(parent={"database_id": database_id}, properties=properties)

            logger.info(f"Added course: {course_data.get('title')} -> {response['id']}")
            return response["id"]

        except Exception as e:
            logger.error(f"Failed to add course entry: {e}")
            return None

    async def add_assignment_entry(self, assignment_data: Dict[str, Any]) -> Optional[str]:
        """Add an assignment entry to the Assignments/Exams database using actual schema"""
        try:
            database_id = await self.get_database_by_name("Assignments/Exams")
            if not database_id:
                raise Exception("Assignments/Exams database not found")

            # Get the actual schema
            schema = await self.get_database_schema("Assignments/Exams")
            if not schema:
                # Fallback to basic title if schema retrieval fails
                properties = {
                    "Name": {"title": [{"text": {"content": assignment_data.get("title", "Untitled Assignment")}}]}
                }
            else:
                # Use schema-based property building
                properties = self._build_properties_from_schema(schema, assignment_data)

                # Ensure we have at least a title
                if not properties:
                    title_prop = None
                    for prop_name, prop_info in schema.get("properties", {}).items():
                        if prop_info.get("type") == "title":
                            title_prop = prop_name
                            break

                    if title_prop:
                        properties[title_prop] = {
                            "title": [{"text": {"content": assignment_data.get("title", "Untitled Assignment")}}]
                        }

            response = await self.client.pages.create(parent={"database_id": database_id}, properties=properties)

            logger.info(f"Added assignment: {assignment_data.get('title')} -> {response['id']}")
            return response["id"]

        except Exception as e:
            logger.error(f"Failed to add assignment entry: {e}")
            return None

    async def add_note_entry(self, note_data: Dict[str, Any]) -> Optional[str]:
        """Add a note entry to the Notes database using actual schema"""
        try:
            database_id = await self.get_database_by_name("Notes")
            if not database_id:
                raise Exception("Notes database not found")

            # Get the actual schema
            schema = await self.get_database_schema("Notes")
            if not schema:
                # Fallback to basic title if schema retrieval fails
                properties = {"Name": {"title": [{"text": {"content": note_data.get("title", "Untitled Note")}}]}}
            else:
                # Use schema-based property building
                properties = self._build_properties_from_schema(schema, note_data)

                # Ensure we have at least a title
                if not properties:
                    title_prop = None
                    for prop_name, prop_info in schema.get("properties", {}).items():
                        if prop_info.get("type") == "title":
                            title_prop = prop_name
                            break

                    if title_prop:
                        properties[title_prop] = {
                            "title": [{"text": {"content": note_data.get("title", "Untitled Note")}}]
                        }

            response = await self.client.pages.create(parent={"database_id": database_id}, properties=properties)

            logger.info(f"Added note: {note_data.get('title')} -> {response['id']}")
            return response["id"]

        except Exception as e:
            logger.error(f"Failed to add note entry: {e}")
            return None

    async def verify_databases_exist(self) -> Dict[str, bool]:
        """Verify that all 3 required databases exist"""
        required_databases = ["Courses", "Notes", "Assignments/Exams"]
        results = {}

        for db_name in required_databases:
            db_id = await self.get_database_by_name(db_name)
            results[db_name] = db_id is not None

        return results

    async def get_synced_courses(self) -> List[NotionCourseInfo]:
        """Get all courses from Notion that have Canvas course IDs"""
        try:
            database_id = await self.get_database_by_name("Courses")
            if not database_id:
                logger.warning("Courses database not found")
                return []

            # Query all pages in the Courses database with proper pagination
            courses = []
            has_more = True
            next_cursor = None

            while has_more:
                query_params = {"database_id": database_id, "page_size": 100}
                if next_cursor:
                    query_params["start_cursor"] = next_cursor

                response = await self.client.databases.query(**query_params)

                for page in response.get("results", []):
                    # Extract course properties
                    properties = page.get("properties", {})

                    # Look for Canvas course ID in properties
                    canvas_course_id = None
                    notion_page_id = page.get("id")
                    title = "Untitled Course"
                    course_code = ""

                    # Extract title
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "title":
                            title_content = prop_data.get("title", [])
                            if title_content:
                                title = title_content[0].get("text", {}).get("content", "Untitled Course")
                            break

                    # Extract course code and look for Canvas course ID in contact field
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "rich_text":
                            rich_text_content = prop_data.get("rich_text", [])
                            if rich_text_content:
                                text_value = rich_text_content[0].get("text", {}).get("content", "")

                                if prop_name.lower() in ["course_code", "course code", "coursecode"]:
                                    course_code = text_value

                        elif prop_data.get("type") == "phone_number":
                            # Canvas course ID is stored in the contact/phone_number field
                            phone_value = prop_data.get("phone_number", "")
                            if phone_value and "Canvas ID:" in phone_value:
                                # Extract the Canvas ID from format "Canvas ID: 123456"
                                try:
                                    canvas_course_id = phone_value.split("Canvas ID:")[1].strip()
                                    logger.info(f"Found Canvas course ID: {canvas_course_id} for course: {title}")
                                except (IndexError, AttributeError):
                                    logger.warning(f"Could not parse Canvas ID from contact field: {phone_value}")

                    # Only include courses that have Canvas course IDs
                    if canvas_course_id:
                        try:
                            # Convert canvas_course_id to integer and create NotionCourseInfo object
                            course_info = NotionCourseInfo(
                                notion_page_id=notion_page_id,
                                canvas_course_id=int(canvas_course_id),
                                title=title,
                                course_code=course_code,
                            )
                            courses.append(course_info)
                        except ValueError as e:
                            logger.warning(f"Invalid Canvas course ID '{canvas_course_id}' for course '{title}': {e}")
                            continue

                # Update pagination variables
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")

            logger.info(f"Retrieved {len(courses)} courses with Canvas IDs from Notion")
            return courses

        except Exception as e:
            logger.error(f"Failed to get synced courses: {e}")
            return []

    async def get_existing_assignments(self) -> List[NotionAssignmentInfo]:
        """Get all existing assignments from Notion with their Canvas assignment IDs"""
        try:
            database_id = await self.get_database_by_name("Assignments/Exams")

            if not database_id:
                logger.warning("Assignments/Exams database not found")
                return []

            # Query all pages in the Assignments/Exams database with proper pagination
            assignments = []
            has_more = True
            next_cursor = None

            while has_more:
                query_params = {"database_id": database_id, "page_size": 100}
                if next_cursor:
                    query_params["start_cursor"] = next_cursor

                response = await self.client.databases.query(**query_params)

                for page in response.get("results", []):
                    properties = page.get("properties", {})

                    notion_page_id = page.get("id")
                    title = "Untitled Assignment"
                    canvas_assignment_id = None

                    # Extract title
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "title":
                            title_content = prop_data.get("title", [])
                            if title_content:
                                title = title_content[0].get("text", {}).get("content", "Untitled Assignment")
                            break

                    # Extract Canvas assignment ID from weighting field
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "number" and prop_name.lower() in ["weighting", "weight"]:
                            weight_value = prop_data.get("number")
                            if (
                                weight_value and weight_value > 1000
                            ):  # Canvas assignment IDs are typically large numbers
                                canvas_assignment_id = str(int(weight_value))
                                logger.debug(
                                    f"Found Canvas assignment ID {canvas_assignment_id} in weighting field for assignment: {title}"
                                )
                                break

                    # Only include assignments that have Canvas assignment IDs (for duplicate detection)
                    if canvas_assignment_id:
                        try:
                            # Create NotionAssignmentInfo object
                            assignment_info = NotionAssignmentInfo(
                                notion_page_id=notion_page_id, canvas_assignment_id=canvas_assignment_id, title=title
                            )
                            assignments.append(assignment_info)
                        except Exception as e:
                            logger.warning(f"Failed to create assignment info for '{title}': {e}")
                            continue
                    else:
                        logger.debug(f"Assignment '{title}' has no Canvas ID - may be manually created")

                # Update pagination variables
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                # Removed verbose logging for performance

            logger.info(f"Found {len(assignments)} existing assignments with Canvas IDs")
            return assignments

        except Exception as e:
            logger.error(f"Failed to get existing assignments: {e}")
            return []

    async def delete_assignments_by_canvas_ids(self, canvas_assignment_ids: List[str]) -> int:
        """Delete assignments from Notion by Canvas assignment IDs"""
        try:
            existing_assignments: List[NotionAssignmentInfo] = await self.get_existing_assignments()
            if not existing_assignments:
                logger.warning("No existing assignments found")
                return 0

            deleted_count = 0
            for assignment in existing_assignments:
                if assignment.canvas_assignment_id in canvas_assignment_ids:
                    try:
                        # Archive (delete) the page in Notion
                        await self.client.pages.update(page_id=assignment.notion_page_id, archived=True)
                        deleted_count += 1
                        logger.info(
                            f"Deleted assignment: {assignment.title} (Canvas ID: {assignment.canvas_assignment_id})"
                        )
                    except Exception as e:
                        logger.error(f"Failed to delete assignment {assignment.title}: {e}")

            logger.info(f"Deleted {deleted_count} assignments")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete assignments: {e}")
            return 0

    async def delete_all_assignments_for_courses(self, course_notion_ids: List[str]) -> int:
        """Delete all assignments that belong to specific courses"""
        try:
            database_id = await self.get_database_by_name("Assignments/Exams")
            if not database_id:
                logger.warning("Assignments/Exams database not found")
                return 0

            # Query all assignments in the database with proper pagination
            deleted_count = 0
            has_more = True
            next_cursor = None

            while has_more:
                query_params = {"database_id": database_id, "page_size": 100}
                if next_cursor:
                    query_params["start_cursor"] = next_cursor

                response = await self.client.databases.query(**query_params)

                for page in response.get("results", []):
                    properties = page.get("properties", {})
                    notion_page_id = page.get("id")

                    # Check if this assignment belongs to one of the specified courses
                    # Look for relation to courses
                    assignment_belongs_to_course = False
                    assignment_title = "Unknown Assignment"

                    # Extract assignment title
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "title":
                            title_content = prop_data.get("title", [])
                            if title_content:
                                assignment_title = title_content[0].get("text", {}).get("content", "Unknown Assignment")
                            break

                    # Check if this assignment is related to any of the specified courses
                    for prop_name, prop_data in properties.items():
                        if prop_data.get("type") == "relation":
                            # Check if this relation field links to any of our courses
                            relations = prop_data.get("relation", [])
                            for relation in relations:
                                if relation.get("id") in course_notion_ids:
                                    assignment_belongs_to_course = True
                                    break

                    if assignment_belongs_to_course:
                        try:
                            # Archive (delete) the assignment
                            await self.client.pages.update(page_id=notion_page_id, archived=True)
                            deleted_count += 1
                            logger.info(f"Deleted assignment: {assignment_title}")
                        except Exception as e:
                            logger.error(f"Failed to delete assignment {assignment_title}: {e}")

                # Update pagination variables
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")

            logger.info(f"Deleted {deleted_count} assignments from specified courses")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete assignments for courses: {e}")
            return 0


# Demo/Test functions
async def test_existing_databases(notion_token: str, parent_page_id: str) -> Dict:
    """Test access to your existing 3 databases"""
    manager = NotionWorkspaceManager(notion_token, parent_page_id)

    try:
        # List all databases in workspace
        all_databases = await manager.list_all_databases()

        # List databases under parent page
        parent_databases = await manager.list_databases_in_parent()

        # Check for required databases
        verification = await manager.verify_databases_exist()

        # Extract just the database names for easy reading
        available_database_names = [db["title"] for db in all_databases]

        return {
            "success": True,
            "message": "Successfully accessed Notion workspace",
            "available_database_names": available_database_names,
            "total_databases_found": len(all_databases),
            "all_databases": all_databases,
            "parent_page_databases": parent_databases,
            "database_verification": verification,
            "note": "Working with 3 databases: Courses, Notes, Assignments/Exams",
        }

    except Exception as e:
        logger.error(f"Failed to test databases: {e}")
        return {"success": False, "message": f"Failed to access databases: {str(e)}", "error": str(e)}


async def get_database_schemas(notion_token: str, parent_page_id: str) -> Dict:
    """Get the complete schemas for all 3 databases"""
    manager = NotionWorkspaceManager(notion_token, parent_page_id)

    try:
        schemas = await manager.get_all_database_schemas()

        return {
            "success": True,
            "message": f"Retrieved schemas for {len(schemas)} databases",
            "schemas": schemas,
            "note": "Use this schema information to properly structure your data when adding entries",
        }

    except Exception as e:
        logger.error(f"Failed to get database schemas: {e}")
        return {"success": False, "message": f"Failed to get schemas: {str(e)}", "error": str(e)}


# Legacy functions for backward compatibility
async def get_notion_workspace_info(notion_token: str, parent_page_id: str) -> Dict:
    """Get information about the Notion workspace structure"""
    return await test_existing_databases(notion_token, parent_page_id)
