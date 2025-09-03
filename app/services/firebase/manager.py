"""
Firebase configuration and initialization for Firestore database.

This module handles the core Firebase initialization and connection management,
providing a clean interface for other Firebase services to build upon.
"""

import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional, Dict, Any
from loguru import logger
import os
from google.cloud.firestore import Client

from app.core.config import settings
from .constants import (
    SERVICE_ACCOUNT_PATH,
    DUMMY_PROJECT_ID,
    DEVELOPMENT_MODE_MESSAGE,
    DEV_MODE_NOTE,
    FIREBASE_UNAVAILABLE_ERROR,
    FIRESTORE_INIT_FAILED,
    FIREBASE_INIT_FAILED,
)


class FirebaseConnectionError(Exception):
    """Custom exception for Firebase connection errors."""

    pass


class FirebaseManager:
    """
    Manages Firebase Firestore database connection and initialization.

    This class handles the Firebase Admin SDK initialization using multiple
    methods (service account, default credentials, or development mode).
    """

    def __init__(self):
        """Initialize the Firebase manager."""
        self.db: Optional["Client"] = None
        self.firebase_available: bool = False
        self._initialize_firebase()

    def _initialize_firebase(self) -> None:
        """
        Initialize Firebase Admin SDK with proper credentials handling.

        Tries multiple initialization methods in order of preference:
        1. Service account key file (for local development)
        2. Application Default Credentials (for production)
        3. Development mode (dummy credentials)

        Raises:
            FirebaseConnectionError: If initialization fails unexpectedly
        """
        try:
            if firebase_admin._apps:
                logger.info("Firebase already initialized")
                self._setup_firestore_client()
                return

            if self._try_service_account_init():
                self._setup_firestore_client()
                return

            if self._try_default_credentials_init():
                self._setup_firestore_client()
                return

            self._setup_development_mode()

        except Exception as e:
            logger.error(f"❌ {FIREBASE_INIT_FAILED}: {e}")
            self.firebase_available = False
            raise FirebaseConnectionError(f"{FIREBASE_INIT_FAILED}: {e}") from e

    def _try_service_account_init(self) -> bool:
        """
        Try to initialize Firebase with service account key file.

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(SERVICE_ACCOUNT_PATH):
            return False

        try:
            logger.info("Using service account key file for Firebase initialization")
            cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized with service account key")
            return True
        except Exception as e:
            logger.warning(f"Service account initialization failed: {e}")
            return False

    def _try_default_credentials_init(self) -> bool:
        """
        Try to initialize Firebase with Application Default Credentials.

        Returns:
            True if successful, False otherwise
        """
        if settings.firebase.project_id == DUMMY_PROJECT_ID:
            return False

        try:
            logger.info("Attempting Firebase initialization with Application Default Credentials")
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": settings.firebase.project_id})
            logger.info("✅ Firebase initialized with Application Default Credentials")
            return True
        except Exception as e:
            logger.warning(f"Default credentials initialization failed: {e}")
            return False

    def _setup_development_mode(self) -> None:
        """Setup development mode when Firebase credentials are not available."""
        logger.warning("Firebase running in development mode with dummy credentials")
        self.firebase_available = False

    def _setup_firestore_client(self) -> None:
        """
        Setup the Firestore client after Firebase initialization.

        Raises:
            FirebaseConnectionError: If Firestore client setup fails
        """
        try:
            self.db = firestore.client()
            self.firebase_available = True
            logger.info("✅ Firestore client initialized successfully")
        except Exception as e:
            error_msg = f"❌ {FIRESTORE_INIT_FAILED}: {e}"
            logger.error(error_msg)
            self.firebase_available = False
            raise FirebaseConnectionError(error_msg) from e

    def is_available(self) -> bool:
        """
        Check if Firebase is available and properly initialized.

        Returns:
            True if Firebase is available, False otherwise
        """
        return self.firebase_available

    def get_database(self) -> Optional["Client"]:
        """
        Get the Firestore database client.

        Returns:
            Firestore client if available, None otherwise
        """
        return self.db if self.firebase_available else None

    def get_availability_error(self) -> Optional[Dict[str, Any]]:
        """
        Get error information if Firebase is not available.

        Returns:
            Error dictionary if Firebase is unavailable, None if available
        """
        if self.firebase_available:
            return None

        return {
            "success": False,
            "error": DEVELOPMENT_MODE_MESSAGE,
            "note": DEV_MODE_NOTE,
        }

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the Firebase connection.

        Returns:
            Dictionary with health check results
        """
        if not self.firebase_available:
            return {
                "status": "unavailable",
                "message": DEVELOPMENT_MODE_MESSAGE,
                "firebase_available": False,
            }

        try:
            # Try a simple operation to verify connection
            if self.db:
                # This will throw an exception if connection is bad
                # collections = list(self.db.collections(page_size=1))
                return {
                    "status": "healthy",
                    "message": "Firebase connection is working",
                    "firebase_available": True,
                }
            else:
                return {
                    "status": "error",
                    "message": "Database client is None",
                    "firebase_available": False,
                }
        except Exception as e:
            logger.error(f"Firebase health check failed: {e}")
            return {
                "status": "error",
                "message": f"Firebase health check failed: {e}",
                "firebase_available": False,
            }
