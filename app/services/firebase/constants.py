"""
Constants for Firebase services.
"""

# Collection names
USER_SETTINGS_COLLECTION = "user_settings"
USER_PREFERENCES_COLLECTION = "user_preferences"
SYNC_LOGS_COLLECTION = "sync_logs"
AUDIT_LOGS_COLLECTION = "audit_logs"

# File paths
SERVICE_ACCOUNT_PATH = "./firebase-keys/service-account.json"

# Default limits
DEFAULT_SYNC_LOGS_LIMIT = 10
DEFAULT_AUDIT_LOGS_LIMIT = 50

# Development constants
DUMMY_PROJECT_ID = "dummy-project-id"
DEVELOPMENT_MODE_MESSAGE = "Firebase not available. Please configure Firebase credentials."
DEV_MODE_NOTE = "Running in development mode without Firebase"

# Error messages
FIREBASE_UNAVAILABLE_ERROR = "Firebase not available"
FIRESTORE_INIT_FAILED = "Firestore client initialization failed"
FIREBASE_INIT_FAILED = "Firebase initialization failed"
