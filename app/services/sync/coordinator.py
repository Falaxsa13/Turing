from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from app.services.canvas import CanvasSyncService
from app.utils.notion_helper import NotionWorkspaceManager


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

    async def sync_current_semester_courses(self) -> Dict[str, Any]:
        """
        Sync current semester courses from Canvas to Notion.

        Returns:
            Dictionary with sync results
        """
        try:
            logger.info("Starting Canvas to Notion sync for current semester courses")

            # Get current semester courses from Canvas
            current_semester_courses = await self.canvas_service.get_current_semester_courses()

            if not current_semester_courses:
                return {
                    "success": False,
                    "message": "No courses found for current semester",
                    "courses_found": 0,
                    "courses_created": 0,
                    "courses_failed": 0,
                    "created_courses": [],
                    "failed_courses": [],
                    "note": "Check your Canvas enrollment status",
                }

            logger.info(f"Found {len(current_semester_courses)} courses for current semester")

            # Sync each course
            created_courses = []
            failed_courses = []

            for canvas_course in current_semester_courses:
                try:
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
                    notion_course_data = self.canvas_service.course_mapper.map_canvas_course_to_notion(canvas_course)
                    parsed_title = notion_course_data.get("title", canvas_course.get("name"))

                    logger.error(f"Failed to create course {parsed_title}: {e}")
                    failed_courses.append({"canvas_id": canvas_course.get("id"), "name": parsed_title, "error": str(e)})

            # Prepare result
            courses_created = len(created_courses)
            courses_failed = len(failed_courses)
            total_courses = len(current_semester_courses)

            success = courses_created > 0 and courses_failed == 0

            result = {
                "success": success,
                "message": f"Successfully synced {courses_created}/{total_courses} courses",
                "courses_found": total_courses,
                "courses_created": courses_created,
                "courses_failed": courses_failed,
                "created_courses": created_courses,
                "failed_courses": failed_courses,
                "note": "Check your Notion Courses database for the new entries!",
            }

            logger.info(f"Sync completed: {courses_created} created, {courses_failed} failed")
            return result

        except Exception as e:
            logger.error(f"Canvas to Notion sync failed: {e}")
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}",
                "courses_found": 0,
                "courses_created": 0,
                "courses_failed": 0,
                "created_courses": [],
                "failed_courses": [],
                "note": "Please check your Canvas and Notion credentials",
            }
