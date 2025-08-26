"""
Canvas API Helper for fetching course data and integrating with Notion.
"""

import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from loguru import logger
import asyncio


class CanvasAPIClient:
    """Canvas API client for fetching course and assignment data"""

    def __init__(self, base_url: str, access_token: str):
        """
        Initialize Canvas API client

        Args:
            base_url: Canvas instance URL (e.g., "https://your-school.instructure.com")
            access_token: Canvas Personal Access Token
        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make an authenticated request to Canvas API"""
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, params=params or {})
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Canvas API HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Canvas API request failed: {e}")
            return None

    async def get_current_user(self) -> Optional[Dict]:
        """Get current user information"""
        return await self._make_request("users/self")

    async def get_enrolled_courses(self, enrollment_state: str = "active") -> List[Dict]:
        """
        Get courses the user is enrolled in

        Args:
            enrollment_state: "active", "invited_or_pending", "completed"
        """
        params = {
            "enrollment_state": enrollment_state,
            "include": ["term", "course_image", "teachers", "total_students"],
            "per_page": 100,
        }

        result = await self._make_request("courses", params)
        return result if isinstance(result, list) else []

    async def get_course_assignments(self, course_id: str) -> List[Dict]:
        """Get assignments for a specific course"""
        params = {"include": ["submission", "assignment_group", "score_statistics"], "per_page": 100}

        result = await self._make_request(f"courses/{course_id}/assignments", params)
        return result if isinstance(result, list) else []

    async def get_course_details(self, course_id: str) -> Optional[Dict]:
        """Get detailed information about a specific course"""
        params = {"include": ["term", "course_image", "teachers", "sections", "storage_quota_used"]}

        return await self._make_request(f"courses/{course_id}", params)

    def determine_semester_from_date(self, start_date: str) -> str:
        """
        Determine semester from course start date

        Args:
            start_date: ISO format date string

        Returns:
            Semester string like "Fall 2025"
        """
        try:
            if not start_date:
                return "Fall 2025"  # Default fallback

            date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            year = date_obj.year
            month = date_obj.month

            # Determine semester based on start month
            if month >= 8:  # August onwards = Fall
                return f"Fall {year}"
            elif month >= 5:  # May-July = Summer
                return f"Summer {year}"
            else:  # January-April = Spring
                return f"Spring {year}"

        except Exception as e:
            logger.warning(f"Failed to parse date {start_date}: {e}")
            return "Fall 2025"  # Default fallback

    def map_canvas_course_to_notion(self, canvas_course: Dict) -> Dict[str, Any]:
        """
        Map Canvas course data to Notion course format

        Args:
            canvas_course: Raw Canvas course data

        Returns:
            Dictionary formatted for Notion course creation
        """
        # Extract course name from Canvas
        full_course_name = canvas_course.get("name", "Untitled Course")

        # Parse course title and course code from Canvas course name
        # Canvas typically formats as: "Course Title - COURSE-CODE"
        # e.g., "Computer Networking I - CS-3251-A"
        if " - " in full_course_name:
            # Split on " - " to separate title from course code
            parts = full_course_name.split(" - ", 1)  # Split only on first occurrence
            course_title = parts[0].strip()  # "Computer Networking I"
            course_code = parts[1].strip()  # "CS-3251-A"
        else:
            # If no " - " separator, use full name as title and check for course_code field
            course_title = full_course_name
            course_code = canvas_course.get("course_code", "")

        # Fallback: if still no course code, try to extract from Canvas course_code field
        if not course_code:
            course_code = canvas_course.get("course_code", "")

        # Extract instructor name
        professor = ""
        teachers = canvas_course.get("teachers", [])
        if teachers:
            professor = teachers[0].get("display_name", "")

        # Determine semester from start date
        start_date = canvas_course.get("start_at")
        term = self.determine_semester_from_date(start_date or "")

        # Format start date for Notion
        formatted_date = ""
        if start_date:
            try:
                date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except:
                pass

        # Build Notion course data
        notion_course = {
            "title": course_title,  # Clean title: "Computer Networking I"
            "course_code": course_code,  # Course code: "CS-3251-A"
            "professor": professor,
            "term": term,
            "date": formatted_date,
            # Add Canvas-specific metadata for reference
            "canvas_course_id": str(canvas_course.get("id", "")),
            "canvas_url": canvas_course.get("html_url", ""),
            "canvas_full_name": full_course_name,  # Keep original for reference
        }

        # Clean up empty fields
        return {k: v for k, v in notion_course.items() if v}


class CanvasNotionSyncer:
    """Synchronize Canvas courses with Notion databases"""

    def __init__(self, canvas_client: CanvasAPIClient, notion_manager):
        self.canvas = canvas_client
        self.notion = notion_manager

    async def sync_current_semester_courses(self) -> Dict[str, Any]:
        """
        Fetch enrolled courses from Canvas and create them in Notion

        Returns:
            Summary of sync operation
        """
        try:
            # Get enrolled courses from Canvas
            logger.info("Fetching enrolled courses from Canvas...")
            canvas_courses = await self.canvas.get_enrolled_courses()

            if not canvas_courses:
                return {
                    "success": False,
                    "message": "No enrolled courses found in Canvas",
                    "courses_found": 0,
                    "courses_created": 0,
                }

            # Filter for current semester courses (you can adjust this logic)
            current_year = datetime.now().year
            current_semester_courses = []

            for course in canvas_courses:
                start_date = course.get("start_at")
                if start_date:
                    try:
                        date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                        # Include courses that started this year or recently
                        if date_obj.year >= current_year - 1:
                            current_semester_courses.append(course)
                    except:
                        # Include courses without valid dates as they might be current
                        current_semester_courses.append(course)
                else:
                    # Include courses without start dates as they might be current
                    current_semester_courses.append(course)

            logger.info(f"Found {len(current_semester_courses)} current semester courses")

            # Create courses in Notion
            created_courses = []
            failed_courses = []

            for canvas_course in current_semester_courses:
                try:
                    # Map Canvas course to Notion format
                    notion_course_data = self.canvas.map_canvas_course_to_notion(canvas_course)

                    # Create in Notion
                    course_id = await self.notion.add_course_entry(notion_course_data)

                    if course_id:
                        created_courses.append(
                            {
                                "notion_id": course_id,
                                "canvas_id": canvas_course.get("id"),
                                "name": notion_course_data.get("title", canvas_course.get("name")),  # Use parsed title
                                "course_code": notion_course_data.get("course_code", ""),
                                "term": notion_course_data.get("term", ""),
                            }
                        )
                        logger.info(
                            f"Created course: {notion_course_data.get('title', canvas_course.get('name'))} -> {course_id}"
                        )
                    else:
                        failed_courses.append(
                            {
                                "canvas_id": canvas_course.get("id"),
                                "name": notion_course_data.get("title", canvas_course.get("name")),  # Use parsed title
                                "error": "Failed to create in Notion",
                            }
                        )

                except Exception as e:
                    # Map Canvas course to get parsed title for error reporting
                    notion_course_data = self.canvas.map_canvas_course_to_notion(canvas_course)
                    parsed_title = notion_course_data.get("title", canvas_course.get("name"))

                    logger.error(f"Failed to create course {parsed_title}: {e}")
                    failed_courses.append({"canvas_id": canvas_course.get("id"), "name": parsed_title, "error": str(e)})

            return {
                "success": True,
                "message": f"Successfully synced {len(created_courses)}/{len(current_semester_courses)} courses",
                "courses_found": len(current_semester_courses),
                "courses_created": len(created_courses),
                "courses_failed": len(failed_courses),
                "created_courses": created_courses,
                "failed_courses": failed_courses,
                "note": "Check your Notion Courses database for the new entries!",
            }

        except Exception as e:
            logger.error(f"Failed to sync courses: {e}")
            return {"success": False, "message": f"Sync failed: {str(e)}", "error": str(e)}


# Utility functions
async def test_canvas_connection(base_url: str, access_token: str) -> Dict[str, Any]:
    """Test Canvas API connection"""
    client = CanvasAPIClient(base_url, access_token)

    try:
        user = await client.get_current_user()
        if user:
            return {
                "success": True,
                "message": "Canvas connection successful",
                "user": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "email": user.get("primary_email"),
                    "avatar_url": user.get("avatar_url"),
                },
            }
        else:
            return {"success": False, "message": "Failed to connect to Canvas - check your credentials"}

    except Exception as e:
        return {"success": False, "message": f"Canvas connection failed: {str(e)}", "error": str(e)}


async def sync_canvas_to_notion(
    canvas_base_url: str, canvas_token: str, notion_token: str, notion_parent_page_id: str
) -> Dict[str, Any]:
    """
    Main function to sync Canvas courses to Notion

    Args:
        canvas_base_url: Canvas instance URL
        canvas_token: Canvas Personal Access Token
        notion_token: Notion API token
        notion_parent_page_id: Notion parent page ID

    Returns:
        Sync operation summary
    """
    from app.utils.notion_helper import NotionWorkspaceManager

    try:
        # Initialize clients
        canvas_client = CanvasAPIClient(canvas_base_url, canvas_token)
        notion_manager = NotionWorkspaceManager(notion_token, notion_parent_page_id)

        # Create syncer
        syncer = CanvasNotionSyncer(canvas_client, notion_manager)

        # Perform sync
        result = await syncer.sync_current_semester_courses()

        return result

    except Exception as e:
        logger.error(f"Canvas to Notion sync failed: {e}")
        return {"success": False, "message": f"Sync operation failed: {str(e)}", "error": str(e)}
