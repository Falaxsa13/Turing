import httpx
from typing import List, Dict, Optional
from loguru import logger


class CanvasAPIClient:
    """
    Canvas LMS API client for making authenticated requests.
    """

    def __init__(self, base_url: str, access_token: str):
        """
        Initialize the Canvas API client.

        Args:
            base_url: Canvas instance base URL (e.g., "https://gatech.instructure.com")
            access_token: Canvas Personal Access Token
        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.api_base = f"{self.base_url}/api/v1"

    async def _make_request(self, endpoint: str, params: Dict = {}) -> Optional[Dict | List]:
        """
        Make an authenticated request to the Canvas API.

        Args:
            endpoint: API endpoint (without /api/v1 prefix)
            params: Query parameters

        Returns:
            JSON response data or None if request fails
        """
        url = f"{self.api_base}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params or {})
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Canvas API HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Canvas API request failed: {e}")
            return None

    async def get_user_info(self) -> Optional[Dict]:
        """Get information about the current user."""
        result = await self._make_request("users/self")
        return result if isinstance(result, dict) else None

    async def get_enrolled_courses(self, enrollment_state: str = "active") -> List[Dict]:
        """
        Get courses the user is enrolled in.

        Args:
            enrollment_state: "active", "invited_or_pending", "completed"

        Returns:
            List of course dictionaries
        """
        params = {
            "enrollment_state": enrollment_state,
            "include": ["term", "course_image", "teachers", "total_students"],
            "per_page": 100,
        }

        result = await self._make_request("courses", params)
        return result if isinstance(result, list) else []

    async def get_course_assignments(self, course_id: str) -> List[Dict]:
        """Get assignments for a specific course."""
        params = {"include": ["submission", "assignment_group", "score_statistics"], "per_page": 100}

        result = await self._make_request(f"courses/{course_id}/assignments", params)
        return result if isinstance(result, list) else []

    async def get_course_details(self, course_id: str) -> Optional[Dict]:
        """Get detailed information about a specific course."""
        params = {"include": ["term", "course_image", "teachers", "sections", "storage_quota_used"]}
        result = await self._make_request(f"courses/{course_id}", params)
        return result if isinstance(result, dict) else None

    async def get_course_sections(self, course_id: str) -> List[Dict]:
        """Get all sections for a course."""
        params = {"include": ["students", "teachers"], "per_page": 100}
        result = await self._make_request(f"courses/{course_id}/sections", params)
        return result if isinstance(result, list) else []

    async def get_section_enrollments(self, section_id: str, enrollment_types: List[str] = []) -> List[Dict]:
        """
        Get enrollments for a specific section.

        Args:
            section_id: The section ID
            enrollment_types: List of enrollment types to filter (e.g., ["TeacherEnrollment"])

        Returns:
            List of enrollment dictionaries
        """
        params = {"state[]": "active", "include[]": "user", "per_page": 50}

        if enrollment_types:
            for enrollment_type in enrollment_types:
                params[f"type[]"] = enrollment_type

        result = await self._make_request(f"sections/{section_id}/enrollments", params)
        return result if isinstance(result, list) else []
