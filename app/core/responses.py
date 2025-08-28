"""
Standardized response models for the Turing Project API.
"""

from typing import Any, Dict, List, Optional, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# Type variable for response data
T = TypeVar("T")


class BaseResponse(BaseModel):
    """Base response model for all API endpoints."""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable message about the operation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    request_id: Optional[str] = Field(default=None, description="Unique request identifier")


class SuccessResponse(BaseResponse, Generic[T]):
    """Standard success response model."""

    data: T = Field(description="Response data")

    def __init__(self, data: T, message: str = "Operation completed successfully", **kwargs):
        super().__init__(success=True, message=message, **kwargs)
        self.data = data


class ErrorResponse(BaseResponse):
    """Standard error response model."""

    error_code: str = Field(description="Machine-readable error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")

    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(success=False, message=message, **kwargs)
        self.error_code = error_code
        self.details = details


class PaginatedResponse(BaseResponse, Generic[T]):
    """Paginated response model for list endpoints."""

    data: List[T] = Field(description="List of items")
    pagination: Dict[str, Any] = Field(description="Pagination information")

    def __init__(
        self,
        data: List[T],
        page: int,
        page_size: int,
        total_count: int,
        message: str = "Data retrieved successfully",
        **kwargs
    ):
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": page * page_size < total_count,
            "has_previous": page > 1,
        }
        super().__init__(success=True, message=message, **kwargs)
        self.data = data
        self.pagination = pagination


class HealthCheckResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Service status")
    environment: str = Field(description="Current environment")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    services: Dict[str, str] = Field(description="Status of individual services")
    uptime: Optional[float] = Field(default=None, description="Service uptime in seconds")


class SyncStatusResponse(BaseModel):
    """Synchronization status response model."""

    status: str = Field(description="Current sync status")
    last_sync: Optional[datetime] = Field(default=None, description="Last synchronization time")
    next_sync: Optional[datetime] = Field(default=None, description="Next scheduled synchronization")
    progress: Optional[float] = Field(default=None, description="Sync progress (0-100)")
    message: Optional[str] = Field(default=None, description="Additional status information")
    errors: List[str] = Field(default_factory=list, description="List of sync errors")


# Convenience functions for creating responses
def success_response(data: Any, message: str = "Operation completed successfully") -> SuccessResponse:
    """Create a success response."""
    return SuccessResponse(data=data, message=message)


def error_response(message: str, error_code: str, details: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Create an error response."""
    return ErrorResponse(message=message, error_code=error_code, details=details)


def paginated_response(
    data: List[Any], page: int, page_size: int, total_count: int, message: str = "Data retrieved successfully"
) -> PaginatedResponse:
    """Create a paginated response."""
    return PaginatedResponse(data=data, page=page, page_size=page_size, total_count=total_count, message=message)
