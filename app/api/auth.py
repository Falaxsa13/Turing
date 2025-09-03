from fastapi import APIRouter, HTTPException, Depends, status
from app.auth import authenticate_user_with_firebase, get_current_user
from app.core.dependencies import get_firebase_services, FirebaseServices
from app.core.exceptions import AuthenticationError, ExternalServiceError
from app.schemas.auth import (
    FirebaseConfigResponse,
    FirebaseKeys,
    FirebaseLoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
)
from app.models.user import AuthenticatedUser, UserProfile, UserPreferences, UserSettings
from datetime import datetime, timezone
from app.core.config import settings
from loguru import logger

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=LoginResponse)
async def login_with_firebase(
    request: FirebaseLoginRequest, firebase_services: FirebaseServices = Depends(get_firebase_services)
):
    """
    Authenticate user with Firebase ID token (Google OAuth).

    This endpoint receives a Firebase ID token from the frontend (after Google OAuth),
    verifies it, and returns a JWT token for subsequent API calls.
    """
    try:
        # Authenticate with Firebase
        auth = await authenticate_user_with_firebase(request.id_token, firebase_services)

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
    firebase_services: FirebaseServices = Depends(get_firebase_services),
):
    """
    Log a logout action (tokens are stateless; frontend should delete it).
    """
    try:
        # Log logout action
        await firebase_services.add_audit_log(
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
    current_user: AuthenticatedUser = Depends(get_current_user),
    firebase_services: FirebaseServices = Depends(get_firebase_services),
):
    """Get current authenticated user information."""

    try:
        user_email = current_user.user_email

        # Get user settings and preferences
        user_settings: UserSettings = await firebase_services.get_user_settings(user_email)

        user_preferences: UserPreferences = await firebase_services.get_user_preferences(user_email)

        def _has(cfg: UserSettings | None, *keys: str) -> bool:
            return bool(cfg and all(getattr(cfg, k) for k in keys))

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user information")


@router.get("/firebase-config", response_model=FirebaseConfigResponse)
async def get_firebase_config():
    """
    Public Firebase configuration for frontend auth.
    """
    return FirebaseConfigResponse(
        firebase=FirebaseKeys(
            apiKey=settings.firebase.api_key,
            authDomain=settings.firebase.auth_domain,
            projectId=settings.firebase.project_id,
            storageBucket=settings.firebase.storage_bucket,
            messagingSenderId=settings.firebase.messaging_sender_id,
            appId=settings.firebase.app_id,
            measurementId=settings.firebase.measurement_id,
        )
    )
