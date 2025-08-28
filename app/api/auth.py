from fastapi import APIRouter, HTTPException, Depends, status
from app.auth import authenticate_user_with_firebase, get_current_user
from app.firebase import get_firebase_db
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.schemas.auth import (
    FirebaseConfigResponse,
    FirebaseKeys,
    FirebaseLoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
)
from app.models.user import AuthenticatedUser, UserProfile
from datetime import datetime, timezone
from app.config import settings
import logging
import asyncio


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login_with_firebase(request: FirebaseLoginRequest, firebase_db=Depends(get_firebase_db)):
    """
    Authenticate user with Firebase ID token (Google OAuth).

    This endpoint receives a Firebase ID token from the frontend (after Google OAuth),
    verifies it, and returns a JWT token for subsequent API calls.
    """
    try:
        # Authenticate with Firebase
        auth = await authenticate_user_with_firebase(request.id_token, firebase_db)

        if not auth:
            raise AuthenticationError("Firebase authentication failed", user_id=None)

        logger.info("User logged in successfully", extra={"user_email": auth.get("user_email")})

        return LoginResponse(
            **auth,
            success=True,
            message="Authentication successful",
        )

    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise ExternalServiceError(
            message="Login failed due to server error", service="authentication", status_code=500
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: LogoutRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    firebase_db=Depends(get_firebase_db),
):
    """
    Log a logout action (tokens are stateless; frontend should delete it).
    """
    try:
        # Log logout action
        await firebase_db.add_audit_log(
            user_email=current_user.user_email,
            action="logout",
            target_id=current_user.user_id,
            metadata={"revoke_token": request.revoke_token},
        )

        logger.info("User logged out", extra={"user_email": current_user.user_email})

        return LogoutResponse(
            success=True,
            message="Logout successful",
            user_email=current_user.user_email,
            logout_timestamp=datetime.now(timezone.utc).isoformat(),
            note="Frontend should delete the access token to complete logout",
        )

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed due to server error"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_info(
    current_user: AuthenticatedUser = Depends(get_current_user), firebase_db=Depends(get_firebase_db)
):
    """
    Get current authenticated user information.
    """

    try:
        user_email = current_user.user_email

        user_settings, user_preferences = await asyncio.gather(
            firebase_db.get_user_settings(user_email),
            firebase_db.get_user_preferences(user_email),
        )

        def _has(cfg: dict | None, *keys: str) -> bool:
            return bool(cfg and all(cfg.get(k) for k in keys))

        setup_status = {
            "has_canvas": _has(user_settings, "canvas_base_url", "canvas_pat"),
            "has_notion": _has(user_settings, "notion_token", "notion_parent_page_id"),
            "has_google": _has(user_settings, "google_credentials"),
        }

        return UserProfile(
            user_email=user_email,
            user_id=current_user.user_id,
            display_name=current_user.display_name,
            photo_url=current_user.photo_url,
            settings=user_settings,
            preferences=user_preferences,
            setup_status=setup_status,
        )

    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user information")


@router.get("/firebase-config", response_model=FirebaseConfigResponse)
async def get_firebase_config():
    """
    Public Firebase configuration for frontend auth.
    """
    return FirebaseConfigResponse(
        firebase=FirebaseKeys(
            apiKey=settings.firebase_api_key,
            authDomain=settings.firebase_auth_domain,
            projectId=settings.firebase_project_id,
            storageBucket=settings.firebase_storage_bucket,
            messagingSenderId=settings.firebase_messaging_sender_id,
            appId=settings.firebase_app_id,
            measurementId=settings.firebase_measurement_id,
        )
    )
