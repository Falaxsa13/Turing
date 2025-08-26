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

    Args:
        date_string: ISO format date string

    Returns:
        Formatted date string or empty string if parsing fails
    """
    if not date_string:
        return ""

    try:
        if "T" in date_string:
            date_obj = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        else:
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")

        return date_obj.strftime("%Y-%m-%d")

    except Exception as e:
        logger.warning(f"Could not format date '{date_string}': {e}")
        return ""
