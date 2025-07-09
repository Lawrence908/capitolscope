"""
JWT Authentication utilities and middleware.

This module provides JWT token generation, validation, and authentication
middleware for the FastAPI application.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from core.database import get_db_session
from core.config import settings
from core.logging import get_logger
from domains.users.models import User, UserStatus

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Security scheme
security = HTTPBearer()

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthenticationError(Exception):
    """Custom authentication error."""
    pass


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")


# ============================================================================
# USER AUTHENTICATION
# ============================================================================

async def authenticate_user(email: str, password: str, session: AsyncSession) -> Optional[User]:
    """Authenticate user with email and password."""
    try:
        # Find user by email
        result = await session.execute(
            select(User).where(User.email == email, User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning("Authentication failed: user not found", email=email)
            return None
        
        # Check password
        if not user.password_hash or not verify_password(password, user.password_hash):
            logger.warning("Authentication failed: invalid password", email=email)
            return None
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            logger.warning("Authentication failed: user not active", email=email, status=user.status)
            return None
        
        logger.info("User authenticated successfully", email=email, user_id=user.id)
        return user
        
    except Exception as e:
        logger.error("Authentication error", error=str(e), email=email)
        return None


async def get_user_by_id(user_id: int, session: AsyncSession) -> Optional[User]:
    """Get user by ID."""
    try:
        result = await session.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error("Error fetching user", error=str(e), user_id=user_id)
        return None


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session)
) -> User:
    """FastAPI dependency to get current authenticated user."""
    try:
        # Extract token from Authorization header
        token = credentials.credentials
        
        # Verify token
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        # Get user from database
        user = await get_user_by_id(int(user_id), session)
        if user is None:
            raise AuthenticationError("User not found")
        
        # Update last active timestamp
        user.update_last_active()
        await session.commit()
        
        return user
        
    except AuthenticationError as e:
        logger.warning("Authentication failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (additional check)."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


# ============================================================================
# ROLE-BASED ACCESS CONTROL
# ============================================================================

def require_subscription(required_tiers: list[str]):
    """Decorator to require specific subscription tiers."""
    def decorator(current_user: User = Depends(get_current_active_user)):
        if current_user.subscription_tier not in required_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires subscription tier: {', '.join(required_tiers)}"
            )
        return current_user
    return decorator


def require_admin():
    """Decorator to require admin privileges."""
    def decorator(current_user: User = Depends(get_current_active_user)):
        # Check if user is admin (you can implement this based on your needs)
        # For now, let's check if they have enterprise tier as admin
        if current_user.subscription_tier != 'enterprise':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user
    return decorator


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """Optional authentication - returns None if no valid token provided."""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
        
        user = await get_user_by_id(int(user_id), session)
        return user if user and user.is_active else None
        
    except Exception:
        return None


# ============================================================================
# TOKEN RESPONSE HELPERS
# ============================================================================

def create_token_response(user: User) -> Dict[str, Any]:
    """Create token response for successful authentication."""
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "subscription_tier": user.subscription_tier,
            "is_verified": user.is_verified,
            "is_premium": user.is_premium,
        }
    } 