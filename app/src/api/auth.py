"""
Authentication API endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.database import get_db_session
from core.logging import get_logger
from core.responses import success_response, error_response
from core.auth import (
    authenticate_user, get_current_user, get_current_active_user,
    create_token_response, verify_token, get_password_hash,
    AuthenticationError
)
from domains.users.models import User, UserStatus, AuthProvider
from domains.users.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest,
    UserResponse, ChangePasswordRequest, ResetPasswordRequest
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/login")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    User login endpoint.
    
    Returns JWT tokens for valid credentials.
    """
    logger.info("User login attempt", email=request.email)
    
    # Authenticate user
    user = await authenticate_user(request.email, request.password, session)
    if not user:
        return error_response(
            message="Incorrect email or password",
            error_code="invalid_credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Update last login
    from sqlalchemy.sql import func
    user.last_login_at = func.now()
    await session.commit()
    
    # Create token response
    token_data = create_token_response(user)
    
    logger.info("User login successful", user_id=user.id, email=user.email)
    return success_response(
        data=token_data,
        meta={"message": "Login successful"}
    )


@router.get(
    "/me",
    summary="Get Current User Info",
    description="Returns user profile for authenticated user.",
    dependencies=[Depends(get_current_active_user)],
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not enough permissions"}
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Get current user information.
    
    Returns user profile for authenticated user.
    """
    logger.info("Getting current user info", user_id=current_user.id, email=current_user.email)
    
    try:
        # User data with safe property access
        user_data = {
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "full_name": current_user.full_name,
            "subscription_tier": current_user.subscription_tier,
            "is_verified": current_user.is_verified,
            # Role information
            "role": current_user.role.value if current_user.role else "user",
            "is_admin": current_user.is_admin,
            "is_moderator": current_user.is_moderator,
            "is_super_admin": current_user.is_super_admin,
            # Additional properties
            "is_premium": current_user.is_premium,
            "is_active": current_user.is_active,
        }
        
        return success_response(
            data=user_data,
            meta={"message": "Current user information retrieved successfully"}
        )
        
    except Exception as e:
        logger.error("Error getting current user info", error=str(e), user_id=getattr(current_user, 'id', 'unknown'))
        return error_response(
            message=f"Failed to retrieve user information: {str(e)}",
            error_code="user_info_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/logout",
    summary="Logout User",
    description="Logout current user. Clients should discard the token on logout.",
    dependencies=[Depends(get_current_active_user)],
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Not authenticated"}
    }
)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> JSONResponse:
    """
    Logout current user.
    
    Note: Since we're using stateless JWT tokens, this is mainly for 
    logging purposes. Clients should discard the token on logout.
    """
    logger.info("User logout", user_id=current_user.id, email=current_user.email)
    
    return success_response(
        data={"logged_out": True},
        meta={"message": "Logged out successfully"}
    )


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Refresh authentication token.
    
    Returns new access token for valid refresh token.
    """
    logger.info("Token refresh attempt")
    
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token)
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            return error_response(
                message="Invalid token type",
                error_code="invalid_token_type",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        user_id = payload.get("sub")
        if not user_id:
            return error_response(
                message="Invalid token payload",
                error_code="invalid_token_payload",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get user from database
        result = await session.execute(
            select(User).where(User.id == int(user_id), User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return error_response(
                message="User not found or inactive",
                error_code="user_not_found",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        
        # Create new token response
        token_data = create_token_response(user)
        
        logger.info("Token refresh successful", user_id=user.id)
        return success_response(
            data=token_data,
            meta={"message": "Token refreshed successfully"}
        )
        
    except AuthenticationError as e:
        logger.warning("Token refresh failed", error=str(e))
        return error_response(
            message=str(e),
            error_code="authentication_failed",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        logger.error("Token refresh error", error=str(e))
        return error_response(
            message="Token refresh failed",
            error_code="internal_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/register")
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    User registration endpoint.
    
    Creates a new user account and returns JWT tokens.
    """
    logger.info("User registration attempt", email=request.email)
    
    try:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            return error_response(
                message="Email already registered",
                error_code="email_exists",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new user
        user = User(
            email=request.email,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            password_hash=get_password_hash(request.password),
            auth_provider=AuthProvider.EMAIL,
            status=UserStatus.ACTIVE,  # For demo, auto-activate
            is_verified=False,
            subscription_tier='free',
            is_public_profile=True,
            show_portfolio=False,
            show_trading_activity=True,
            beta_features_enabled=False,
            marketing_emails_enabled=True,
        )
        
        # Set full name
        if request.first_name and request.last_name:
            user.full_name = f"{request.first_name} {request.last_name}"
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Create token response
        token_data = create_token_response(user)
        
        logger.info("User registration successful", user_id=user.id, email=user.email)
        return success_response(
            data=token_data,
            meta={"message": "Registration successful"}
        )
        
    except IntegrityError as e:
        await session.rollback()
        logger.error("Database integrity error during registration", error=str(e))
        return error_response(
            message="Registration failed - user may already exist",
            error_code="integrity_error",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        await session.rollback()
        logger.error("Registration error", error=str(e))
        return error_response(
            message="Registration failed",
            error_code="internal_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post(
    "/change-password",
    summary="Change Password",
    description="Change user password. Requires current password verification.",
    dependencies=[Depends(get_current_active_user)],
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Current password is incorrect"},
        401: {"description": "Not authenticated"}
    }
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Change user password.
    
    Requires current password verification.
    """
    logger.info("Password change request", user_id=current_user.id)
    
    # Verify current password
    user = await authenticate_user(current_user.email, request.current_password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    await session.commit()
    
    logger.info("Password changed successfully", user_id=current_user.id)
    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Request password reset.
    
    Sends reset token to user's email.
    """
    logger.info("Password reset request", email=request.email)
    
    # Check if user exists
    result = await session.execute(
        select(User).where(User.email == request.email, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user:
        # In a real app, you'd send an email with reset token
        # For now, we'll just log it
        logger.info("Password reset token would be sent", user_id=user.id)
    
    return {"message": "If an account with that email exists, a reset link has been sent"}




 