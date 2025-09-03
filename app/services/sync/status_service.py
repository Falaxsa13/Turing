from datetime import datetime
from typing import List
from loguru import logger

from app.core.exceptions import ValidationError, DatabaseError
from app.utils.notion_helper import NotionWorkspaceManager
from app.models.user_settings import UserSettings, UserPreferences
from app.schemas.sync import (
    SyncStatusResponse,
    SetupStatus,
    SyncHistory,
    SyncData,
    NotionCourseInfo,
    NotionAssignmentInfo,
    SyncedCoursesResponse,
    SyncedAssignmentsResponse,
)


class SyncStatusService:
    def __init__(self, firebase_db):
        self.firebase_db = firebase_db
        self._user_settings_cache = {}
        self._notion_manager_cache = {}

    def _convert_datetime_to_string(self, dt_value):
        """Convert datetime objects to ISO format strings"""
        if dt_value is None:
            return None
        if isinstance(dt_value, datetime):
            return dt_value.isoformat()
        try:
            return dt_value.isoformat()
        except:
            return str(dt_value)

    async def _get_validated_user_settings(self, user_email: str) -> UserSettings:
        """Fetch and validate user settings. This is a common operation across all methods"""
        if user_email in self._user_settings_cache:
            return self._user_settings_cache[user_email]

        user_settings: UserSettings = await self.firebase_db.get_user_settings(user_email)

        if not user_settings:
            raise DatabaseError("User not found. Please run /setup/init first.")

        if not user_settings.notion_token or not user_settings.notion_parent_page_id:
            raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

        self._user_settings_cache[user_email] = user_settings
        return user_settings

    async def _get_notion_manager(self, user_email: str) -> NotionWorkspaceManager:
        """Get or create a NotionWorkspaceManager for the user."""
        if user_email in self._notion_manager_cache:
            return self._notion_manager_cache[user_email]

        user_settings: UserSettings = await self._get_validated_user_settings(user_email)

        if not user_settings.notion_token or not user_settings.notion_parent_page_id:
            raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

        notion_manager = NotionWorkspaceManager(user_settings.notion_token, user_settings.notion_parent_page_id)
        self._notion_manager_cache[user_email] = notion_manager

        return notion_manager

    async def get_synced_courses(self, user_email: str) -> SyncedCoursesResponse:
        """Get all courses that have been synced from Canvas to Notion."""
        try:
            notion_manager = await self._get_notion_manager(user_email)
            synced_courses = await notion_manager.get_synced_courses()

            return SyncedCoursesResponse(
                success=True,
                message=f"Found {len(synced_courses)} synced courses",
                courses_count=len(synced_courses),
                courses=synced_courses,
                note="These courses have Canvas IDs and were synced from Canvas",
            )

        except Exception as e:
            logger.error(f"Failed to get synced courses: {e}")
            raise e

    async def get_synced_assignments(self, user_email: str) -> SyncedAssignmentsResponse:
        """Get all assignments that have been synced from Canvas to Notion."""
        try:
            notion_manager = await self._get_notion_manager(user_email)
            synced_assignments = await notion_manager.get_existing_assignments()

            return SyncedAssignmentsResponse(
                success=True,
                message=f"Found {len(synced_assignments)} synced assignments",
                assignments_count=len(synced_assignments),
                assignments=synced_assignments,
                note="These assignments have Canvas IDs and were synced from Canvas",
            )

        except Exception as e:
            logger.error(f"Failed to get synced assignments: {e}")
            raise e

    async def get_sync_status(self, user_email: str) -> SyncStatusResponse:
        """Get overall sync status including course and assignment counts."""
        try:
            user_settings = await self._get_validated_user_settings(user_email)
            notion_manager = await self._get_notion_manager(user_email)

            synced_courses: List[NotionCourseInfo] = await notion_manager.get_synced_courses()
            synced_assignments: List[NotionAssignmentInfo] = await notion_manager.get_existing_assignments()

            recent_sync_logs = await self.firebase_db.get_sync_logs(user_email, limit=5)

            last_course_sync = self._convert_datetime_to_string(user_settings.last_canvas_sync)
            last_assignment_sync = self._convert_datetime_to_string(user_settings.last_assignment_sync)

            return SyncStatusResponse(
                success=True,
                message=f"Sync status retrieved for {user_email}",
                user_email=user_email,
                setup_status=SetupStatus(
                    has_canvas=bool(user_settings.canvas_base_url and user_settings.canvas_pat),
                    has_notion=bool(user_settings.notion_token and user_settings.notion_parent_page_id),
                ),
                sync_history=SyncHistory(
                    last_course_sync=last_course_sync,
                    last_assignment_sync=last_assignment_sync,
                ),
                sync_data=SyncData(
                    courses_synced=len(synced_courses),
                    assignments_synced=len(synced_assignments),
                ),
                courses=synced_courses,
                assignments=synced_assignments,
                recent_sync_logs=recent_sync_logs,
                note="Complete overview of your Canvas-to-Notion sync status",
            )

        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            raise e
