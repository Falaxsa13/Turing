from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.services.canvas import CanvasSyncService, AssignmentMapper
from app.utils.notion_helper import NotionWorkspaceManager
from app.schemas.sync import AssignmentSyncResponse


class SyncCoordinator:
    """
    Coordinates synchronization between Canvas and Notion.
    """

    def __init__(self, canvas_base_url: str, canvas_token: str, notion_token: str, notion_parent_page_id: str):
        """
        Initialize the sync coordinator.

        Args:
            canvas_base_url: Canvas instance base URL
            canvas_token: Canvas Personal Access Token
            notion_token: Notion integration token
            notion_parent_page_id: Notion parent page ID
        """
        self.canvas_service = CanvasSyncService(canvas_base_url, canvas_token)
        self.notion_manager = NotionWorkspaceManager(notion_token, notion_parent_page_id)
        self.assignment_mapper = AssignmentMapper()

    async def sync_current_semester_courses(self) -> Dict[str, Any]:
        """
        Sync current semester courses from Canvas to Notion.
        Skips courses that already exist in Notion (based on Canvas course ID).

        Returns:
            Dictionary with sync results
        """
        try:
            logger.info("Starting Canvas to Notion sync for current semester courses")

            # Get existing courses to check for duplicates
            existing_courses = await self.notion_manager.get_synced_courses()
            existing_canvas_ids = set(course.canvas_course_id for course in existing_courses)
            logger.info(f"Found {len(existing_canvas_ids)} existing courses in Notion")

            # Get current semester courses from Canvas
            current_semester_courses = await self.canvas_service.get_current_semester_courses()

            if not current_semester_courses:
                return {
                    "success": False,
                    "message": "No courses found for current semester",
                    "courses_found": 0,
                    "courses_created": 0,
                    "courses_failed": 0,
                    "courses_skipped": 0,
                    "created_courses": [],
                    "failed_courses": [],
                    "note": "Check your Canvas enrollment status",
                }

            logger.info(f"Found {len(current_semester_courses)} courses for current semester")

            # Sync each course
            created_courses = []
            failed_courses = []
            skipped_courses = 0

            for canvas_course in current_semester_courses:
                try:
                    canvas_course_id = str(canvas_course.get("id", ""))
                    course_name = canvas_course.get("name", "Untitled Course")

                    # Skip if course already exists in Notion
                    if canvas_course_id in existing_canvas_ids:
                        skipped_courses += 1
                        logger.info(f"Skipping existing course: {course_name} (Canvas ID: {canvas_course_id})")
                        continue

                    # Enhance course with detailed instructor information
                    enhanced_course = await self.canvas_service.enhance_course_with_professors(canvas_course)

                    # Map Canvas course to Notion format
                    notion_course_data = self.canvas_service.course_mapper.map_canvas_course_to_notion(enhanced_course)

                    # Create in Notion
                    course_id = await self.notion_manager.add_course_entry(notion_course_data)

                    if course_id:
                        created_courses.append(
                            {
                                "notion_id": course_id,
                                "canvas_id": canvas_course.get("id"),
                                "name": notion_course_data.get("title", canvas_course.get("name")),
                                "course_code": notion_course_data.get("course_code", ""),
                                "term": notion_course_data.get("term", ""),
                                "professor": notion_course_data.get("professor", ""),
                            }
                        )
                        logger.info(
                            f"Created course: {notion_course_data.get('title', canvas_course.get('name'))} -> {course_id}"
                        )
                    else:
                        failed_courses.append(
                            {
                                "canvas_id": canvas_course.get("id"),
                                "name": notion_course_data.get("title", canvas_course.get("name")),
                                "error": "Failed to create in Notion",
                            }
                        )

                except Exception as e:
                    # Map Canvas course to get parsed title for error reporting
                    try:
                        notion_course_data = self.canvas_service.course_mapper.map_canvas_course_to_notion(
                            canvas_course
                        )
                        parsed_title = notion_course_data.get("title", canvas_course.get("name"))
                    except:
                        parsed_title = canvas_course.get("name", "Unknown Course")

                    logger.error(f"Failed to create course {parsed_title}: {e}")
                    failed_courses.append({"canvas_id": canvas_course.get("id"), "name": parsed_title, "error": str(e)})

            # Prepare result
            courses_created = len(created_courses)
            courses_failed = len(failed_courses)
            total_courses = len(current_semester_courses)

            success = courses_created > 0 or total_courses == skipped_courses
            skipped_message = f" (skipped {skipped_courses} existing)" if skipped_courses > 0 else ""
            message = f"Canvas sync completed. Created {courses_created}/{total_courses} courses{skipped_message}"

            result = {
                "success": success,
                "message": message,
                "courses_found": total_courses,
                "courses_created": courses_created,
                "courses_failed": courses_failed,
                "courses_skipped": skipped_courses,
                "created_courses": created_courses,
                "failed_courses": failed_courses,
                "note": "Courses synced with duplicate detection enabled",
            }

            logger.info(
                f"Sync completed: {courses_created} created, {courses_failed} failed, {skipped_courses} skipped"
            )
            return result

        except Exception as e:
            logger.error(f"Canvas sync failed: {e}")
            return {
                "success": False,
                "message": f"Canvas sync failed: {str(e)}",
                "courses_found": 0,
                "courses_created": 0,
                "courses_failed": 0,
                "courses_skipped": 0,
                "created_courses": [],
                "failed_courses": [],
                "note": "Check logs for detailed error information",
            }

    async def sync_assignments_for_courses(self) -> AssignmentSyncResponse:
        """
        Sync all assignments from Canvas to Notion for courses that were previously synced.
        Skips assignments that already exist in Notion (based on Canvas assignment ID).

        Returns:
            Dictionary with sync results including success status, counts, and details
        """
        try:
            logger.info("Starting assignment synchronization from Canvas to Notion")

            # Get courses that were previously synced from Canvas (have Canvas course IDs)
            synced_courses = await self.notion_manager.get_synced_courses()

            if not synced_courses:
                return AssignmentSyncResponse(
                    success=False,
                    message="No courses with Canvas IDs found in Notion. Please run course sync first.",
                    courses_processed=0,
                    assignments_found=0,
                    assignments_created=0,
                    assignments_failed=0,
                    assignments_skipped=0,
                    created_assignments=[],
                    failed_assignments=[],
                    note="Use /sync/start to import courses first",
                )

            logger.info(f"Found {len(synced_courses)} courses with Canvas IDs")

            # Get existing assignments to check for duplicates
            existing_assignments = await self.notion_manager.get_existing_assignments()
            existing_canvas_ids = set(
                assignment.canvas_assignment_id
                for assignment in existing_assignments
                if assignment.canvas_assignment_id
            )
            logger.info(f"Found {len(existing_canvas_ids)} existing assignments in Notion")
            logger.debug(f"Existing Canvas assignment IDs: {list(existing_canvas_ids)[:10]}...")

            total_assignments_found = 0
            total_assignments_created = 0
            total_assignments_failed = 0
            total_assignments_skipped = 0
            created_assignments = []
            failed_assignments = []

            # Process each course
            for course in synced_courses:
                canvas_course_id = course.canvas_course_id
                notion_course_id = course.notion_page_id
                course_title = course.title

                logger.info(f"Processing assignments for course: {course_title} (Canvas ID: {canvas_course_id})")
                logger.debug(f"Notion course ID type: {type(notion_course_id)}, value: {repr(notion_course_id)}")

                try:
                    # Fetch assignments from Canvas for this course
                    canvas_assignments = await self.canvas_service.canvas_client.get_course_assignments(
                        str(canvas_course_id)
                    )

                    if not canvas_assignments:
                        logger.info(f"No assignments found for course: {course_title}")
                        continue

                    logger.info(f"Found {len(canvas_assignments)} assignments for course: {course_title}")
                    total_assignments_found += len(canvas_assignments)

                    # Process each assignment
                    for assignment in canvas_assignments:
                        try:
                            assignment_id = str(assignment.get("id"))  # Convert to string for comparison
                            assignment_name = assignment.get("name", "Unnamed Assignment")

                            logger.debug(f"Checking assignment: {assignment_name} (Canvas ID: {assignment_id})")

                            # Check if this assignment already exists (duplicate detection)
                            if assignment_id in existing_canvas_ids:
                                logger.info(
                                    f"Skipping duplicate assignment: {assignment_name} (Canvas ID: {assignment_id})"
                                )
                                total_assignments_skipped += 1
                                continue

                            # Map Canvas assignment to Notion format
                            notion_assignment = self.assignment_mapper.map_canvas_assignment_to_notion(
                                assignment, notion_course_id
                            )

                            logger.debug(f"About to create assignment with course ID: {repr(notion_course_id)}")

                            # Create assignment in Notion
                            notion_assignment_id = await self._create_assignment_in_notion(
                                notion_assignment, notion_course_id
                            )

                            if notion_assignment_id:
                                total_assignments_created += 1
                                # Build response matching SyncAssignmentInfo schema
                                created_assignments.append(
                                    {
                                        "notion_id": notion_assignment_id,
                                        "canvas_id": int(assignment_id),
                                        "name": assignment_name,
                                        "type": notion_assignment.get("type", "Assignment"),
                                        "due_date": notion_assignment.get("due_date"),
                                        "total_score": float(notion_assignment.get("total_score", 0)),
                                        "course_title": course_title,
                                    }
                                )
                                logger.info(f"✅ Created assignment: {assignment_name}")
                            else:
                                total_assignments_failed += 1
                                failed_assignments.append(
                                    {
                                        "canvas_id": int(assignment_id),
                                        "name": assignment_name,
                                        "course_title": course_title,
                                        "error": "Failed to create in Notion",
                                    }
                                )
                                logger.error(f"❌ Failed to create assignment: {assignment_name}")

                        except Exception as e:
                            total_assignments_failed += 1
                            assignment_name = assignment.get("name", "Unknown Assignment")
                            assignment_id = assignment.get("id", 0)
                            failed_assignments.append(
                                {
                                    "canvas_id": int(assignment_id) if assignment_id else 0,
                                    "name": assignment_name,
                                    "course_title": course_title,
                                    "error": str(e),
                                }
                            )
                            logger.error(f"❌ Error processing assignment {assignment_name}: {e}")

                except Exception as e:
                    logger.error(f"Failed to process assignments for course {course_title}: {e}")
                    # Continue processing other courses

            # Prepare final response
            success = total_assignments_created > 0 or total_assignments_found == total_assignments_skipped
            skipped_message = (
                f" (skipped {total_assignments_skipped} existing)" if total_assignments_skipped > 0 else ""
            )
            message = f"Assignment sync completed. Created {total_assignments_created}/{total_assignments_found} assignments{skipped_message}"

            return AssignmentSyncResponse(
                success=success,
                message=message,
                courses_processed=len(synced_courses),
                assignments_found=total_assignments_found,
                assignments_created=total_assignments_created,
                assignments_failed=total_assignments_failed,
                assignments_skipped=total_assignments_skipped,
                created_assignments=created_assignments,
                failed_assignments=failed_assignments,
                note="Assignments synced with duplicate detection enabled",
            )

        except Exception as e:
            logger.error(f"Assignment sync failed: {e}")
            return AssignmentSyncResponse(
                success=False,
                message=f"Assignment sync failed: {str(e)}",
                courses_processed=0,
                assignments_found=0,
                assignments_created=0,
                assignments_failed=0,
                assignments_skipped=0,
                created_assignments=[],
                failed_assignments=[],
                note="Check logs for detailed error information",
            )

    async def _create_assignment_in_notion(
        self, assignment_data: Dict[str, Any], course_notion_id: str
    ) -> Optional[str]:
        """
        Create an assignment in Notion's Assignments/Exams database with course relation.

        Args:
            assignment_data: Assignment data mapped for Notion
            course_notion_id: Notion page ID of the course this assignment belongs to

        Returns:
            Notion page ID of created assignment or None if failed
        """
        try:
            # Add course relation to assignment data
            assignment_with_relation = assignment_data.copy()

            # Based on the Notion schema documentation, assignments link to courses
            # We need to determine the exact relation field name
            database_id = await self.notion_manager.get_database_by_name("Assignments/Exams")
            if not database_id:
                logger.error("Assignments/Exams database not found")
                return None

            # Get database schema to find relation field
            database_info = await self.notion_manager.client.databases.retrieve(database_id=database_id)
            properties = database_info.get("properties", {})

            # Find relation field that connects to courses
            relation_field_name = None
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "relation":
                    relation_field_name = prop_name
                    break

            if relation_field_name:
                # Clean up course_notion_id - ensure it's just the UUID string
                clean_course_id = course_notion_id

                # Handle case where course_notion_id might be a string representation of a dict
                if isinstance(course_notion_id, str) and course_notion_id.startswith("{'id':"):
                    # Extract the UUID from string like "{'id': 'uuid-here'}"
                    try:
                        import ast

                        parsed = ast.literal_eval(course_notion_id)
                        if isinstance(parsed, dict) and "id" in parsed:
                            clean_course_id = parsed["id"]
                            logger.info(f"Extracted UUID from dict string: {clean_course_id}")
                    except:
                        # If parsing fails, try to extract with regex
                        import re

                        match = re.search(r"'id':\s*'([^']+)'", course_notion_id)
                        if match:
                            clean_course_id = match.group(1)
                            logger.info(f"Extracted UUID with regex: {clean_course_id}")

                # Remove any extra quotes or whitespace
                clean_course_id = clean_course_id.strip().strip('"').strip("'")

                logger.info(f"Setting course relation: {relation_field_name} = {clean_course_id}")
                assignment_with_relation[relation_field_name] = [{"id": clean_course_id}]
                logger.info(f"Added course relation using field: {relation_field_name}")

            # Create assignment in Notion
            notion_assignment_id = await self.notion_manager.add_assignment_entry(assignment_with_relation)

            if notion_assignment_id:
                logger.info(f"Successfully created assignment in Notion: {notion_assignment_id}")
                return notion_assignment_id
            else:
                logger.error("Failed to create assignment in Notion")
                return None

        except Exception as e:
            logger.error(f"Failed to create assignment in Notion: {e}")
            return None

    async def _create_course_in_notion(self, course_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a course in Notion's Courses database.

        Args:
            course_data: Course data mapped for Notion

        Returns:
            Notion page ID of created course or None if failed
        """
        try:
            # Create course in Notion
            notion_course_id = await self.notion_manager.add_course_entry(course_data)

            if notion_course_id:
                logger.info(f"Successfully created course in Notion: {notion_course_id}")
                return notion_course_id
            else:
                logger.error("Failed to create course in Notion")
                return None

        except Exception as e:
            logger.error(f"Failed to create course in Notion: {e}")
            return None
