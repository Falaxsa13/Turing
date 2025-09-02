"""
Authentication utilities for Firebase and JWT token handling.
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
from app.firebase import firebase_manager, get_firebase_db
from app.models.user import User, AuthenticatedUser
from loguru import logger
from typing import Optional, Dict, Any
import asyncio


security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt.expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        return None


async def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """Verify Firebase ID token and return user info"""
    try:
        # Run Firebase token verification in a thread since it's synchronous
        loop = asyncio.get_event_loop()
        decoded_token = await loop.run_in_executor(None, firebase_manager.verify_firebase_token, id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Firebase token verification failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), firebase_db=Depends(get_firebase_db)
) -> AuthenticatedUser:
    """Get current authenticated user from JWT token"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # First try to verify as JWT token
        payload = verify_token(credentials.credentials)
        if payload:
            user_email: Optional[str] = payload.get("sub")
            if user_email is None:
                raise credentials_exception

            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

            return AuthenticatedUser(
                user_email=user_email,
                user_id=payload.get("user_id", ""),
                token_expires_at=datetime.fromtimestamp(exp) if exp else None,
                auth_method="jwt",
            )

        # If JWT verification fails, try Firebase token
        firebase_user = await verify_firebase_token(credentials.credentials)
        if firebase_user:
            return AuthenticatedUser(
                user_email=firebase_user.get("email", ""),
                user_id=firebase_user.get("uid", ""),
                display_name=firebase_user.get("name"),
                photo_url=firebase_user.get("picture"),
                auth_method="firebase",
            )

        raise credentials_exception

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise credentials_exception


async def get_current_user_email(current_user: AuthenticatedUser = Depends(get_current_user)) -> str:
    """Get current user email from authenticated user"""
    return current_user.user_email


async def authenticate_user_with_firebase(
    id_token: str, firebase_db=Depends(get_firebase_db)
) -> Optional[Dict[str, Any]]:
    """Authenticate user with Firebase ID token and create/update user settings"""
    try:
        # Verify Firebase token
        firebase_user = await verify_firebase_token(id_token)
        if not firebase_user:
            return None

        user_email = firebase_user.get("email")
        user_id = firebase_user.get("uid")
        display_name = firebase_user.get("name")
        photo_url = firebase_user.get("picture")

        if not user_email or not user_id:
            logger.error("Firebase token missing required fields")
            return None

        # Check if user settings exist, create if not
        user_settings = await firebase_db.get_user_settings(user_email)
        if not user_settings:
            # Create new user settings
            now = datetime.utcnow()
            user_data = {
                "created_at": now,
                "updated_at": now,
            }
            await firebase_db.create_or_update_user_settings(user_email, user_data)
            logger.info(f"Created new user settings for {user_email}")

        # Create JWT token for the user
        access_token_expires = timedelta(minutes=settings.jwt.expire_minutes)
        access_token = create_access_token(
            data={"sub": user_email, "user_id": user_id}, expires_delta=access_token_expires
        )

        # Log authentication
        await firebase_db.add_audit_log(
            user_email=user_email,
            action="login",
            target_id=user_id,
            metadata={"display_name": display_name, "auth_method": "firebase_google"},
        )

        return {
            "user_email": user_email,
            "user_id": user_id,
            "display_name": display_name,
            "photo_url": photo_url,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt.expire_minutes * 60,
        }

    except Exception as e:
        logger.error(f"Firebase authentication failed: {e}")
        return None


# Dependency for optional authentication (doesn't raise error if not authenticated)
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[AuthenticatedUser]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None

    try:
        # Try JWT first
        payload = verify_token(credentials.credentials)
        if payload:
            user_email: Optional[str] = payload.get("sub")
            if user_email:
                return AuthenticatedUser(user_email=user_email, user_id=payload.get("user_id", ""), auth_method="jwt")

        # Try Firebase token
        firebase_user = await verify_firebase_token(credentials.credentials)
        if firebase_user:
            return AuthenticatedUser(
                user_email=firebase_user.get("email", ""),
                user_id=firebase_user.get("uid", ""),
                display_name=firebase_user.get("name"),
                photo_url=firebase_user.get("picture"),
                auth_method="firebase",
            )

        return None

    except Exception as e:
        logger.warning(f"Optional authentication failed: {e}")
        return None
