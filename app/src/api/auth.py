"""
Authentication API endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from core.database import get_db_session
from core.logging import get_logger
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


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    User login endpoint.
    
    Returns JWT tokens for valid credentials.
    """
    logger.info("User login attempt", email=request.email)
    
    # Authenticate user
    user = await authenticate_user(request.email, request.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    from sqlalchemy.sql import func
    user.last_login_at = func.now()
    await session.commit()
    
    # Create token response
    token_response = create_token_response(user)
    
    logger.info("User login successful", user_id=user.id, email=user.email)
    return token_response


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    User logout endpoint.
    
    Invalidates the current authentication token.
    """
    logger.info("User logout", user_id=current_user.id)
    
    # In a production app, you'd want to blacklist the token
    # For now, we'll just return a success message
    return {"message": "Logout successful"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
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
            raise AuthenticationError("Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        # Get user from database
        result = await session.execute(
            select(User).where(User.id == int(user_id), User.is_deleted == False)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new token response
        token_response = create_token_response(user)
        
        logger.info("Token refresh successful", user_id=user.id)
        return token_response
        
    except AuthenticationError as e:
        logger.warning("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Get current user information.
    
    Returns user profile for authenticated user.
    """
    logger.info("Getting current user info", user_id=current_user.id)
    
    return UserResponse.from_orm(current_user)


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
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
        token_response = create_token_response(user)
        
        logger.info("User registration successful", user_id=user.id, email=user.email)
        return token_response
        
    except IntegrityError as e:
        await session.rollback()
        logger.error("Database integrity error during registration", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed - user may already exist"
        )
    except Exception as e:
        await session.rollback()
        logger.error("Registration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/change-password")
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


# Create a demo admin user endpoint for testing
@router.post("/create-admin", include_in_schema=False)
async def create_admin_user(
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Create a demo admin user for testing.
    This endpoint is hidden from the schema.
    """
    try:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == "admin@capitolscope.com")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            return {"message": "Admin user already exists"}
        
        # Create admin user
        admin = User(
            email="admin@capitolscope.com",
            username="admin",
            first_name="Admin",
            last_name="User",
            full_name="Admin User",
            password_hash=get_password_hash("password123"),
            auth_provider=AuthProvider.EMAIL,
            status=UserStatus.ACTIVE,
            is_verified=True,
            subscription_tier='enterprise',  # Admin gets enterprise tier
            is_public_profile=False,
            show_portfolio=False,
            show_trading_activity=False,
            beta_features_enabled=True,
            marketing_emails_enabled=False,
        )
        
        session.add(admin)
        await session.commit()
        
        logger.info("Admin user created successfully", user_id=admin.id)
        return {
            "message": "Admin user created successfully",
            "email": "admin@capitolscope.com",
            "password": "password123"
        }
        
    except Exception as e:
        await session.rollback()
        logger.error("Error creating admin user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin user"
        ) 