"""
Canvas LMS API client for making authenticated requests.

This module provides a clean interface for interacting with the Canvas API,
with proper error handling, type safety, and request management.
"""

import httpx
from typing import List, Dict, Optional, Any, Union
from loguru import logger

# API Constants
DEFAULT_TIMEOUT = 30.0
DEFAULT_PER_PAGE = 100
MAX_SECTION_ENROLLMENTS = 50
API_VERSION = "v1"

# Common API includes
COURSE_INCLUDES = ["term", "course_image", "teachers", "total_students"]
COURSE_DETAIL_INCLUDES = ["term", "course_image", "teachers", "sections", "storage_quota_used"]
ASSIGNMENT_INCLUDES = ["submission", "assignment_group", "score_statistics"]
SECTION_INCLUDES = ["students", "teachers"]
ENROLLMENT_INCLUDES = ["user"]

# Enrollment states
ENROLLMENT_STATES = ["active", "invited_or_pending", "completed"]


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class CanvasAPIClient:
    """
    Canvas LMS API client for making authenticated requests.

    This client provides methods for interacting with Canvas courses, assignments,
    sections, and enrollments with proper error handling and type safety.
    """

    def __init__(self, base_url: str, access_token: str):
        """
        Initialize the Canvas API client.

        Args:
            base_url: Canvas instance base URL (e.g., "https://gatech.instructure.com")
            access_token: Canvas Personal Access Token

        Raises:
            ValueError: If base_url or access_token is empty
        """
        if not base_url or not access_token:
            raise ValueError("Both base_url and access_token are required")

        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.api_base = f"{self.base_url}/api/{API_VERSION}"

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """
        Make an authenticated request to the Canvas API.

        Args:
            endpoint: API endpoint (without /api/v1 prefix)
            params: Query parameters

        Returns:
            JSON response data or None if request fails

        Raises:
            CanvasAPIError: If the API request fails with specific error information
        """
        url = f"{self.api_base}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(url, headers=headers, params=params or {})
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            error_msg = f"Canvas API HTTP error {e.response.status_code} for endpoint '{endpoint}'"
            logger.error(f"{error_msg}: {e.response.text}")
            raise CanvasAPIError(error_msg, e.response.status_code, e.response.text)
        except httpx.TimeoutException:
            error_msg = f"Canvas API timeout for endpoint '{endpoint}'"
            logger.error(error_msg)
            raise CanvasAPIError(error_msg)
        except Exception as e:
            error_msg = f"Canvas API request failed for endpoint '{endpoint}': {e}"
            logger.error(error_msg)
            raise CanvasAPIError(error_msg)

    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current authenticated user.

        Returns:
            User information dictionary or None if request fails
        """
        try:
            result = await self._make_request("users/self")
            return result if isinstance(result, dict) else None
        except CanvasAPIError:
            logger.warning("Failed to get user info, returning None")
            return None

    async def get_enrolled_courses(self, enrollment_state: str = "active") -> List[Dict[str, Any]]:
        """
        Get courses the user is enrolled in.

        Args:
            enrollment_state: "active", "invited_or_pending", or "completed"

        Returns:
            List of course dictionaries

        Raises:
            ValueError: If enrollment_state is not valid
        """
        if enrollment_state not in ENROLLMENT_STATES:
            raise ValueError(f"enrollment_state must be one of {ENROLLMENT_STATES}")

        params = {
            "enrollment_state": enrollment_state,
            "include": COURSE_INCLUDES,
            "per_page": DEFAULT_PER_PAGE,
        }

        try:
            result = await self._make_request("courses", params)
            return result if isinstance(result, list) else []
        except CanvasAPIError:
            logger.warning(f"Failed to get enrolled courses for state '{enrollment_state}', returning empty list")
            return []

    async def get_course_assignments(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get assignments for a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of assignment dictionaries
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        params = {"include": ASSIGNMENT_INCLUDES, "per_page": DEFAULT_PER_PAGE}

        try:
            result = await self._make_request(f"courses/{course_id}/assignments", params)
            return result if isinstance(result, list) else []
        except CanvasAPIError:
            logger.warning(f"Failed to get assignments for course {course_id}, returning empty list")
            return []

    async def get_course_details(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific course.

        Args:
            course_id: Canvas course ID

        Returns:
            Course details dictionary or None if request fails
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        params = {"include": COURSE_DETAIL_INCLUDES}

        try:
            result = await self._make_request(f"courses/{course_id}", params)
            return result if isinstance(result, dict) else None
        except CanvasAPIError:
            logger.warning(f"Failed to get course details for {course_id}, returning None")
            return None

    async def get_course_sections(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get all sections for a course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of section dictionaries
        """
        if not course_id:
            raise ValueError("course_id cannot be empty")

        params = {"include": SECTION_INCLUDES, "per_page": DEFAULT_PER_PAGE}

        try:
            result = await self._make_request(f"courses/{course_id}/sections", params)
            return result if isinstance(result, list) else []
        except CanvasAPIError:
            logger.warning(f"Failed to get sections for course {course_id}, returning empty list")
            return []

    async def get_section_enrollments(
        self, section_id: str, enrollment_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get enrollments for a specific section.

        Args:
            section_id: The section ID
            enrollment_types: List of enrollment types to filter (e.g., ["TeacherEnrollment"])

        Returns:
            List of enrollment dictionaries
        """
        if not section_id:
            raise ValueError("section_id cannot be empty")

        params: Dict[str, Any] = {"state[]": "active", "include[]": "user", "per_page": MAX_SECTION_ENROLLMENTS}

        # Add enrollment type filters if provided
        if enrollment_types:
            for enrollment_type in enrollment_types:
                params["type[]"] = enrollment_type

        try:
            result = await self._make_request(f"sections/{section_id}/enrollments", params)
            return result if isinstance(result, list) else []
        except CanvasAPIError:
            logger.warning(f"Failed to get enrollments for section {section_id}, returning empty list")
            return []
