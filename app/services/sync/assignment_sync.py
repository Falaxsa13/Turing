from datetime import datetime, timezone
from app.core.exceptions import ValidationError, DatabaseError
from app.services.sync.coordinator import SyncCoordinator
from app.models.user_settings import UserSettings
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AssignmentSyncService:
    def __init__(self, firebase_db):
        self.firebase_db = firebase_db

    async def sync_assignments(self, user_email: str):
        """Fetch all assignments from previously synced Canvas courses and create them in Notion."""
        try:
            # Get user settings
            user_settings: Optional[Dict[str, Any]] = await self.firebase_db.get_user_settings(user_email)

            if not user_settings:
                raise DatabaseError("User not found. Please run /setup/init first.")

            # Validate required settings
            if not user_settings.get("canvas_base_url") or not user_settings.get("canvas_pat"):
                raise ValidationError("Canvas credentials not configured. Please set Canvas base URL and PAT.")

            if not user_settings.get("notion_token") or not user_settings.get("notion_parent_page_id"):
                raise ValidationError("Notion credentials not configured. Please set Notion token and parent page ID.")

            # Create sync coordinator and perform assignment sync
            logger.info(f"Starting assignment sync for user: {user_email}")

            sync_coordinator = SyncCoordinator(
                canvas_base_url=user_settings["canvas_base_url"],
                canvas_token=user_settings["canvas_pat"],
                notion_token=user_settings["notion_token"],
                notion_parent_page_id=user_settings["notion_parent_page_id"],
            )

            sync_result = await sync_coordinator.sync_assignments_for_courses()

            # Update last sync time if successful and log sync
            if sync_result["success"] and sync_result["assignments_created"] > 0:
                now = datetime.now(timezone.utc)
                await self.firebase_db.create_or_update_user_settings(
                    user_email,
                    {
                        "last_assignment_sync": now,
                        "updated_at": now,
                    },
                )

            # Add sync log
            status = "success" if sync_result["success"] else "failed"
            await self.firebase_db.add_sync_log(
                user_email,
                {
                    "sync_type": "assignments",
                    "status": status,
                    "items_processed": sync_result["assignments_found"],
                    "items_created": sync_result["assignments_created"],
                    "items_failed": sync_result["assignments_failed"],
                    "items_skipped": sync_result["assignments_skipped"],
                    "metadata": {
                        "courses_processed": sync_result["courses_processed"],
                        "assignments": sync_result["created_assignments"][:10],  # Limit logged data
                    },
                },
            )

            logger.info(f"Updated last assignment sync time for user: {user_email}")

            return sync_result

        except Exception as e:
            logger.error(f"Unexpected error during assignment sync: {e}")

            # Log failed sync
            try:
                await self.firebase_db.add_sync_log(
                    user_email,
                    {
                        "sync_type": "assignments",
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
