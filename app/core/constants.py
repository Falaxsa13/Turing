"""
Constants and configuration values for the Turing Project.
"""

from enum import Enum
from typing import Final

# API Constants
API_VERSION: Final[str] = "v1"
API_PREFIX: Final[str] = f"/api/{API_VERSION}"

# HTTP Status Codes
HTTP_OK: Final[int] = 200
HTTP_CREATED: Final[int] = 201
HTTP_BAD_REQUEST: Final[int] = 400
HTTP_UNAUTHORIZED: Final[int] = 401
HTTP_FORBIDDEN: Final[int] = 403
HTTP_NOT_FOUND: Final[int] = 404
HTTP_INTERNAL_SERVER_ERROR: Final[int] = 500

# Database Collections (actually used in the codebase)
COLLECTION_USER_SETTINGS: Final[str] = "user_settings"
COLLECTION_AUDIT_LOGS: Final[str] = "audit_logs"
COLLECTION_SYNC_STATUS: Final[str] = "sync_status"

# JWT Constants (used in auth.py)
JWT_ALGORITHM: Final[str] = "HS256"
JWT_EXPIRY_HOURS: Final[int] = 24

# Sync Constants (used in sync.py and base.py)
DEFAULT_SYNC_INTERVAL_MINUTES: Final[int] = 15

# Canvas Constants (used in canvas.py and canvas services)
CANVAS_API_VERSION: Final[str] = "v1"
CANVAS_DEFAULT_PAGE_SIZE: Final[int] = 100
CANVAS_MAX_PAGE_SIZE: Final[int] = 1000

# Notion Constants (used in notion.py and notion services)
NOTION_API_VERSION: Final[str] = "2022-06-28"
NOTION_DEFAULT_PAGE_SIZE: Final[int] = 100
NOTION_MAX_PAGE_SIZE: Final[int] = 100

# File Paths (used in config and firebase.py)
FIREBASE_KEYS_DIR: Final[str] = "./firebase-keys"
SERVICE_ACCOUNT_FILE: Final[str] = "service-account.json"
LOG_DIR: Final[str] = "./logs"

# Environment Names (used in config.py)
ENV_DEVELOPMENT: Final[str] = "dev"
ENV_PRODUCTION: Final[str] = "prod"
ENV_TESTING: Final[str] = "test"

# Logging (used in logging.py)
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_LOG_ROTATION: Final[str] = "10 MB"
DEFAULT_LOG_RETENTION: Final[str] = "30 days"

# Error Messages (used throughout the application)
ERROR_FIREBASE_NOT_AVAILABLE: Final[str] = "Firebase not available. Please configure Firebase credentials."
ERROR_INVALID_TOKEN: Final[str] = "Invalid or expired token"
ERROR_UNAUTHORIZED: Final[str] = "Unauthorized access"
ERROR_NOT_FOUND: Final[str] = "Resource not found"
ERROR_VALIDATION_FAILED: Final[str] = "Validation failed"
ERROR_EXTERNAL_SERVICE: Final[str] = "External service error"

# Success Messages (used in API responses)
SUCCESS_OPERATION: Final[str] = "Operation completed successfully"
SUCCESS_SYNC: Final[str] = "Synchronization completed successfully"
SUCCESS_AUTH: Final[str] = "Authentication successful"

# Audit Actions (used in firebase.py and logging service)
AUDIT_ACTION_LOGIN: Final[str] = "login"
AUDIT_ACTION_LOGOUT: Final[str] = "logout"
AUDIT_ACTION_SYNC: Final[str] = "sync"
AUDIT_ACTION_UPDATE: Final[str] = "update"
AUDIT_ACTION_DELETE: Final[str] = "delete"


class SyncStatus(str, Enum):
    """Synchronization status enumeration - used in sync.py and base.py."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
