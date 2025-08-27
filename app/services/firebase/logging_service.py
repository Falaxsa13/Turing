"""
Firebase logging service for managing sync and audit logs.

This module provides services for logging operations in Firestore,
including sync logs and audit logs with proper error handling.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from firebase_admin import firestore

from .manager import FirebaseManager
from .constants import (
    SYNC_LOGS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    DEFAULT_SYNC_LOGS_LIMIT,
    DEFAULT_AUDIT_LOGS_LIMIT,
)


class FirebaseLoggingService:
    """
    Service for managing logs in Firebase Firestore.

    This service handles sync logs and audit logs operations
    with proper error handling and development mode support.
    """

    def __init__(self, firebase_manager: FirebaseManager):
        """
        Initialize the logging service.

        Args:
            firebase_manager: Initialized Firebase manager instance
        """
        self.firebase_manager = firebase_manager
        self.db = firebase_manager.get_database()

    async def add_sync_log(self, user_email: str, sync_data: Dict[str, Any]) -> bool:
        """
        Add a sync log entry to Firestore.

        Args:
            user_email: User's email address
            sync_data: Sync operation data to log

        Returns:
            True if successful, False otherwise
        """
        if not self.firebase_manager.is_available():
            logger.warning(f"Firebase not available, skipping sync log for {user_email}")
            return True  # Return True for development mode

        if self.db is None:
            logger.warning("Firebase database is not available")
            return False

        try:
            log_entry = self._create_sync_log_entry(user_email, sync_data)
            self.db.collection(SYNC_LOGS_COLLECTION).add(log_entry)
            logger.info(f"Sync log added for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to add sync log for {user_email}: {e}")
            return False

    async def get_sync_logs(self, user_email: str, limit: int = DEFAULT_SYNC_LOGS_LIMIT) -> List[Dict[str, Any]]:
        """
        Get recent sync logs for a user.

        Args:
            user_email: User's email address
            limit: Maximum number of logs to retrieve

        Returns:
            List of sync log dictionaries
        """
        if not self._check_firebase_available(user_email, "get sync logs"):
            return []

        try:
            query = (
                self.db.collection(SYNC_LOGS_COLLECTION)
                .where("user_email", "==", user_email)
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            return self._execute_log_query(query)

        except Exception as e:
            logger.error(f"Failed to get sync logs for {user_email}: {e}")
            return []

    async def add_audit_log(
        self, user_email: str, action: str, target_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add an audit log entry to Firestore.

        Args:
            user_email: User's email address
            action: Action performed
            target_id: ID of the target object
            metadata: Additional metadata for the action

        Returns:
            True if successful, False otherwise
        """
        if not self._check_firebase_available(user_email, "audit log"):
            return True  # Return True for development mode

        try:
            log_entry = self._create_audit_log_entry(user_email, action, target_id, metadata)
            self.db.collection(AUDIT_LOGS_COLLECTION).add(log_entry)
            logger.info(f"Audit log added: {action} for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to add audit log for {user_email}: {e}")
            return False

    async def get_audit_logs(self, user_email: str, limit: int = DEFAULT_AUDIT_LOGS_LIMIT) -> List[Dict[str, Any]]:
        """
        Get recent audit logs for a user.

        Args:
            user_email: User's email address
            limit: Maximum number of logs to retrieve

        Returns:
            List of audit log dictionaries
        """
        if not self._check_firebase_available(user_email, "get audit logs"):
            return []

        try:
            query = (
                self.db.collection(AUDIT_LOGS_COLLECTION)
                .where("user_email", "==", user_email)
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            return self._execute_log_query(query)

        except Exception as e:
            logger.error(f"Failed to get audit logs for {user_email}: {e}")
            return []

    def _create_sync_log_entry(self, user_email: str, sync_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a sync log entry with proper structure.

        Args:
            user_email: User's email address
            sync_data: Sync operation data

        Returns:
            Formatted sync log entry
        """
        log_entry = sync_data.copy()
        log_entry["user_email"] = user_email
        log_entry["timestamp"] = firestore.SERVER_TIMESTAMP
        return log_entry

    def _create_audit_log_entry(
        self, user_email: str, action: str, target_id: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create an audit log entry with proper structure.

        Args:
            user_email: User's email address
            action: Action performed
            target_id: ID of the target object
            metadata: Additional metadata

        Returns:
            Formatted audit log entry
        """
        return {
            "user_email": user_email,
            "action": action,
            "target_id": target_id,
            "metadata": metadata or {},
            "timestamp": firestore.SERVER_TIMESTAMP,
        }

    def _execute_log_query(self, query) -> List[Dict[str, Any]]:
        """
        Execute a log query and format the results.

        Args:
            query: Firestore query object

        Returns:
            List of formatted log dictionaries
        """
        docs = query.stream()
        logs = []

        for doc in docs:
            log_data = doc.to_dict()
            log_data["id"] = doc.id
            logs.append(log_data)

        return logs

    def _check_firebase_available(self, user_email: str, operation: str) -> bool:
        """
        Check if Firebase is available for the operation.

        Args:
            user_email: User email for logging
            operation: Operation description for logging

        Returns:
            True if Firebase is available, False otherwise
        """
        if not self.firebase_manager.is_available():
            logger.info(f"Firebase not available, skipping {operation} for {user_email}")
            return False
        return True
