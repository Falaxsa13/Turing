import logging

logger = logging.getLogger(__name__)


class SyncLogService:
    def __init__(self, firebase_db):
        self.firebase_db = firebase_db

    async def get_sync_logs(self, user_email: str, limit: int = 20):
        """Get sync logs for the user."""
        try:
            # Get sync logs
            sync_logs = await self.firebase_db.get_sync_logs(user_email, limit)

            return {
                "success": True,
                "message": f"Found {len(sync_logs)} sync logs",
                "logs_count": len(sync_logs),
                "logs": sync_logs,
                "note": "Recent sync activity logs",
            }

        except Exception as e:
            logger.error(f"Failed to get sync logs: {e}")
            raise e

    async def get_audit_logs(self, user_email: str, limit: int = 50):
        """Get audit logs for the user."""
        try:
            # Get audit logs
            audit_logs = await self.firebase_db.get_audit_logs(user_email, limit)

            return {
                "success": True,
                "message": f"Found {len(audit_logs)} audit logs",
                "logs_count": len(audit_logs),
                "logs": audit_logs,
                "note": "Recent user activity audit logs",
            }

        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            raise e
