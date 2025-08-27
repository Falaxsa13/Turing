"""
Authentication API endpoints for Firebase authentication with Google login.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from app.auth import authenticate_user_with_firebase, get_current_user, get_current_user_email
from app.firebase import get_firebase_db
from loguru import logger
from typing import Optional


router = APIRouter(prefix="/auth", tags=["authentication"])


class FirebaseLoginRequest(BaseModel):
    """Request model for Firebase authentication"""

    id_token: str  # Firebase ID token from client


class LoginResponse(BaseModel):
    """Response model for successful authentication"""

    success: bool
    message: str
    user_email: str
    user_id: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    access_token: str
    token_type: str
    expires_in: int


class LogoutRequest(BaseModel):
    """Request model for logout"""

    revoke_token: bool = False


@router.post("/login", response_model=LoginResponse)
async def login_with_firebase(request: FirebaseLoginRequest, firebase_db=Depends(get_firebase_db)):
    """
    🔑 Authenticate user with Firebase ID token (Google OAuth).

    This endpoint receives a Firebase ID token from the frontend (after Google OAuth),
    verifies it, and returns a JWT token for subsequent API calls.
    """
    try:
        # Authenticate with Firebase
        auth_result = await authenticate_user_with_firebase(request.id_token, firebase_db)

        if not auth_result:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase authentication failed")

        logger.info(f"User logged in successfully: {auth_result['user_email']}")

        return LoginResponse(
            success=True,
            message="Authentication successful",
            user_email=auth_result["user_email"],
            user_id=auth_result["user_id"],
            display_name=auth_result.get("display_name"),
            photo_url=auth_result.get("photo_url"),
            access_token=auth_result["access_token"],
            token_type=auth_result["token_type"],
            expires_in=auth_result["expires_in"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed due to server error"
        )


@router.post("/logout")
async def logout(
    request: LogoutRequest, current_user: dict = Depends(get_current_user), firebase_db=Depends(get_firebase_db)
):
    """
    🚪 Logout current user.

    Logs the logout action for audit purposes.
    Note: JWT tokens are stateless, so logout is mainly for logging purposes.
    Frontend should delete the token to effectively log out.
    """
    try:
        user_email = current_user["user_email"]
        user_id = current_user["user_id"]

        # Log logout action
        await firebase_db.add_audit_log(
            user_email=user_email, action="logout", target_id=user_id, metadata={"revoke_token": request.revoke_token}
        )

        logger.info(f"User logged out: {user_email}")

        return {"success": True, "message": "Logout successful", "note": "Frontend should delete the access token"}

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed due to server error"
        )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user), firebase_db=Depends(get_firebase_db)):
    """
    👤 Get current authenticated user information.

    Returns user profile and preferences.
    """
    try:
        user_email = current_user["user_email"]

        # Get user settings
        user_settings = await firebase_db.get_user_settings(user_email)

        # Get user preferences
        user_preferences = await firebase_db.get_user_preferences(user_email)

        return {
            "success": True,
            "user_email": user_email,
            "user_id": current_user.get("user_id"),
            "display_name": current_user.get("display_name"),
            "photo_url": current_user.get("photo_url"),
            "settings": user_settings,
            "preferences": user_preferences,
            "setup_status": {
                "has_canvas": bool(
                    user_settings and user_settings.get("canvas_base_url") and user_settings.get("canvas_pat")
                ),
                "has_notion": bool(
                    user_settings and user_settings.get("notion_token") and user_settings.get("notion_parent_page_id")
                ),
                "has_google": bool(user_settings and user_settings.get("google_credentials")),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user information")


@router.get("/firebase-config")
async def get_firebase_config():
    """
    🔧 Get Firebase configuration for frontend.

    Returns public Firebase configuration needed for frontend authentication.
    """
    from app.config import settings

    return {
        "firebase": {
            "apiKey": settings.firebase_api_key,
            "authDomain": settings.firebase_auth_domain,
            "projectId": settings.firebase_project_id,
            "storageBucket": settings.firebase_storage_bucket,
            "messagingSenderId": settings.firebase_messaging_sender_id,
            "appId": settings.firebase_app_id,
            "measurementId": settings.firebase_measurement_id,
        }
    }
