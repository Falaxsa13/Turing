from datetime import datetime, timezone
from typing import Optional, Dict, Any
from loguru import logger

from app.core.exceptions import ValidationError, DatabaseError
from app.models.user_settings import UserSettings
from app.services.canvas import CanvasSyncService, CourseMapper
from app.utils.notion_helper import NotionWorkspaceManager


class CourseSyncService:
    def __init__(self, firebase_db):
        self.firebase_db = firebase_db

    async def sync_courses(self, user_email: str):
        """Fetch enrolled Canvas courses and create them in Notion for the current semester."""
        try:
            # Get user settings
            user_settings: UserSettings = await self.firebase_db.get_user_settings(user_email)

            if not user_settings:
                raise DatabaseError("User not found. Please run /setup/init first.")

            # Validate required settings
            if not user_settings.canvas_base_url or not user_settings.canvas_pat:
                raise ValidationError("Canvas credentials not configured. Please set Canvas base URL and PAT.")

            if not user_settings.notion_token or not user_settings.notion_parent_page_id:
                raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

            # Create Canvas and Notion services and perform the sync
            logger.info(f"Starting Canvas to Notion sync for user: {user_email}")

            # Initialize Canvas sync service
            canvas_service = CanvasSyncService(
                canvas_base_url=user_settings.canvas_base_url, canvas_token=user_settings.canvas_pat
            )

            # Initialize Notion workspace manager
            notion_manager = NotionWorkspaceManager(
                notion_token=user_settings.notion_token, parent_page_id=user_settings.notion_parent_page_id
            )

            # Initialize course mapper
            course_mapper = CourseMapper()

            # Perform the sync
            sync_result = await self._sync_current_semester_courses(canvas_service, notion_manager, course_mapper)

            # Update last sync time if successful and log sync
            if sync_result["success"]:
                now = datetime.now(timezone.utc)
                await self.firebase_db.create_or_update_user_settings(
                    user_email,
                    {
                        "last_canvas_sync": now,
                        "last_notion_sync": now,
                        "updated_at": now,
                    },
                )

                # Add sync log
                await self.firebase_db.add_sync_log(
                    user_email,
                    {
                        "sync_type": "courses",
                        "status": "success",
                        "items_processed": sync_result["courses_found"],
                        "items_created": sync_result["courses_created"],
                        "items_failed": sync_result["courses_failed"],
                        "items_skipped": sync_result["courses_skipped"],
                        "metadata": {"courses": sync_result["created_courses"][:5]},  # Limit logged data
                    },
                )

                logger.info(f"Canvas sync completed for user: {user_email}")

            return sync_result

        except Exception as e:
            logger.error(f"Unexpected error during Canvas sync: {e}")

            # Log failed sync
            try:
                await self.firebase_db.add_sync_log(
                    user_email,
                    {
                        "sync_type": "courses",
                        "status": "failed",
                        "error_message": str(e),
                        "items_processed": 0,
                        "items_created": 0,
                        "items_failed": 0,
                        "items_skipped": 0,
                    },
                )
            except:
                pass  # Don't fail if logging fails

            raise e

    async def _sync_current_semester_courses(self, canvas_service, notion_manager, course_mapper):
        """Sync current semester courses from Canvas to Notion."""
        try:
            # Get current semester courses from Canvas
            logger.info("Fetching current semester courses from Canvas...")
            canvas_courses = await canvas_service.get_current_semester_courses()

            if not canvas_courses:
                return {
                    "success": True,
                    "message": "No current semester courses found",
                    "courses_found": 0,
                    "courses_created": 0,
                    "courses_failed": 0,
                    "courses_skipped": 0,
                    "created_courses": [],
                    "failed_courses": [],
                    "note": "No courses to sync for current semester",
                }

            logger.info(f"Found {len(canvas_courses)} current semester courses")

            # Get existing courses to check for duplicates
            existing_courses = await notion_manager.get_synced_courses()
            existing_canvas_ids = {str(course.canvas_course_id) for course in existing_courses}

            logger.info(f"Found {len(existing_canvas_ids)} existing courses in Notion")

            courses_created = 0
            courses_failed = 0
            courses_skipped = 0
            created_courses = []
            failed_courses = []

            # Process each course
            for canvas_course in canvas_courses:
                try:
                    course_id = str(canvas_course.get("id", ""))
                    course_name = canvas_course.get("name", "Untitled Course")

                    # Check for duplicates
                    if course_id in existing_canvas_ids:
                        logger.info(f"Skipping existing course: {course_name}")
                        courses_skipped += 1
                        continue

                    # Map Canvas course to Notion format
                    notion_course = course_mapper.map_canvas_course_to_notion(canvas_course)

                    # Create course in Notion
                    notion_course_id = await notion_manager.add_course_entry(notion_course)

                    if notion_course_id:
                        courses_created += 1
                        created_courses.append(
                            {
                                "notion_id": notion_course_id,
                                "canvas_id": int(course_id),
                                "name": course_name,
                                "course_code": notion_course.get("course_code", ""),
                            }
                        )
                        logger.info(f"✅ Created course: {course_name}")
                    else:
                        courses_failed += 1
                        failed_courses.append(
                            {
                                "canvas_id": int(course_id) if course_id.isdigit() else 0,
                                "name": course_name,
                                "error": "Failed to create in Notion",
                            }
                        )
                        logger.error(f"❌ Failed to create course: {course_name}")

                except Exception as e:
                    courses_failed += 1
                    failed_courses.append(
                        {
                            "canvas_id": int(course_id) if course_id.isdigit() else 0,
                            "name": course_name,
                            "error": str(e),
                        }
                    )
                    logger.error(f"❌ Error processing course {course_name}: {e}")

            # Build result
            success = courses_failed == 0
            message = f"Processed {len(canvas_courses)} courses: {courses_created} created, {courses_failed} failed, {courses_skipped} skipped"

            return {
                "success": success,
                "message": message,
                "courses_found": len(canvas_courses),
                "courses_created": courses_created,
                "courses_failed": courses_failed,
                "courses_skipped": courses_skipped,
                "created_courses": created_courses,
                "failed_courses": failed_courses,
                "note": "Course sync completed successfully" if success else "Some courses failed to sync",
            }

        except Exception as e:
            logger.error(f"Failed to sync courses: {e}")
            return {
                "success": False,
                "message": f"Course sync failed: {str(e)}",
                "courses_found": 0,
                "courses_created": 0,
                "courses_failed": 0,
                "courses_skipped": 0,
                "created_courses": [],
                "failed_courses": [],
                "note": "Check logs for detailed error information",
            }
