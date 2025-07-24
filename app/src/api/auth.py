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
import logging
logger = logging.getLogger(__name__)
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
from schemas.base import ResponseEnvelope, create_response

router = APIRouter()


@router.post(
    "/login",
    response_model=ResponseEnvelope[TokenResponse],
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        500: {"description": "Internal server error"}
    }
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[TokenResponse]:
    """
    User login endpoint.
    
    Returns JWT tokens for valid credentials.
    """
    logger.info(f"User login attempt: email={request.email}")
    
    # Authenticate user
    user = await authenticate_user(request.email, request.password, session)
    if not user:
        return create_response(error="Incorrect email or password")
    
    # Update last login
    from sqlalchemy.sql import func
    user.last_login_at = func.now()
    await session.commit()
    
    # Create token response
    token_data = create_token_response(user)
    
    logger.info(f"User login successful: user_id={user.id}, email={user.email}")
    return create_response(data=token_data)


@router.get(
    "/me",
    response_model=ResponseEnvelope[UserResponse],
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not enough permissions"}
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> ResponseEnvelope[UserResponse]:
    """
    Get current user information.
    
    Returns user profile for authenticated user.
    """
    logger.info(f"Getting current user info: user_id={current_user.id}, email={current_user.email}")
    
    try:
        # Convert user model to response schema
        user_data = UserResponse.model_validate(current_user)
        return create_response(data=user_data)
        
    except Exception as e:
        logger.error(f"Error getting current user info: error={str(e)}, user_id={getattr(current_user, 'id', 'unknown')}")
        return create_response(error=f"Failed to retrieve user information: {str(e)}")


@router.post(
    "/logout",
    response_model=ResponseEnvelope[Dict[str, bool]],
    responses={
        200: {"description": "Successfully logged out"},
        401: {"description": "Not authenticated"}
    }
)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> ResponseEnvelope[Dict[str, bool]]:
    """
    Logout current user.
    
    Note: Since we're using stateless JWT tokens, this is mainly for 
    logging purposes. Clients should discard the token on logout.
    """
    logger.info(f"User logout: user_id={current_user.id}, email={current_user.email}")
    
    return create_response(data={"logged_out": True})


@router.post(
    "/refresh",
    response_model=ResponseEnvelope[TokenResponse],
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid refresh token"},
        500: {"description": "Internal server error"}
    }
)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[TokenResponse]:
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
            return create_response(error="Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            return create_response(error="Invalid token payload")
        
        # Get user from database
        result = await session.execute(
            select(User).where(User.id == int(user_id), User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            return create_response(error="User not found or inactive")
        
        # Create new token response
        token_data = create_token_response(user)
        
        logger.info(f"Token refresh successful: user_id={user.id}")
        return create_response(data=token_data)
        
    except AuthenticationError as e:
        logger.error(f"Token refresh failed: {str(e)}")
        return create_response(error=str(e))
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return create_response(error="Token refresh failed")


@router.post(
    "/register",
    response_model=ResponseEnvelope[TokenResponse],
    responses={
        200: {"description": "Registration successful"},
        400: {"description": "Email already exists"},
        500: {"description": "Internal server error"}
    }
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[TokenResponse]:
    """
    User registration endpoint.
    
    Creates a new user account and returns JWT tokens.
    """
    logger.info(f"User registration attempt: email={request.email}")
    
    try:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == request.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            return create_response(error="Email already registered")
        
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
        
        logger.info(f"User registration successful: user_id={user.id}, email={user.email}")
        return create_response(data=token_data)
        
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Database integrity error during registration: {str(e)}")
        return create_response(error="Registration failed - user may already exist")
    except Exception as e:
        await session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return create_response(error="Registration failed")


@router.post(
    "/change-password",
    response_model=ResponseEnvelope[Dict[str, str]],
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
) -> ResponseEnvelope[Dict[str, str]]:
    """
    Change user password.
    
    Requires current password verification.
    """
    logger.info(f"Password change request: user_id={current_user.id}")
    
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
    
    logger.info(f"Password changed successfully: user_id={current_user.id}")
    return create_response(data={"message": "Password changed successfully"})


@router.post(
    "/reset-password",
    response_model=ResponseEnvelope[Dict[str, str]],
    responses={
        200: {"description": "Reset email sent if account exists"},
        500: {"description": "Internal server error"}
    }
)
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[Dict[str, str]]:
    """
    Request password reset.
    
    Sends reset token to user's email.
    """
    logger.info(f"Password reset request: email={request.email}")
    
    # Check if user exists
    result = await session.execute(
        select(User).where(User.email == request.email, User.is_deleted == False)
    )
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if user:
        # In a real app, you'd send an email with reset token
        # For now, we'll just log it
        logger.info(f"Password reset token would be sent: user_id={user.id}")
    
    return create_response(data={"message": "If an account with that email exists, a reset link has been sent"})




 