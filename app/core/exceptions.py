"""
Custom exceptions for the Turing Project application.
"""

from typing import Optional, Any, Dict


class TuringException(Exception):
    """Base exception for all Turing Project errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(TuringException):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        details = {"field": field, "value": value} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationError(TuringException):
    """Raised when authentication fails."""

    def __init__(self, message: str, user_id: Optional[str] = None):
        details = {"user_id": user_id} if user_id else {}
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(TuringException):
    """Raised when authorization fails."""

    def __init__(self, message: str, user_id: Optional[str] = None, resource: Optional[str] = None):
        details = {"user_id": user_id, "resource": resource}
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class DatabaseError(TuringException):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: Optional[str] = None, collection: Optional[str] = None):
        details = {"operation": operation, "collection": collection}
        super().__init__(message, "DATABASE_ERROR", details)


class ExternalServiceError(TuringException):
    """Raised when external service calls fail."""

    def __init__(self, message: str, service: str, status_code: Optional[int] = None):
        details = {"service": service, "status_code": status_code}
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class ConfigurationError(TuringException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, "CONFIGURATION_ERROR", details)
