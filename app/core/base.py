"""
Base classes and abstractions for the Turing Project services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generic, TypeVar
import logging

# Type variable for service results
T = TypeVar("T")


class ServiceResult(Generic[T]):
    """Wrapper for service operation results."""

    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error


class BaseService(ABC):
    """Base class for all services."""

    def __init__(self):
        # Module-level logger (industry standard)
        self.logger = logging.getLogger(self.__class__.__name__)

    def log_info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(message, **kwargs)

    def log_warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(message, **kwargs)

    def log_error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(message, **kwargs)

    def log_debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(message, **kwargs)


class BaseAPIClient(BaseService):
    """Base class for external API clients."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = None

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the API client."""
        pass

    @abstractmethod
    async def close(self):
        """Close the API client and cleanup resources."""
        pass

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class BaseDataProcessor(BaseService, Generic[T]):
    """Base class for data processing services."""

    @abstractmethod
    async def process(self, data: Any) -> T:
        """Process input data and return processed result."""
        pass

    @abstractmethod
    async def validate(self, data: Any) -> bool:
        """Validate input data."""
        pass

    @abstractmethod
    async def transform(self, data: Any) -> T:
        """Transform input data to output format."""
        pass


class BaseSyncService(BaseService):
    """Base class for synchronization services."""

    def __init__(self, sync_interval_minutes: int = 15):
        super().__init__()
        self.sync_interval_minutes = sync_interval_minutes
        self.last_sync = None
        self.is_syncing = False

    @abstractmethod
    async def sync(self) -> bool:
        """Perform synchronization."""
        pass

    @abstractmethod
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        pass

    async def should_sync(self) -> bool:
        """Check if synchronization should be performed."""
        if self.is_syncing:
            return False

        # Add your sync logic here
        return True
