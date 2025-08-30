"""
Firebase logging service for managing sync and audit logs.

This module provides services for logging operations in Firestore,
including sync logs and audit logs with proper error handling.
"""

from typing import Any, Dict, List, Optional
from loguru import logger
from google.cloud.firestore import SERVER_TIMESTAMP
from firebase_admin import firestore

from .manager import FirebaseManager
from .constants import (
    SYNC_LOGS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    DEFAULT_SYNC_LOGS_LIMIT,
    DEFAULT_AUDIT_LOGS_LIMIT,
)

Log = Dict[str, Any]


class FirebaseLoggingService:
    """Service for managing sync and audit logs in Firebase Firestore."""

    def __init__(self, firebase_manager: FirebaseManager):
        self.firebase_manager = firebase_manager
        self.db = firebase_manager.get_database()

    async def add_sync_log(self, user_email: str, sync_data: Log) -> bool:
        """Add a sync log entry."""
        if not self._available_for_write(user_email, "sync log"):
            return True

        entry = self._make_sync_entry(user_email, sync_data)
        return self._add_log(SYNC_LOGS_COLLECTION, entry, f"sync log for {user_email}")

    async def get_sync_logs(self, user_email: str, limit: int = DEFAULT_SYNC_LOGS_LIMIT) -> List[Log]:
        """Return recent sync logs for a user."""
        return await self._get_logs(SYNC_LOGS_COLLECTION, user_email, limit)

    async def add_audit_log(
        self,
        user_email: str,
        action: str,
        target_id: str,
        metadata: Optional[Log] = None,
    ) -> bool:
        """Add an audit log entry."""
        if not self._available_for_write(user_email, "audit log"):
            return True

        entry = self._make_audit_entry(user_email, action, target_id, metadata)
        return self._add_log(AUDIT_LOGS_COLLECTION, entry, f"audit '{action}' for {user_email}")

    async def get_audit_logs(self, user_email: str, limit: int = DEFAULT_AUDIT_LOGS_LIMIT) -> List[Log]:
        """Return recent audit logs for a user."""
        return await self._get_logs(AUDIT_LOGS_COLLECTION, user_email, limit)

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _available_for_write(self, user_email: str, operation: str) -> bool:
        """Checks write availability; logs and returns False in dev mode."""
        if not self.firebase_manager.is_available():
            logger.info(f"Firebase not available, skipping {operation} for {user_email}")
            return False
        if not self.db:
            logger.warning("Firestore client not initialized; write skipped")
            return False
        return True

    def _available_for_read(self, user_email: str, operation: str) -> bool:
        """Checks read availability; returns False if not possible."""
        if not self.firebase_manager.is_available():
            logger.info(f"Firebase not available, skipping {operation} for {user_email}")
            return False
        if not self.db:
            logger.warning("Firestore client not initialized; read not possible")
            return False
        return True

    def _add_log(self, collection: str, entry: Log, context: str) -> bool:
        try:
            if not self.db:
                logger.warning("Firebase database is not available")
                return False

            self.db.collection(collection).add(entry)
            logger.info(f"{context} added")
            return True
        except Exception as e:
            logger.error(f"Failed to add {context}: {e}")
            return False

    async def _get_logs(self, collection: str, user_email: str, limit: int) -> List[Log]:
        if not self._available_for_read(user_email, f"get {collection}"):
            return []
        try:

            if not self.db:
                logger.warning("Firebase database is not available")
                return []

            query = (
                self.db.collection(collection).where("user_email", "==", user_email).order_by("timestamp").limit(limit)
            )
            return self._execute_log_query(query)
        except Exception as e:
            logger.error(f"Failed to get logs from {collection} for {user_email}: {e}")
            return []

    @staticmethod
    def _make_sync_entry(user_email: str, data: Log) -> Log:
        entry = dict(data)
        entry["user_email"] = user_email
        entry["timestamp"] = SERVER_TIMESTAMP
        return entry

    @staticmethod
    def _make_audit_entry(user_email: str, action: str, target_id: str, metadata: Optional[Log]) -> Log:
        return {
            "user_email": user_email,
            "action": action,
            "target_id": target_id,
            "metadata": metadata or {},
            "timestamp": SERVER_TIMESTAMP,
        }

    @staticmethod
    def _execute_log_query(query) -> List[Log]:
        # Compact stream → list transform; each item includes document ID.
        return [{"id": d.id, **d.to_dict()} for d in query.stream()]
