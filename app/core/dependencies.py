"""
Core dependency injection for the application.

This module provides clean dependency injection functions for Firebase services
and other core application dependencies.
"""

from functools import lru_cache
from firebase_admin import auth
from app.models.user_settings import UserPreferences, UserSettings
from app.services.firebase import FirebaseManager, FirebaseUserService, FirebaseLoggingService


# Global Firebase manager (singleton)
@lru_cache()
def get_firebase_manager() -> FirebaseManager:
    """Get the global Firebase manager instance."""
    return FirebaseManager()


def get_firebase_user_service() -> FirebaseUserService:
    """Dependency to get Firebase user service."""
    return FirebaseUserService(get_firebase_manager())


def get_firebase_logging_service() -> FirebaseLoggingService:
    """Dependency to get Firebase logging service."""
    return FirebaseLoggingService(get_firebase_manager())


class FirebaseServices:
    """
    Unified Firebase services container.

    This provides a single dependency that gives access to all Firebase services
    while maintaining clean separation of concerns.
    """

    def __init__(self):
        self._manager = get_firebase_manager()
        self._user_service = get_firebase_user_service()
        self._logging_service = get_firebase_logging_service()

    @property
    def manager(self) -> FirebaseManager:
        """Get the Firebase manager."""
        return self._manager

    @property
    def user(self) -> FirebaseUserService:
        """Get the Firebase user service."""
        return self._user_service

    @property
    def logging(self) -> FirebaseLoggingService:
        """Get the Firebase logging service."""
        return self._logging_service

    # Convenience properties for backward compatibility
    @property
    def db(self):
        """Get Firestore database client."""
        return self._manager.get_database()

    @property
    def firebase_available(self) -> bool:
        """Check if Firebase is available."""
        return self._manager.is_available()

    # Authentication methods
    def verify_firebase_token(self, id_token: str):
        """Verify Firebase ID token and return user info."""
        if not self._manager.is_available():
            return None
        try:
            return auth.verify_id_token(id_token)
        except Exception:
            return None

    # User service delegation
    async def get_user_settings(self, user_email: str) -> UserSettings:
        """Get user settings from Firestore."""
        settings_dict = await self._user_service.get_user_settings(user_email)
        if not settings_dict:
            raise ValueError("User settings data is not available")

        return UserSettings(**settings_dict)

    async def create_or_update_user_settings(self, user_email: str, settings_data: dict) -> bool:
        """Create or update user settings."""
        return await self._user_service.create_or_update_user_settings(user_email, settings_data)

    async def get_user_preferences(self, user_email: str) -> UserPreferences:
        """Get user preferences with fallback defaults."""
        preferences: UserPreferences | None = await self._user_service.get_user_preferences(user_email)

        if preferences:
            return preferences

        return UserPreferences(
            user_email=user_email,
            dashboard_layout="grid",
            default_view="assignments",
            notifications_enabled=True,
            theme="light",
            sync_frequency="manual",
            show_completed_assignments=True,
        )

    async def save_user_preferences(self, user_email: str, preferences: UserPreferences) -> bool:
        """Save user preferences."""
        return await self._user_service.save_user_preferences(user_email, preferences)

    # Logging service delegation
    async def add_sync_log(self, user_email: str, sync_data: dict) -> bool:
        """Add a sync log entry."""
        return await self._logging_service.add_sync_log(user_email, sync_data)

    async def get_sync_logs(self, user_email: str, limit: int = 10):
        """Get recent sync logs."""
        return await self._logging_service.get_sync_logs(user_email, limit)

    async def add_audit_log(self, user_email: str, action: str, target_id: str, metadata: dict = {}) -> bool:
        """Add an audit log entry."""
        return await self._logging_service.add_audit_log(user_email, action, target_id, metadata or {})

    async def get_audit_logs(self, user_email: str, limit: int = 50):
        """Get recent audit logs."""
        return await self._logging_service.get_audit_logs(user_email, limit)

    # Assignment mapping (if still needed)
    async def add_assignment_mapping(self, assignment_mapping: dict) -> bool:
        """Add assignment mapping."""
        if not self._manager.is_available():
            return False

        db = self._manager.get_database()
        if db is None:
            return False

        try:
            db.collection("assignment_mappings").add(assignment_mapping)
            return True
        except Exception:
            return False


def get_firebase_services() -> FirebaseServices:
    """Dependency to get unified Firebase services."""
    return FirebaseServices()
