"""
JWT Authentication utilities and middleware.

This module provides JWT token generation, validation, and authentication
middleware for the FastAPI application.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt, JWTError

from core.database import get_db_session
from core.config import settings
import logging
logger = logging.getLogger(__name__)
from domains.users.models import User, UserStatus

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Custom JWT Security scheme with proper naming for OpenAPI
class CustomHTTPBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.scheme_name = "bearerAuth"  # This matches our OpenAPI definition

# JWT Security scheme
security = CustomHTTPBearer()

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
    encoded_jwt = jwt.encode(to_encode, settings.effective_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.effective_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.effective_secret_key, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except JWTError:
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
            logger.warning(f"Authentication failed: user not found, email={email}")
            return None
        
        # Check password
        if not user.password_hash or not verify_password(password, user.password_hash):
            logger.warning(f"Authentication failed: invalid password, email={email}")
            return None
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            logger.warning(f"Authentication failed: user not active, email={email}, status={user.status}")
            return None
        
        logger.info(f"User authenticated successfully, email={email}, user_id={user.id}")
        return user
        
    except ValueError as e:
        # Handle enum validation errors (case mismatch between DB and Python enum)
        if "is not among the defined enum values" in str(e):
            logger.error(f"Enum validation error - database values don't match Python enum. Email={email}, error={str(e)}")
            # For now, return None to prevent login, but log the issue
            return None
        else:
            logger.error(f"ValueError in authentication, email={email}, error={str(e)}")
            return None
    except Exception as e:
        logger.error(f"Authentication error, email={email}, error={str(e)}")
        return None


async def get_user_by_id(user_id: str, session: AsyncSession) -> Optional[User]:
    """Get user by ID."""
    try:
        result = await session.execute(
            select(User).where(User.id == user_id, User.is_deleted == False)
        )
        return result.scalar_one_or_none()
    except ValueError as e:
        # Handle enum validation errors (case mismatch between DB and Python enum)
        if "is not among the defined enum values" in str(e):
            logger.error(f"Enum validation error - database values don't match Python enum. User ID={user_id}, error={str(e)}")
            return None
        else:
            logger.error(f"ValueError fetching user, user_id={user_id}, error={str(e)}")
            return None
    except Exception as e:
        logger.error(f"Error fetching user, user_id={user_id}, error={str(e)}")
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
        user = await get_user_by_id(user_id, session)
        if user is None:
            raise AuthenticationError("User not found")
        
        return user
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error, error={str(e)}")
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


def require_role(required_roles: list[str]):
    """Decorator to require specific user roles."""
    def decorator(current_user: User = Depends(get_current_active_user)):
        from domains.users.models import UserRole
        
        # Convert string roles to UserRole enums for comparison
        required_role_enums = []
        for role_str in required_roles:
            try:
                required_role_enums.append(UserRole(role_str))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid role specified: {role_str}"
                )
        
        if current_user.role not in required_role_enums:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(required_roles)}"
            )
        return current_user
    return decorator


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def decorator(current_user: User = Depends(get_current_active_user)):
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires permission: {permission}"
            )
        return current_user
    return decorator


def require_admin():
    """Decorator to require admin privileges."""
    def decorator(current_user: User = Depends(get_current_active_user)):
        if not (current_user.is_admin or current_user.is_super_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return current_user
    return decorator


def require_moderator():
    """Decorator to require moderator privileges or higher."""
    def decorator(current_user: User = Depends(get_current_active_user)):
        if not current_user.is_moderator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Moderator privileges or higher required"
            )
        return current_user
    return decorator


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(CustomHTTPBearer(auto_error=False)),
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
        
        user = await get_user_by_id(user_id, session)
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
    
    # Safely access attributes that might not be loaded to avoid lazy loading issues
    try:
        last_login_at = user.last_login_at
    except:
        last_login_at = None
    
    try:
        updated_at = user.updated_at
    except:
        updated_at = None
    
    try:
        created_at = user.created_at
    except:
        created_at = None
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "location": user.location,
            "website_url": user.website_url,
            # Status
            "status": user.status,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "last_login_at": last_login_at,
            # Subscription
            "subscription_tier": user.subscription_tier,
            "is_premium": user.is_premium,
            # Privacy
            "is_public_profile": user.is_public_profile,
            "show_portfolio": user.show_portfolio,
            "show_trading_activity": user.show_trading_activity,
            # Timestamps
            "created_at": created_at,
            "updated_at": updated_at,
        }
    } 