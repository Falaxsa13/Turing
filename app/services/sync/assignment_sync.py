"""
Assignment sync service for creating beautiful Notion assignment pages.
"""

from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
from loguru import logger

from app.core.exceptions import ValidationError, DatabaseError
from app.schemas.sync import AssignmentSyncResponse, SyncAssignmentInfo, SyncFailedAssignment
from app.schemas.canvas import CanvasAssignmentDetails, CanvasAssignmentGroup, CanvasSubmissionInfo
from app.schemas.notion import NotionAssignmentFormatting
from app.services.canvas.enhanced_client import EnhancedCanvasClient
from app.services.notion.assignment_formatter import AssignmentFormatter
from app.services.notion.enhanced_assignment_manager import EnhancedAssignmentManager
from app.models.user_settings import UserSettings
from app.utils.notion_helper import NotionWorkspaceManager


class AssignmentSyncService:
    """Assignment sync service for rich Notion formatting."""

    def __init__(self, firebase_db=None):
        """Initialize the assignment sync service."""
        self.formatter = AssignmentFormatter()
        self.firebase_db = firebase_db
        self._current_user_email = None

    async def sync_assignments(
        self,
        user_email: str,
        include_submissions: bool = True,
        include_statistics: bool = True,
        include_rubrics: bool = True,
        include_assignment_groups: bool = True,
    ) -> AssignmentSyncResponse:
        """
        Sync Canvas assignments to Notion with rich formatting.

        This method creates beautiful, well-formatted assignment pages in Notion
        with comprehensive Canvas assignment details.
        """
        try:
            logger.info(f"Starting assignment sync for user: {user_email}")

            # Store user email for use in other methods
            self._current_user_email = user_email

            # Get user settings
            user_settings: UserSettings = await self._get_user_settings(user_email)

            # Validate credentials
            if not user_settings.canvas_base_url or not user_settings.canvas_pat:
                raise ValidationError("Canvas credentials not configured. Please set Canvas base URL and PAT.")
            if not user_settings.notion_token or not user_settings.notion_parent_page_id:
                raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

            # Initialize enhanced clients
            canvas_client = EnhancedCanvasClient(user_settings.canvas_base_url, user_settings.canvas_pat)
            notion_manager = EnhancedAssignmentManager(user_settings.notion_token, user_settings.notion_parent_page_id)

            # Get synced courses
            synced_courses = await self._get_synced_courses(user_email)

            logger.info(f"Found {len(synced_courses)} synced courses")

            if not synced_courses:
                return AssignmentSyncResponse(
                    success=False,
                    message="No synced courses found. Please sync courses first.",
                    courses_processed=0,
                    assignments_found=0,
                    assignments_created=0,
                    assignments_failed=0,
                    assignments_skipped=0,
                    created_assignments=[],
                    failed_assignments=[],
                    note="Sync courses before syncing assignments.",
                )

            # Get existing assignments once for all courses
            existing_assignments = await self._get_existing_assignments_batch()
            existing_assignment_ids = {int(assignment.canvas_assignment_id) for assignment in existing_assignments}

            # Process courses in parallel
            semaphore = asyncio.Semaphore(3)

            async def process_course_with_semaphore(course):
                async with semaphore:
                    return await self._sync_course_assignments(
                        canvas_client,
                        notion_manager,
                        course,
                        existing_assignment_ids,
                        include_submissions,
                        include_statistics,
                        include_rubrics,
                        include_assignment_groups,
                    )

            # Process all courses in parallel
            course_results = await asyncio.gather(
                *[process_course_with_semaphore(course) for course in synced_courses], return_exceptions=True
            )

            # Aggregate results
            total_assignments_found = 0
            total_assignments_created = 0
            total_assignments_failed = 0
            total_assignments_skipped = 0
            created_assignments = []
            failed_assignments = []

            for i, result in enumerate(course_results):
                course = synced_courses[i]
                if isinstance(result, BaseException):
                    logger.error(f"Failed to sync assignments for course {course.get('title', 'Unknown')}: {result}")
                    failed_assignments.append(
                        SyncFailedAssignment(
                            canvas_id=course.get("canvas_course_id", 0),
                            name=course.get("title", "Unknown Course"),
                            course_title=course.get("title", "Unknown Course"),
                            error=f"Course sync failed: {str(result)}",
                        )
                    )
                else:
                    # Aggregate successful results
                    total_assignments_found += result["assignments_found"]
                    total_assignments_created += result["assignments_created"]
                    total_assignments_failed += result["assignments_failed"]
                    total_assignments_skipped += result["assignments_skipped"]
                    created_assignments.extend(result["created_assignments"])
                    failed_assignments.extend(result["failed_assignments"])

            # Create response
            success = total_assignments_failed == 0
            message = (
                f"Assignment sync completed. {total_assignments_created} assignments created with rich formatting."
            )

            if total_assignments_failed > 0:
                message += f" {total_assignments_failed} assignments failed."

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
                note="Assignments created with enhanced formatting including descriptions, statistics, and rubrics.",
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
                note="Check logs for detailed error information.",
            )

    async def _sync_course_assignments(
        self,
        canvas_client: EnhancedCanvasClient,
        notion_manager: EnhancedAssignmentManager,
        course: Dict[str, Any],
        existing_assignment_ids: set,  # Pre-fetched existing assignments
        include_submissions: bool,
        include_statistics: bool,
        include_rubrics: bool,
        include_assignment_groups: bool,
    ) -> Dict[str, Any]:
        """Sync assignments for a single course with pre-fetched duplicate data."""

        course_title = course.get("title", "Unknown Course")
        course_id = str(course.get("canvas_course_id", ""))
        notion_course_id = course.get("notion_page_id", "")

        try:
            # Fetch assignments for this course
            assignments = await canvas_client.get_enhanced_course_assignments(
                course_id, include_submissions=include_submissions, include_groups=include_assignment_groups
            )

            if not assignments:
                return {
                    "assignments_found": 0,
                    "assignments_created": 0,
                    "assignments_failed": 0,
                    "assignments_skipped": 0,
                    "created_assignments": [],
                    "failed_assignments": [],
                }

            # Check for duplicates within this course
            canvas_ids_in_course = [a.id for a in assignments]
            unique_canvas_ids = set(canvas_ids_in_course)
            if len(canvas_ids_in_course) != len(unique_canvas_ids):
                duplicates = [id for id in canvas_ids_in_course if canvas_ids_in_course.count(id) > 1]
                logger.warning(f"Found duplicate Canvas assignment IDs within course: {set(duplicates)}")

            # Use pre-fetched existing assignments (no redundant queries)
            new_assignments = [a for a in assignments if a.id not in existing_assignment_ids]
            skipped_count = len(assignments) - len(new_assignments)

            if not new_assignments:
                return {
                    "assignments_found": len(assignments),
                    "assignments_created": 0,
                    "assignments_failed": 0,
                    "assignments_skipped": skipped_count,
                    "created_assignments": [],
                    "failed_assignments": [],
                }

            # Get assignment groups if needed (only for this course)
            assignment_groups = {}
            if include_assignment_groups:
                assignment_groups = await self._get_assignment_groups(canvas_client, course_id)

            # Process assignments in parallel with higher concurrency
            semaphore = asyncio.Semaphore(8)

            async def process_assignment_with_semaphore(assignment):
                async with semaphore:
                    return await self._process_single_assignment(
                        canvas_client,
                        notion_manager,
                        assignment,
                        assignment_groups.get(assignment.assignment_group_id),
                        notion_course_id or "",
                        course_title,
                        include_submissions,
                        include_statistics,
                        include_rubrics,
                        include_assignment_groups,
                    )

            # Process all assignments in parallel
            results = await asyncio.gather(
                *[process_assignment_with_semaphore(assignment) for assignment in new_assignments],
                return_exceptions=True,
            )

            # Process results
            assignments_created = 0
            assignments_failed = 0
            created_assignments = []
            failed_assignments = []

            for i, result in enumerate(results):
                assignment = new_assignments[i]
                if isinstance(result, Exception):
                    logger.error(f"Failed to process assignment '{assignment.name}': {result}")
                    assignments_failed += 1
                    failed_assignments.append(
                        SyncFailedAssignment(
                            canvas_id=assignment.id, name=assignment.name, course_title=course_title, error=str(result)
                        )
                    )
                elif isinstance(result, dict) and result.get("success"):
                    assignments_created += 1
                    created_assignments.append(result["assignment_info"])
                elif isinstance(result, dict):
                    assignments_failed += 1
                    failed_assignments.append(result["failed_info"])
                else:
                    assignments_failed += 1
                    failed_assignments.append(
                        SyncFailedAssignment(
                            canvas_id=assignment.id,
                            name=assignment.name,
                            course_title=course_title,
                            error="Unexpected result type",
                        )
                    )

            return {
                "assignments_found": len(assignments),
                "assignments_created": assignments_created,
                "assignments_failed": assignments_failed,
                "assignments_skipped": skipped_count,
                "created_assignments": created_assignments,
                "failed_assignments": failed_assignments,
            }

        except Exception as e:
            logger.error(f"Failed to sync assignments for course {course_title}: {e}")
            return {
                "assignments_found": 0,
                "assignments_created": 0,
                "assignments_failed": 1,
                "assignments_skipped": 0,
                "created_assignments": [],
                "failed_assignments": [
                    SyncFailedAssignment(
                        canvas_id=int(course_id) if course_id.isdigit() else 0,
                        name=course_title,
                        course_title=course_title,
                        error=str(e),
                    )
                ],
            }

    async def _process_single_assignment(
        self,
        canvas_client: EnhancedCanvasClient,
        notion_manager: EnhancedAssignmentManager,
        assignment: CanvasAssignmentDetails,
        assignment_group: Optional[CanvasAssignmentGroup],
        notion_course_id: str,
        course_title: str,
        include_submissions: bool,
        include_statistics: bool,
        include_rubrics: bool,
        include_assignment_groups: bool,
    ) -> Dict[str, Any]:
        """Process a single assignment with optimized performance."""

        try:
            # Get user submission if requested
            submission_info = None
            if include_submissions:
                submission_info = await canvas_client.get_user_submission_for_assignment(
                    str(assignment.course_id), str(assignment.id)
                )

            # Format assignment for Notion
            assignment_formatting = self.formatter.format_assignment_for_notion(
                assignment,
                assignment_group,
                submission_info,
                notion_course_id,
                include_rubric=include_rubrics,
                include_statistics=include_statistics,
                include_submission_details=include_submissions,
                include_assignment_group=include_assignment_groups,
            )

            # Get assignments database ID
            assignments_db_id = await self._get_assignments_database_id()
            if not assignments_db_id:
                raise Exception("Assignments database not found")

            # Create rich assignment page in Notion
            page_id = await notion_manager.create_rich_assignment_page(assignment_formatting, assignments_db_id)

            if not page_id:
                raise Exception("Failed to create assignment page in Notion")

            # Store assignment mapping in Firebase
            await self._store_assignment_mapping(assignment.id, page_id, assignment.name, course_title)

            # Create success response
            assignment_info = SyncAssignmentInfo(
                canvas_id=assignment.id,
                notion_id=page_id,
                name=assignment.name,
                type=assignment.submission_types[0] if assignment.submission_types else "online_upload",
                course_title=course_title,
                due_date=assignment.due_at.isoformat() if assignment.due_at else None,
                total_score=assignment.points_possible or 0.0,
            )

            # logger.info(f"Successfully created assignment: {assignment.name}")
            return {"success": True, "assignment_info": assignment_info, "failed_info": None}

        except Exception as e:
            logger.error(f"Failed to process assignment '{assignment.name}': {e}")
            return {
                "success": False,
                "assignment_info": None,
                "failed_info": SyncFailedAssignment(
                    canvas_id=assignment.id,
                    name=assignment.name,
                    course_title=course_title,
                    error=str(e),
                ),
            }

    async def _get_existing_assignments_batch(self) -> List[Any]:
        """Get all existing assignments from Notion in one batch call."""
        try:
            # Get user settings to access Notion
            user_email = getattr(self, "_current_user_email", None)
            if not user_email:
                logger.warning("No user email available for getting existing assignments")
                return []

            user_settings = await self._get_user_settings(user_email)

            # Create NotionWorkspaceManager to get existing assignments
            from app.utils.notion_helper import NotionWorkspaceManager

            if not user_settings.notion_token or not user_settings.notion_parent_page_id:
                raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

            notion_manager = NotionWorkspaceManager(user_settings.notion_token, user_settings.notion_parent_page_id)

            # Get existing assignments from Notion (single API call)
            existing_assignments = await notion_manager.get_existing_assignments()
            logger.info(f"Retrieved {len(existing_assignments)} existing assignments from Notion")

            return existing_assignments

        except Exception as e:
            logger.warning(f"Failed to get existing assignments batch: {e}")
            return []

    async def _get_assignment_groups(
        self, canvas_client: EnhancedCanvasClient, course_id: str
    ) -> Dict[int, CanvasAssignmentGroup]:
        """Get assignment groups for a course."""
        try:
            groups = await canvas_client.get_course_assignment_groups(course_id)
            return {group.id: group for group in groups}
        except Exception as e:
            logger.warning(f"Failed to get assignment groups for course {course_id}: {e}")
            return {}

    async def _get_assignments_database_id(self) -> Optional[str]:
        """Get the Notion assignments database ID."""
        try:
            # Get user settings to access Notion
            user_email = getattr(self, "_current_user_email", None)
            if not user_email:
                logger.warning("No user email available for getting assignments database ID")
                return None

            user_settings = await self._get_user_settings(user_email)

            # Create NotionWorkspaceManager to get database ID
            from app.utils.notion_helper import NotionWorkspaceManager

            if not user_settings.notion_token or not user_settings.notion_parent_page_id:
                raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

            notion_manager = NotionWorkspaceManager(user_settings.notion_token, user_settings.notion_parent_page_id)

            # Get database ID for assignments
            database_id = await notion_manager.get_database_by_name("Assignments/Exams")
            return database_id

        except Exception as e:
            logger.warning(f"Failed to get assignments database ID: {e}")
            return None

    async def _get_synced_courses(self, user_email: str) -> List[Dict[str, Any]]:
        """Get synced courses for the user."""
        try:

            user_settings = await self._get_user_settings(user_email)

            if not user_settings.notion_token or not user_settings.notion_parent_page_id:
                raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

            notion_manager = NotionWorkspaceManager(user_settings.notion_token, user_settings.notion_parent_page_id)

            synced_courses = await notion_manager.get_synced_courses()
            return [course.dict() for course in synced_courses]

        except Exception as e:
            logger.warning(f"Failed to get synced courses: {e}")
            return []

    async def _get_user_settings(self, user_email: str) -> UserSettings:
        """Get user settings from Firebase."""
        from app.core.dependencies import get_firebase_services

        firebase_services = get_firebase_services()
        return await firebase_services.get_user_settings(user_email)

    async def _store_assignment_mapping(self, canvas_id: int, notion_id: str, title: str, course_title: str):
        """Store assignment mapping in Firebase."""
        try:
            if not self.firebase_db:
                logger.warning("Firebase database not available, skipping assignment mapping storage")
                return

            assignment_mapping = {
                "canvas_assignment_id": canvas_id,
                "notion_page_id": notion_id,
                "assignment_title": title,
                "course_title": course_title,
                "created_at": datetime.now(),
                "user_email": self._current_user_email,
            }

            # Store in Firebase
            await self.firebase_db.add_assignment_mapping(assignment_mapping)
            logger.debug(f"Stored assignment mapping for: {title}")

        except Exception as e:
            logger.warning(f"Failed to store assignment mapping for {title}: {e}")
            # Don't fail the sync for this non-critical operation
