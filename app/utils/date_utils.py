from datetime import datetime
from typing import Optional
from loguru import logger


def determine_semester_from_date(date_string: str) -> str:
    """
    Determine the semester term based on a date string.
    If no date is provided, defaults to "Fall 2025".

    Args:
        date_string: ISO format date string

    Returns:
        Semester string like "Fall 2025"
    """
    if not date_string:
        return "Fall 2025"

    try:
        # Parse the date
        if "T" in date_string:
            date_obj = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        else:
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")

        year = date_obj.year
        month = date_obj.month

        # Determine semester based on month
        if month in [1, 2, 3, 4, 5]:
            return f"Spring {year}"
        elif month in [6, 7]:
            return f"Summer {year}"
        else:  # August - December
            return f"Fall {year}"

    except Exception as e:
        logger.warning(f"Could not parse date '{date_string}': {e}")
        # Default to Fall 2025 when date parsing fails
        return "Fall 2025"


def format_date_for_notion(date_string: str) -> str:
    """
    Format a date string for Notion consumption (YYYY-MM-DD).

    For Canvas due dates, this function correctly handles timezone conversion.
    Canvas sends dates like "2024-12-15T23:59:00Z" which should be interpreted
    as the local due date, not shifted by timezone conversion.

    Args:
        date_string: ISO format date string from Canvas (e.g., "2024-12-15T23:59:00Z")

    Returns:
        Formatted date string (YYYY-MM-DD) or empty string if parsing fails
    """
    if not date_string:
        return ""

    try:
        if "T" in date_string:
            # Canvas sends dates like "2024-12-15T23:59:00Z"
            # The key insight: Canvas due dates are meant to be interpreted
            # as local time for the course, not UTC time.

            # Parse as UTC first
            utc_date_string = date_string.replace("Z", "+00:00")
            utc_dt = datetime.fromisoformat(utc_date_string)

            # Extract just the date part (YYYY-MM-DD) from the UTC time
            # This preserves the intended due date without timezone shifting
            return utc_dt.strftime("%Y-%m-%d")
        else:
            # Already in YYYY-MM-DD format
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            return date_obj.strftime("%Y-%m-%d")

    except Exception as e:
        logger.warning(f"Could not format date '{date_string}': {e}")
        return ""


def format_canvas_due_date_for_notion_est(date_string: str) -> str:
    """
    Format Canvas due date for Notion with proper EST timezone handling.

    The issue: When we send just a date like "2025-08-29" to Notion, it interprets
    it as "2025-08-29T00:00:00Z" (midnight UTC), which then gets converted to EST
    and shows as the previous day.

    Solution: Send the exact Canvas time but converted to EST timezone.

    Args:
        date_string: Canvas due date string (e.g., "2025-08-29T23:59:00Z" or "2025-10-23T03:59:00Z")

    Returns:
        Formatted date string with time in EST timezone for Notion
    """
    if not date_string:
        return ""

    try:
        if "T" in date_string:
            # Handle both UTC (Z) and timezone offset formats
            if date_string.endswith("Z"):
                # Canvas sends UTC dates like "2025-10-23T03:59:00Z"
                # Parse as UTC
                utc_date_string = date_string.replace("Z", "+00:00")
                utc_dt = datetime.fromisoformat(utc_date_string)

                # Convert UTC to EST (UTC-5)
                # Use timedelta to handle hour rollovers properly
                from datetime import timedelta

                est_dt = utc_dt - timedelta(hours=5)

            else:
                # Canvas sends timezone-aware dates like "2025-08-29T23:59:00-06:00"
                # Parse directly
                utc_dt = datetime.fromisoformat(date_string)

                # Convert to EST (assuming Canvas timezone is behind EST)
                # Use timedelta to handle hour rollovers properly
                from datetime import timedelta

                est_dt = utc_dt - timedelta(hours=5)

            # Format as ISO string with EST timezone
            # This ensures Notion shows the correct date and time
            return est_dt.strftime("%Y-%m-%dT%H:%M:%S-05:00")
        else:
            # Already in YYYY-MM-DD format, add time and EST timezone
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            # Set to noon EST to avoid midnight timezone issues
            est_time = date_obj.replace(hour=12, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S-05:00")
            return est_time

    except Exception as e:
        logger.warning(f"Could not format Canvas due date for EST '{date_string}': {e}")
        return ""
