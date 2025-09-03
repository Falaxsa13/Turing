"""
Enhanced Canvas API client for fetching comprehensive assignment details.

This client extends the basic Canvas client to fetch rich assignment information
including submission details, assignment groups, statistics, and rubrics for
beautiful Notion formatting.
"""

import httpx
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from loguru import logger

from app.schemas.canvas import (
    CanvasAssignmentDetails,
    CanvasAssignmentGroup,
    CanvasSubmissionInfo,
    AssignmentSubmissionType,
    AssignmentWorkflowState,
    AssignmentGradingType,
)
from .client import CanvasAPIClient, CanvasAPIError, ASSIGNMENT_INCLUDES


class EnhancedCanvasClient(CanvasAPIClient):
    """
    Enhanced Canvas API client for comprehensive assignment data.

    This client fetches rich assignment information including:
    - Full assignment details with all available fields
    - Assignment group information and weights
    - User submission details and scores
    - Score statistics and class analytics
    - Assignment rubrics and criteria
    - Assignment overrides and special cases
    """

    def __init__(self, base_url: str, access_token: str):
        """Initialize the enhanced Canvas client."""
        super().__init__(base_url, access_token)

    async def get_enhanced_assignment_details(
        self, course_id: str, assignment_id: str, include_submission: bool = True
    ) -> Optional[CanvasAssignmentDetails]:
        """
        Get comprehensive assignment details including all available information.

        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID
            include_submission: Whether to include user submission info

        Returns:
            Enhanced assignment details or None if failed
        """
        try:
            # logger.info(f"Fetching enhanced details for assignment {assignment_id} in course {course_id}")

            # Build includes based on user preferences
            includes = ASSIGNMENT_INCLUDES.copy()
            if not include_submission:
                includes.remove("submission")

            params = {"include[]": includes, "per_page": 1}

            # Fetch the specific assignment
            result = await self._make_request(f"courses/{course_id}/assignments/{assignment_id}", params)

            if not result or not isinstance(result, dict):
                logger.warning(f"No assignment data returned for {assignment_id}")
                return None

            # Transform raw data to enhanced schema
            enhanced_assignment = self._transform_assignment_data(result, course_id)

            # logger.info(f"Successfully fetched enhanced details for assignment '{enhanced_assignment.name}'")
            return enhanced_assignment

        except CanvasAPIError as e:
            logger.error(f"Canvas API error fetching assignment {assignment_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching assignment {assignment_id}: {e}")
            return None

    async def get_enhanced_course_assignments(
        self, course_id: str, include_submissions: bool = True, include_groups: bool = True
    ) -> List[CanvasAssignmentDetails]:
        """
        Get all assignments for a course with enhanced details (with proper pagination).

        Args:
            course_id: Canvas course ID
            include_submissions: Whether to include user submission info
            include_groups: Whether to include assignment group info

        Returns:
            List of enhanced assignment details
        """
        try:
            # logger.info(f"Fetching enhanced assignments for course {course_id}")

            # Fetch all assignments with pagination
            all_assignments = []
            page = 1
            per_page = 100

            while True:
                params = {
                    "include": ASSIGNMENT_INCLUDES,
                    "per_page": per_page,
                    "page": page,
                }

                result = await self._make_request(f"courses/{course_id}/assignments", params)

                if not result or not isinstance(result, list):
                    if page == 1:
                        logger.warning(f"No assignments returned for course {course_id}")
                        return []
                    break

                all_assignments.extend(result)
                logger.debug(f"Page {page}: {len(result)} assignments, total: {len(all_assignments)}")

                # Last page if we got fewer results than requested
                if len(result) < per_page:
                    break

                page += 1

            if not all_assignments:
                logger.warning(f"No assignments found for course {course_id}")
                return []

            logger.info(
                f"IMPORTANT IMPORTANT IMPORTANT Found {len(all_assignments)} assignments for course {course_id}"
            )

            # Transform each assignment
            enhanced_assignments = []
            for assignment_data in all_assignments:
                try:
                    enhanced_assignment = self._transform_assignment_data(assignment_data, course_id)
                    enhanced_assignments.append(enhanced_assignment)
                except Exception as e:
                    logger.warning(f"Failed to transform assignment {assignment_data.get('id')}: {e}")
                    continue

            logger.info(
                f"Successfully fetched {len(enhanced_assignments)} enhanced assignments for course {course_id} (from {len(all_assignments)} raw assignments)"
            )
            return enhanced_assignments

        except CanvasAPIError as e:
            logger.error(f"Canvas API error fetching assignments for course {course_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching assignments for course {course_id}: {e}")
            return []

    async def get_assignment_group_details(self, course_id: str, group_id: str) -> Optional[CanvasAssignmentGroup]:
        """
        Get detailed information about an assignment group.

        Args:
            course_id: Canvas course ID
            group_id: Assignment group ID

        Returns:
            Assignment group details or None if failed
        """
        try:
            logger.info(f"Fetching assignment group {group_id} details for course {course_id}")

            result = await self._make_request(f"courses/{course_id}/assignment_groups/{group_id}")

            if not result or not isinstance(result, dict):
                logger.warning(f"No assignment group data returned for {group_id}")
                return None

            # Transform to schema
            group_details = CanvasAssignmentGroup(
                id=result.get("id", 0),
                name=result.get("name", "Unknown Group"),
                group_weight=result.get("group_weight"),
                assignments_count=result.get("assignments_count"),
                assignment_visibility=result.get("assignment_visibility"),
            )

            # logger.info(f"Successfully fetched assignment group '{group_details.name}' details")
            return group_details

        except CanvasAPIError as e:
            logger.error(f"Canvas API error fetching assignment group {group_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching assignment group {group_id}: {e}")
            return None

    async def get_user_submission_for_assignment(
        self, course_id: str, assignment_id: str
    ) -> Optional[CanvasSubmissionInfo]:
        """
        Get the current user's submission for a specific assignment.

        Args:
            course_id: Canvas course ID
            assignment_id: Canvas assignment ID

        Returns:
            User submission info or None if no submission
        """
        try:
            # logger.info(f"Fetching user submission for assignment {assignment_id} in course {course_id}")

            # Get user's own submission
            result = await self._make_request(f"courses/{course_id}/assignments/{assignment_id}/submissions/self")

            if not result or not isinstance(result, dict):
                logger.info(f"No submission found for assignment {assignment_id}")
                return None

            # Transform to schema
            submission_info = CanvasSubmissionInfo(
                id=result.get("id", 0),
                user_id=result.get("user_id", 0),
                assignment_id=result.get("assignment_id", 0),
                score=result.get("score"),
                grade=result.get("grade"),
                submitted_at=self._parse_datetime(result.get("submitted_at")),
                workflow_state=result.get("workflow_state", "unsubmitted"),
                late=result.get("late", False),
                excused=result.get("excused", False),
                attempt=result.get("attempt"),
                body=result.get("body"),
                submission_type=result.get("submission_type"),
            )

            # logger.info(f"Successfully fetched submission info for assignment {assignment_id}")
            return submission_info

        except CanvasAPIError as e:
            logger.error(f"Canvas API error fetching submission for assignment {assignment_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching submission for assignment {assignment_id}: {e}")
            return None

    async def get_course_assignment_groups(self, course_id: str) -> List[CanvasAssignmentGroup]:
        """
        Get all assignment groups for a course.

        Args:
            course_id: Canvas course ID

        Returns:
            List of assignment group details
        """
        try:
            logger.info(f"Fetching assignment groups for course {course_id}")

            result = await self._make_request(f"courses/{course_id}/assignment_groups")

            if not result or not isinstance(result, list):
                logger.warning(f"No assignment groups returned for course {course_id}")
                return []

            # Transform each group
            assignment_groups = []
            for group_data in result:
                try:
                    group_details = CanvasAssignmentGroup(
                        id=group_data.get("id", 0),
                        name=group_data.get("name", "Unknown Group"),
                        group_weight=group_data.get("group_weight"),
                        assignments_count=group_data.get("assignments_count"),
                        assignment_visibility=group_data.get("assignment_visibility"),
                    )
                    assignment_groups.append(group_details)
                except Exception as e:
                    logger.warning(f"Failed to transform assignment group {group_data.get('id')}: {e}")
                    continue

            # logger.info(f"Successfully fetched {len(assignment_groups)} assignment groups for course {course_id}")
            return assignment_groups

        except CanvasAPIError as e:
            logger.error(f"Canvas API error fetching assignment groups for course {course_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching assignment groups for course {course_id}: {e}")
            return []

    def _transform_assignment_data(self, raw_data: Dict[str, Any], course_id: str) -> CanvasAssignmentDetails:
        """Transform raw Canvas assignment data to enhanced schema."""

        # Parse submission types
        submission_types = []
        raw_submission_types = raw_data.get("submission_types", [])
        for sub_type in raw_submission_types:
            try:
                submission_types.append(AssignmentSubmissionType(sub_type))
            except ValueError:
                logger.warning(f"Unknown submission type: {sub_type}")
                submission_types.append(AssignmentSubmissionType.NONE)

        # Parse workflow state
        try:
            workflow_state = AssignmentWorkflowState(raw_data.get("workflow_state", "unpublished"))
        except ValueError:
            workflow_state = AssignmentWorkflowState.UNPUBLISHED

        # Parse grading type
        grading_type = None
        raw_grading_type = raw_data.get("grading_type")
        if raw_grading_type:
            try:
                grading_type = AssignmentGradingType(raw_grading_type)
            except ValueError:
                logger.warning(f"Unknown grading type: {raw_grading_type}")

        # Create enhanced assignment object
        enhanced_assignment = CanvasAssignmentDetails(
            id=raw_data.get("id", 0),
            name=raw_data.get("name", "Untitled Assignment"),
            description=raw_data.get("description"),
            description_plain=raw_data.get("description_plain"),
            due_at=self._parse_datetime(raw_data.get("due_at")),
            lock_at=self._parse_datetime(raw_data.get("lock_at")),
            unlock_at=self._parse_datetime(raw_data.get("unlock_at")),
            created_at=self._parse_datetime(raw_data.get("created_at")),
            updated_at=self._parse_datetime(raw_data.get("updated_at")),
            points_possible=raw_data.get("points_possible"),
            grading_type=grading_type,
            grading_standard_id=raw_data.get("grading_standard_id"),
            submission_types=submission_types,
            allowed_attempts=raw_data.get("allowed_attempts"),
            submission_downloads=raw_data.get("submission_downloads"),
            workflow_state=workflow_state,
            published=raw_data.get("published", False),
            muted=raw_data.get("muted"),
            anonymous_grading=raw_data.get("anonymous_grading"),
            moderated_grading=raw_data.get("moderated_grading"),
            group_category_id=raw_data.get("group_category_id"),
            peer_reviews=raw_data.get("peer_reviews"),
            anonymous_peer_reviews=raw_data.get("anonymous_peer_reviews"),
            peer_review_count=raw_data.get("peer_review_count"),
            external_tool_tag_attributes=raw_data.get("external_tool_tag_attributes"),
            lti_resource_link_id=raw_data.get("lti_resource_link_id"),
            is_quiz_assignment=raw_data.get("is_quiz_assignment"),
            assignment_group_id=raw_data.get("assignment_group_id"),
            position=raw_data.get("position"),
            html_url=raw_data.get("html_url"),
            quiz_id=raw_data.get("quiz_id"),
            course_id=int(course_id),
            course_name=raw_data.get("course_name"),
            score_statistics=raw_data.get("score_statistics"),
            rubric=raw_data.get("rubric"),
            assignment_overrides=raw_data.get("overrides"),
            omit_from_final_grade=raw_data.get("omit_from_final_grade"),
            hide_in_gradebook=raw_data.get("hide_in_gradebook"),
            important_dates=raw_data.get("important_dates"),
            require_lockdown_browser=raw_data.get("require_lockdown_browser"),
            can_duplicate=raw_data.get("can_duplicate"),
        )

        return enhanced_assignment

    def _parse_datetime(self, datetime_string: Optional[str]) -> Optional[datetime]:
        """Parse Canvas datetime string to Python datetime object."""
        if not datetime_string:
            return None

        try:
            # Handle Canvas ISO format with timezone
            if datetime_string.endswith("Z"):
                datetime_string = datetime_string[:-1] + "+00:00"
            return datetime.fromisoformat(datetime_string)
        except ValueError:
            logger.warning(f"Failed to parse datetime: {datetime_string}")
            return None

    async def get_user_submissions_batch(
        self, course_id: str, assignment_ids: List[int]
    ) -> Dict[int, CanvasSubmissionInfo]:
        """
        Get user submissions for multiple assignments in batch (performance optimization).

        Args:
            course_id: Canvas course ID
            assignment_ids: List of assignment IDs to get submissions for

        Returns:
            Dictionary mapping assignment_id to submission info
        """
        try:
            submissions = {}

            # Canvas API doesn't support batch submission fetching, but we can optimize
            # by making concurrent requests with a semaphore to limit concurrency
            import asyncio

            semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

            async def get_single_submission(assignment_id: int):
                async with semaphore:
                    try:
                        submission = await self.get_user_submission_for_assignment(course_id, str(assignment_id))
                        return assignment_id, submission
                    except Exception as e:
                        logger.warning(f"Failed to get submission for assignment {assignment_id}: {e}")
                        return assignment_id, None

            # Process all submissions concurrently
            results = await asyncio.gather(
                *[get_single_submission(aid) for aid in assignment_ids], return_exceptions=True
            )

            # Process results
            for result in results:
                if isinstance(result, BaseException):
                    logger.warning(f"Exception in batch submission fetch: {result}")
                    continue

                assignment_id, submission = result
                if submission:
                    submissions[assignment_id] = submission

            logger.info(f"Retrieved {len(submissions)} submissions out of {len(assignment_ids)} assignments")
            return submissions

        except Exception as e:
            logger.error(f"Failed to get batch submissions for course {course_id}: {e}")
            return {}
