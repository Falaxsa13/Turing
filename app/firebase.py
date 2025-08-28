"""
Firebase configuration and management for the Turing Project.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from firebase_admin import credentials, firestore, initialize_app, _apps, auth
from app.core.config import settings
from app.models.user_settings import UserSettings, AuditLog, UserPreferences
from app.schemas.sync import SyncLog

# Module-level logger (industry standard)
logger = logging.getLogger(__name__)


class FirebaseManager:
    """Manages Firebase Firestore database operations"""

    def __init__(self):
        self.db = None
        self.firebase_available = False
        self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK with proper credentials handling"""
        try:
            # Check if Firebase is already initialized
            if not _apps:
                # Try different initialization methods in order of preference

                # Method 1: Service account key file (for local development)
                service_account_path = "./firebase-keys/service-account.json"
                if os.path.exists(service_account_path):
                    logger.info("Using service account key file for Firebase initialization")
                    cred = credentials.Certificate(service_account_path)

                    # Read project ID from service account file instead of config
                    import json

                    with open(service_account_path, "r") as f:
                        service_account_data = json.load(f)
                        project_id = service_account_data.get("project_id")

                    if project_id:
                        initialize_app(
                            cred,
                            {
                                "projectId": project_id,
                            },
                        )
                        logger.info(f"Firebase initialized with service account key for project: {project_id}")
                    else:
                        logger.error("Service account file missing project_id")
                        self.firebase_available = False
                        return

                # Method 2: Application Default Credentials (for production)
                elif settings.firebase.project_id != "dummy-project-id":
                    logger.info("Attempting Firebase initialization with Application Default Credentials")
                    initialize_app(
                        credentials.ApplicationDefault(),
                        {
                            "projectId": settings.firebase.project_id,
                        },
                    )
                    logger.info("Firebase initialized with Application Default Credentials")

                # Method 3: Development mode (dummy credentials)
                else:
                    logger.warning("Firebase running in development mode with dummy credentials")
                    self.firebase_available = False
                    return

            # Get Firestore client
            try:
                self.db = firestore.client()
                self.firebase_available = True
                logger.info("✅ Firestore client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Firestore client initialization failed: {e}")
                self.firebase_available = False

        except Exception as e:
            logger.error(f"❌ Firebase initialization failed: {e}")
            self.firebase_available = False

    def _check_firebase_available(self):
        """Check if Firebase is available, return error if not"""
        if not self.firebase_available:
            return {
                "success": False,
                "error": "Firebase not available. Please configure Firebase credentials.",
                "note": "Running in development mode without Firebase",
            }
        return None

    async def get_user_settings(self, user_email: str) -> Optional[Dict[str, Any]]:
        """Get user settings from Firestore"""
        error = self._check_firebase_available()
        if error:
            # Return empty dict for development mode
            logger.warning(f"Firebase not available, returning empty user settings for {user_email}")
            return None

        if self.db is None:
            return None

        try:
            doc_ref = self.db.collection("user_settings").document(user_email)
            doc = doc_ref.get()

            if doc.exists:
                data = doc.to_dict()
                if not data:
                    return None

                data["user_email"] = user_email  # Add the document ID as user_email
                return data
            return None

        except Exception as e:
            logger.error(f"Failed to get user settings for {user_email}: {e}")
            return None

    async def create_or_update_user_settings(self, user_email: str, settings_data: Dict[str, Any]) -> bool:
        """Create or update user settings in Firestore"""
        error = self._check_firebase_available()
        if error:
            logger.warning(f"Firebase not available, skipping user settings update for {user_email}")
            return True  # Return True for development mode

        try:
            # Remove user_email from data if present (it's the document ID)
            settings_data.pop("user_email", None)

            doc_ref = self.db.collection("user_settings").document(user_email)
            doc_ref.set(settings_data, merge=True)

            logger.info(f"User settings updated for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to update user settings for {user_email}: {e}")
            return False

    async def add_sync_log(self, user_email: str, sync_data: Dict[str, Any]) -> bool:
        """Add a sync log entry"""
        error = self._check_firebase_available()
        if error:
            logger.info(f"Firebase not available, skipping sync log for {user_email}")
            return True

        try:
            sync_data["user_email"] = user_email
            sync_data["timestamp"] = firestore.SERVER_TIMESTAMP

            self.db.collection("sync_logs").add(sync_data)
            logger.info(f"Sync log added for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to add sync log for {user_email}: {e}")
            return False

    async def get_sync_logs(self, user_email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync logs for a user"""
        error = self._check_firebase_available()
        if error:
            return []

        try:
            query = (
                self.db.collection("sync_logs")
                .where("user_email", "==", user_email)
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = query.stream()
            logs = []

            for doc in docs:
                log_data = doc.to_dict()
                log_data["id"] = doc.id
                logs.append(log_data)

            return logs

        except Exception as e:
            logger.error(f"Failed to get sync logs for {user_email}: {e}")
            return []

    async def add_audit_log(
        self, user_email: str, action: str, target_id: str, metadata: Dict[str, Any] = None
    ) -> bool:
        """Add an audit log entry"""
        error = self._check_firebase_available()
        if error:
            logger.info(f"Firebase not available, skipping audit log for {user_email}")
            return True

        try:
            audit_data = {
                "user_email": user_email,
                "action": action,
                "target_id": target_id,
                "metadata": metadata or {},
                "timestamp": firestore.SERVER_TIMESTAMP,
            }

            self.db.collection("audit_logs").add(audit_data)
            logger.info(f"Audit log added: {action} for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to add audit log for {user_email}: {e}")
            return False

    async def get_audit_logs(self, user_email: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent audit logs for a user"""
        error = self._check_firebase_available()
        if error:
            return []

        try:
            query = (
                self.db.collection("audit_logs")
                .where("user_email", "==", user_email)
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = query.stream()
            logs = []

            for doc in docs:
                log_data = doc.to_dict()
                log_data["id"] = doc.id
                logs.append(log_data)

            return logs

        except Exception as e:
            logger.error(f"Failed to get audit logs for {user_email}: {e}")
            return []

    async def save_user_preferences(self, user_email: str, preferences: Dict[str, Any]) -> bool:
        """Save user preferences"""
        error = self._check_firebase_available()
        if error:
            logger.warning(f"Firebase not available, skipping user preferences for {user_email}")
            return True

        try:
            doc_ref = self.db.collection("user_preferences").document(user_email)
            doc_ref.set(preferences, merge=True)

            logger.info(f"User preferences saved for {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to save user preferences for {user_email}: {e}")
            return False

    async def get_user_preferences(self, user_email: str) -> Optional[Dict[str, Any]]:
        """Get user preferences"""
        error = self._check_firebase_available()
        if error:
            # Return default preferences for development
            return {
                "dashboard_layout": "grid",
                "default_view": "assignments",
                "notifications_enabled": True,
                "theme": "light",
            }

        try:
            doc_ref = self.db.collection("user_preferences").document(user_email)
            doc = doc_ref.get()

            if doc.exists:
                return doc.to_dict()
            else:
                # Return default preferences
                return {
                    "dashboard_layout": "grid",
                    "default_view": "assignments",
                    "notifications_enabled": True,
                    "theme": "light",
                }

        except Exception as e:
            logger.error(f"Failed to get user preferences for {user_email}: {e}")
            return {}

    def verify_firebase_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token and return user info"""
        error = self._check_firebase_available()
        if error:
            logger.warning("Firebase not available, cannot verify token")
            return None

        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Failed to verify Firebase token: {e}")
            return None


# Global Firebase manager instance
firebase_manager = FirebaseManager()


def get_firebase_db():
    """Dependency to get Firebase database manager"""
    return firebase_manager
