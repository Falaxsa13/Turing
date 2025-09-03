"""
Firebase user service for managing user settings and preferences.

This module provides services for user-related operations in Firestore,
including settings management and preferences handling.
"""

from typing import Dict, Any, Optional
from loguru import logger

from .manager import FirebaseManager
from .constants import USER_SETTINGS_COLLECTION, USER_PREFERENCES_COLLECTION
from app.models.user_settings import UserPreferences, UserSettings


class FirebaseUserService:
    """
    Service for managing user data in Firebase Firestore.

    This service handles user settings and preferences operations
    with proper error handling and development mode support.
    """

    def __init__(self, firebase_manager: FirebaseManager):
        """
        Initialize the user service.

        Args:
            firebase_manager: Initialized Firebase manager instance
        """
        self.firebase_manager = firebase_manager
        self.db = firebase_manager.get_database()

    async def get_user_settings(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Get user settings from Firestore.

        Args:
            user_email: User's email address (used as document ID)

        Returns:
            User settings dictionary or None if not found/error
        """
        if not self.firebase_manager.is_available():
            logger.warning(f"Firebase not available, skipping get user settings for {user_email}")
            return None

        if self.db is None:
            logger.warning("Firebase database is not available")
            return None

        try:
            doc_ref = self.db.collection(USER_SETTINGS_COLLECTION).document(user_email)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()

                if data is None:
                    logger.warning(f"User settings not found for {user_email}")
                    return None

                data["user_email"] = user_email  # Add the document ID as user_email
                return data
            return None

        except Exception as e:
            logger.error(f"Failed to get user settings for {user_email}: {e}")
            return None

    async def create_or_update_user_settings(self, user_email: str, settings_data: Dict[str, Any]) -> bool:
        """
        Create or update user settings in Firestore.

        Args:
            user_email: User's email address (used as document ID)
            settings_data: Settings data to save

        Returns:
            True if successful, False otherwise
        """
        if not self.firebase_manager.is_available():
            logger.warning(f"Firebase not available, skipping update user settings for {user_email}")
            return True  # Return True for development mode

        if self.db is None:
            logger.warning("Firebase database is not available")
            return False

        try:
            # Remove user_email from data if present (it's the document ID)
            settings_data = settings_data.copy()  # Avoid modifying original
            settings_data.pop("user_email", None)

            doc_ref = self.db.collection(USER_SETTINGS_COLLECTION).document(user_email)
            doc_ref.set(settings_data, merge=True)

            logger.info(f"User settings updated for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to update user settings for {user_email}: {e}")
            return False

    async def get_user_preferences(self, user_email: str) -> Optional[UserPreferences]:
        """
        Get user preferences from Firestore.

        Args:
            user_email: User's email address (used as document ID)

        Returns:
            User preferences dictionary or None if not found/error
        """
        if not self.firebase_manager.is_available():
            logger.warning(f"Firebase not available, skipping get user preferences for {user_email}")
            return None

        if self.db is None:
            logger.warning("Firebase database is not available")
            return None

        try:
            doc_ref = self.db.collection(USER_PREFERENCES_COLLECTION).document(user_email)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()

                if data is None:
                    logger.warning(f"User preferences not found for {user_email}")
                    return None

                data["user_email"] = user_email
                return UserPreferences(**data)

            return None

        except Exception as e:
            logger.error(f"Failed to get user preferences for {user_email}: {e}")
            return None

    async def save_user_preferences(self, user_email: str, preferences: UserPreferences) -> bool:
        """Save user preferences to Firestore."""

        if not self.firebase_manager.is_available():
            logger.warning(f"Firebase not available, skipping save user preferences for {user_email}")
            return False

        if self.db is None:
            logger.warning("Firebase database is not available")
            return False

        try:
            # Remove user_email from preferences if present (it's the document ID)
            preferences_data = preferences.model_dump()  # Avoid modifying original
            preferences_data.pop("user_email", None)

            doc_ref = self.db.collection(USER_PREFERENCES_COLLECTION).document(user_email)
            doc_ref.set(preferences_data, merge=True)

            return True

        except Exception as e:
            logger.error(f"Failed to save user preferences for {user_email}: {e}")
            return False

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
            logger.warning(f"Firebase not available, skipping {operation} for {user_email}")
            return False
        return True
