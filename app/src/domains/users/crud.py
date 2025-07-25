"""
Users domain CRUD operations.

This module contains repository implementations for user domain
data access operations including authentication and subscription management.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
import uuid
import hashlib

from sqlalchemy import and_, or_, desc, asc, func, text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from domains.base.crud import CRUDBase
from domains.users.interfaces import (
    UserRepositoryInterface, UserPreferenceRepositoryInterface,
    UserWatchlistRepositoryInterface, UserAlertRepositoryInterface,
    UserNotificationRepositoryInterface, UserSessionRepositoryInterface,
    UserApiKeyRepositoryInterface
)
from domains.users.models import (
    User, UserPreference, UserWatchlist, UserAlert,
    UserNotification, UserSession, UserApiKey
)
from domains.users.schemas import (
    UserCreate, UserUpdate, UserDetail, UserSummary,
    UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceDetail,
    UserWatchlistCreate, UserWatchlistUpdate, UserWatchlistDetail, UserWatchlistSummary,
    UserAlertCreate, UserAlertUpdate, UserAlertDetail, UserAlertSummary,
    UserNotificationCreate, UserNotificationDetail, UserNotificationSummary,
    ApiKeyCreate, ApiKeyDetail, ApiKeySummary,
    UserQuery, NotificationQuery, UserStatus
)
from core.exceptions import NotFoundError, ValidationError
import logging
logger = logging.getLogger(__name__)


# ============================================================================
# USER REPOSITORY
# ============================================================================

class UserRepository(CRUDBase[User, UserCreate, UserUpdate], UserRepositoryInterface):
    """Repository for user operations."""
    
    def __init__(self, db: Session):
        super().__init__(User, db)
        self.db = db
    
    async def create(self, user_data: UserCreate) -> UserDetail:
        """Create a new user."""
        try:
            # Generate full name
            full_name = None
            if user_data.first_name and user_data.last_name:
                full_name = f"{user_data.first_name} {user_data.last_name}"
            
            user_dict = user_data.dict(exclude={'password'})
            user_dict['full_name'] = full_name
            
            # Hash password if provided
            if user_data.password:
                user_dict['password_hash'] = self._hash_password(user_data.password)
            
            db_user = User(**user_dict)
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            
            logger.info(f"Created user: {db_user.email} ({db_user.id})")
            return UserDetail.from_orm(db_user)
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise ValidationError(f"User with this email already exists")
    
    async def get_by_id(self, user_id: int) -> Optional[UserDetail]:
        """Get user by ID."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if db_user:
            return UserDetail.from_orm(db_user)
        return None
    
    async def get_by_email(self, email: str) -> Optional[UserDetail]:
        """Get user by email address."""
        db_user = self.db.query(User).filter(User.email == email).first()
        if db_user:
            return UserDetail.from_orm(db_user)
        return None
    
    async def get_by_username(self, username: str) -> Optional[UserDetail]:
        """Get user by username."""
        db_user = self.db.query(User).filter(User.username == username).first()
        if db_user:
            return UserDetail.from_orm(db_user)
        return None
    
    async def get_by_provider_id(self, provider: str, provider_id: str) -> Optional[UserDetail]:
        """Get user by OAuth provider ID."""
        db_user = (
            self.db.query(User)
            .filter(
                and_(
                    User.auth_provider == provider,
                    User.provider_id == provider_id
                )
            )
            .first()
        )
        if db_user:
            return UserDetail.from_orm(db_user)
        return None
    
    async def update(self, user_id: int, update_data: UserUpdate) -> Optional[UserDetail]:
        """Update user profile."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            raise NotFoundError(f"User {user_id} not found")
        
        update_dict = update_data.dict(exclude_unset=True)
        
        # Update full name if first/last name changed
        if 'first_name' in update_dict or 'last_name' in update_dict:
            first_name = update_dict.get('first_name', db_user.first_name)
            last_name = update_dict.get('last_name', db_user.last_name)
            if first_name and last_name:
                update_dict['full_name'] = f"{first_name} {last_name}"
        
        for key, value in update_dict.items():
            setattr(db_user, key, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Updated user: {db_user.email} ({db_user.id})")
        return UserDetail.from_orm(db_user)
    
    async def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update user password."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return False
        
        db_user.password_hash = password_hash
        self.db.commit()
        
        logger.info(f"Updated password for user: {user_id}")
        return True
    
    async def update_subscription(self, user_id: int, subscription_data: Dict[str, Any]) -> UserDetail:
        """Update user subscription information."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            raise NotFoundError(f"User {user_id} not found")
        
        for key, value in subscription_data.items():
            if hasattr(db_user, key):
                setattr(db_user, key, value)
        
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Updated subscription for user: {user_id}")
        return UserDetail.from_orm(db_user)
    
    async def verify_email(self, user_id: int) -> UserDetail:
        """Mark user email as verified."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            raise NotFoundError(f"User {user_id} not found")
        
        db_user.is_verified = True
        db_user.email_verified_at = func.now()
        db_user.status = UserStatus.ACTIVE
        
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Verified email for user: {user_id}")
        return UserDetail.from_orm(db_user)
    
    async def update_last_login(self, user_id: int) -> bool:
        """Update last login timestamp."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return False
        
        db_user.last_login_at = func.now()
        self.db.commit()
        return True
    
    async def update_last_active(self, user_id: int) -> bool:
        """Update last active timestamp."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return False
        
        db_user.last_active_at = func.now()
        self.db.commit()
        return True
    
    async def list_users(self, query: UserQuery) -> Tuple[List[UserSummary], int]:
        """List users with pagination and filtering."""
        db_query = self.db.query(User).filter(User.is_deleted == False)
        
        # Apply filters
        if query.status:
            db_query = db_query.filter(User.status.in_([s.value for s in query.status]))
        
        if query.subscription_tiers:
            db_query = db_query.filter(User.subscription_tier.in_([t.value for t in query.subscription_tiers]))
        
        if query.auth_providers:
            db_query = db_query.filter(User.auth_provider.in_([p.value for p in query.auth_providers]))
        
        if query.is_verified is not None:
            db_query = db_query.filter(User.is_verified == query.is_verified)
        
        if query.search:
            search_term = f"%{query.search}%"
            db_query = db_query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.username.ilike(search_term)
                )
            )
        
        # Count total results
        total_count = db_query.count()
        
        # Apply sorting
        sort_column = getattr(User, query.sort_by, User.created_at)
        if query.sort_order == "desc":
            db_query = db_query.order_by(desc(sort_column))
        else:
            db_query = db_query.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (query.page - 1) * query.limit
        db_users = db_query.offset(offset).limit(query.limit).all()
        
        users = [UserSummary.from_orm(user) for user in db_users]
        return users, total_count
    
    async def search_users(self, search_term: str, limit: int = 10) -> List[UserSummary]:
        """Search users by name or email."""
        search_pattern = f"%{search_term}%"
        db_users = (
            self.db.query(User)
            .filter(
                and_(
                    User.is_deleted == False,
                    or_(
                        User.email.ilike(search_pattern),
                        User.full_name.ilike(search_pattern),
                        User.username.ilike(search_pattern)
                    )
                )
            )
            .order_by(User.full_name)
            .limit(limit)
            .all()
        )
        
        return [UserSummary.from_orm(user) for user in db_users]
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user usage statistics."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return {}
        
        # Get basic statistics
        stats = {
            'user_id': user_id,
            'account_age_days': (datetime.now() - db_user.created_at).days if db_user.created_at else 0,
            'last_login_days_ago': (datetime.now() - db_user.last_login_at).days if db_user.last_login_at else None,
            'api_calls_count': db_user.api_calls_count,
            'subscription_tier': db_user.subscription_tier.value,
        }
        
        # Count related entities
        watchlist_count = self.db.query(func.count(UserWatchlist.id)).filter(UserWatchlist.user_id == user_id).scalar()
        alert_count = self.db.query(func.count(UserAlert.id)).filter(UserAlert.user_id == user_id).scalar()
        notification_count = self.db.query(func.count(UserNotification.id)).filter(UserNotification.user_id == user_id).scalar()
        
        stats.update({
            'watchlist_count': watchlist_count or 0,
            'alert_count': alert_count or 0,
            'total_notification_count': notification_count or 0,
        })
        
        return stats
    
    async def soft_delete(self, user_id: int) -> bool:
        """Soft delete user account."""
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return False
        
        db_user.is_deleted = True
        db_user.deleted_at = func.now()
        db_user.status = UserStatus.INACTIVE
        
        self.db.commit()
        
        logger.info(f"Soft deleted user: {user_id}")
        return True
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 (in production, use bcrypt)."""
        return hashlib.sha256(password.encode()).hexdigest()


# ============================================================================
# USER PREFERENCE REPOSITORY
# ============================================================================

class UserPreferenceRepository(CRUDBase[UserPreference, UserPreferenceCreate, UserPreferenceUpdate], UserPreferenceRepositoryInterface):
    """Repository for user preference operations."""
    
    def __init__(self, db: Session):
        super().__init__(UserPreference, db)
        self.db = db
    
    async def create(self, user_id: int, preferences: UserPreferenceCreate) -> UserPreferenceDetail:
        """Create user preferences."""
        try:
            preference_data = preferences.dict()
            preference_data['user_id'] = user_id
            
            db_preference = UserPreference(**preference_data)
            self.db.add(db_preference)
            self.db.commit()
            self.db.refresh(db_preference)
            
            logger.info(f"Created preferences for user: {user_id}")
            return UserPreferenceDetail.from_orm(db_preference)
            
        except IntegrityError:
            self.db.rollback()
            raise ValidationError("User preferences already exist")
    
    async def get_by_user_id(self, user_id: int) -> Optional[UserPreferenceDetail]:
        """Get user preferences by user ID."""
        db_preference = (
            self.db.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .first()
        )
        
        if db_preference:
            return UserPreferenceDetail.from_orm(db_preference)
        return None
    
    async def update(self, user_id: int, update_data: UserPreferenceUpdate) -> UserPreferenceDetail:
        """Update user preferences."""
        db_preference = (
            self.db.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .first()
        )
        
        if not db_preference:
            # Create preferences if they don't exist
            create_data = UserPreferenceCreate(**update_data.dict(exclude_unset=True))
            return await self.create(user_id, create_data)
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_preference, key, value)
        
        self.db.commit()
        self.db.refresh(db_preference)
        
        logger.info(f"Updated preferences for user: {user_id}")
        return UserPreferenceDetail.from_orm(db_preference)
    
    async def delete(self, user_id: int) -> bool:
        """Delete user preferences."""
        db_preference = (
            self.db.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .first()
        )
        
        if not db_preference:
            return False
        
        self.db.delete(db_preference)
        self.db.commit()
        
        logger.info(f"Deleted preferences for user: {user_id}")
        return True


# ============================================================================
# USER WATCHLIST REPOSITORY
# ============================================================================

class UserWatchlistRepository(CRUDBase[UserWatchlist, UserWatchlistCreate, UserWatchlistUpdate], UserWatchlistRepositoryInterface):
    """Repository for user watchlist operations."""
    
    def __init__(self, db: Session):
        super().__init__(UserWatchlist, db)
        self.db = db
    
    async def create(self, user_id: int, watchlist_data: UserWatchlistCreate) -> UserWatchlistDetail:
        """Create a new watchlist."""
        watchlist_dict = watchlist_data.dict()
        watchlist_dict['user_id'] = user_id
        
        # Calculate initial item count
        securities_count = len(watchlist_dict.get('watched_securities', []))
        members_count = len(watchlist_dict.get('watched_members', []))
        watchlist_dict['item_count'] = securities_count + members_count
        
        db_watchlist = UserWatchlist(**watchlist_dict)
        self.db.add(db_watchlist)
        self.db.commit()
        self.db.refresh(db_watchlist)
        
        logger.info(f"Created watchlist: {db_watchlist.name} for user {user_id}")
        return UserWatchlistDetail.from_orm(db_watchlist)
    
    async def get_by_id(self, watchlist_id: int) -> Optional[UserWatchlistDetail]:
        """Get watchlist by ID."""
        db_watchlist = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.id == watchlist_id)
            .first()
        )
        
        if db_watchlist:
            return UserWatchlistDetail.from_orm(db_watchlist)
        return None
    
    async def get_user_watchlists(self, user_id: int) -> List[UserWatchlistSummary]:
        """Get all watchlists for a user."""
        db_watchlists = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.user_id == user_id)
            .order_by(UserWatchlist.sort_order, UserWatchlist.name)
            .all()
        )
        
        return [UserWatchlistSummary.from_orm(wl) for wl in db_watchlists]
    
    async def get_default_watchlist(self, user_id: int) -> Optional[UserWatchlistDetail]:
        """Get user's default watchlist."""
        db_watchlist = (
            self.db.query(UserWatchlist)
            .filter(
                and_(
                    UserWatchlist.user_id == user_id,
                    UserWatchlist.is_default == True
                )
            )
            .first()
        )
        
        if db_watchlist:
            return UserWatchlistDetail.from_orm(db_watchlist)
        return None
    
    async def update(self, watchlist_id: int, update_data: UserWatchlistUpdate) -> UserWatchlistDetail:
        """Update watchlist."""
        db_watchlist = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.id == watchlist_id)
            .first()
        )
        
        if not db_watchlist:
            raise NotFoundError(f"Watchlist {watchlist_id} not found")
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_watchlist, key, value)
        
        db_watchlist.last_updated = func.now()
        
        self.db.commit()
        self.db.refresh(db_watchlist)
        
        logger.info(f"Updated watchlist: {watchlist_id}")
        return UserWatchlistDetail.from_orm(db_watchlist)
    
    async def add_item(self, watchlist_id: int, item_type: str, item_id: int) -> bool:
        """Add item to watchlist."""
        db_watchlist = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.id == watchlist_id)
            .first()
        )
        
        if not db_watchlist:
            return False
        
        if item_type == 'security':
            db_watchlist.add_security(item_id)
        elif item_type == 'member':
            db_watchlist.add_member(item_id)
        else:
            return False
        
        self.db.commit()
        return True
    
    async def remove_item(self, watchlist_id: int, item_type: str, item_id: int) -> bool:
        """Remove item from watchlist."""
        db_watchlist = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.id == watchlist_id)
            .first()
        )
        
        if not db_watchlist:
            return False
        
        if item_type == 'security':
            db_watchlist.remove_security(item_id)
        elif item_type == 'member':
            db_watchlist.remove_member(item_id)
        else:
            return False
        
        self.db.commit()
        return True
    
    async def delete(self, watchlist_id: int) -> bool:
        """Delete watchlist."""
        db_watchlist = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.id == watchlist_id)
            .first()
        )
        
        if not db_watchlist:
            return False
        
        self.db.delete(db_watchlist)
        self.db.commit()
        
        logger.info(f"Deleted watchlist: {watchlist_id}")
        return True
    
    async def get_public_watchlists(self, limit: int = 50) -> List[UserWatchlistSummary]:
        """Get public watchlists."""
        db_watchlists = (
            self.db.query(UserWatchlist)
            .filter(UserWatchlist.is_public == True)
            .order_by(desc(UserWatchlist.last_updated))
            .limit(limit)
            .all()
        )
        
        return [UserWatchlistSummary.from_orm(wl) for wl in db_watchlists]


# ============================================================================
# USER ALERT REPOSITORY
# ============================================================================

class UserAlertRepository(CRUDBase[UserAlert, UserAlertCreate, UserAlertUpdate], UserAlertRepositoryInterface):
    """Repository for user alert operations."""
    
    def __init__(self, db: Session):
        super().__init__(UserAlert, db)
        self.db = db
    
    async def create(self, user_id: int, alert_data: UserAlertCreate) -> UserAlertDetail:
        """Create a new alert."""
        alert_dict = alert_data.dict()
        alert_dict['user_id'] = user_id
        
        db_alert = UserAlert(**alert_dict)
        self.db.add(db_alert)
        self.db.commit()
        self.db.refresh(db_alert)
        
        logger.info(f"Created alert: {db_alert.name} for user {user_id}")
        return UserAlertDetail.from_orm(db_alert)
    
    async def get_by_id(self, alert_id: int) -> Optional[UserAlertDetail]:
        """Get alert by ID."""
        db_alert = self.db.query(UserAlert).filter(UserAlert.id == alert_id).first()
        if db_alert:
            return UserAlertDetail.from_orm(db_alert)
        return None
    
    async def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[UserAlertSummary]:
        """Get all alerts for a user."""
        db_query = self.db.query(UserAlert).filter(UserAlert.user_id == user_id)
        
        if active_only:
            db_query = db_query.filter(UserAlert.is_active == True)
        
        db_alerts = db_query.order_by(UserAlert.name).all()
        return [UserAlertSummary.from_orm(alert) for alert in db_alerts]
    
    async def update(self, alert_id: int, update_data: UserAlertUpdate) -> UserAlertDetail:
        """Update alert."""
        db_alert = self.db.query(UserAlert).filter(UserAlert.id == alert_id).first()
        if not db_alert:
            raise NotFoundError(f"Alert {alert_id} not found")
        
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_alert, key, value)
        
        self.db.commit()
        self.db.refresh(db_alert)
        
        logger.info(f"Updated alert: {alert_id}")
        return UserAlertDetail.from_orm(db_alert)
    
    async def activate(self, alert_id: int) -> bool:
        """Activate alert."""
        db_alert = self.db.query(UserAlert).filter(UserAlert.id == alert_id).first()
        if not db_alert:
            return False
        
        db_alert.is_active = True
        self.db.commit()
        return True
    
    async def deactivate(self, alert_id: int) -> bool:
        """Deactivate alert."""
        db_alert = self.db.query(UserAlert).filter(UserAlert.id == alert_id).first()
        if not db_alert:
            return False
        
        db_alert.is_active = False
        self.db.commit()
        return True
    
    async def delete(self, alert_id: int) -> bool:
        """Delete alert."""
        db_alert = self.db.query(UserAlert).filter(UserAlert.id == alert_id).first()
        if not db_alert:
            return False
        
        self.db.delete(db_alert)
        self.db.commit()
        
        logger.info(f"Deleted alert: {alert_id}")
        return True
    
    async def trigger_alert(self, alert_id: int) -> bool:
        """Record alert trigger."""
        db_alert = self.db.query(UserAlert).filter(UserAlert.id == alert_id).first()
        if not db_alert:
            return False
        
        db_alert.trigger_alert()
        self.db.commit()
        return True
    
    async def get_alerts_to_check(self) -> List[UserAlertDetail]:
        """Get all active alerts that need to be checked."""
        db_alerts = (
            self.db.query(UserAlert)
            .filter(UserAlert.is_active == True)
            .all()
        )
        
        return [UserAlertDetail.from_orm(alert) for alert in db_alerts]


# ============================================================================
# NOTIFICATION & SESSION REPOSITORIES (Simplified)
# ============================================================================

class UserNotificationRepository(CRUDBase[UserNotification, UserNotificationCreate, dict], UserNotificationRepositoryInterface):
    """Repository for user notification operations."""
    
    def __init__(self, db: Session):
        super().__init__(UserNotification, db)
        self.db = db
    
    async def create(self, user_id: int, notification_data: UserNotificationCreate) -> UserNotificationDetail:
        """Create a new notification."""
        notification_dict = notification_data.dict()
        notification_dict['user_id'] = user_id
        
        db_notification = UserNotification(**notification_dict)
        self.db.add(db_notification)
        self.db.commit()
        self.db.refresh(db_notification)
        
        return UserNotificationDetail.from_orm(db_notification)
    
    async def get_by_id(self, notification_id: int) -> Optional[UserNotificationDetail]:
        """Get notification by ID."""
        db_notification = (
            self.db.query(UserNotification)
            .filter(UserNotification.id == notification_id)
            .first()
        )
        
        if db_notification:
            return UserNotificationDetail.from_orm(db_notification)
        return None
    
    async def get_user_notifications(self, user_id: int, query: NotificationQuery) -> Tuple[List[UserNotificationSummary], int]:
        """Get notifications for a user with pagination."""
        db_query = (
            self.db.query(UserNotification)
            .filter(UserNotification.user_id == user_id)
        )
        
        # Apply filters
        if query.notification_types:
            db_query = db_query.filter(UserNotification.notification_type.in_([t.value for t in query.notification_types]))
        
        if query.channels:
            db_query = db_query.filter(UserNotification.channel.in_([c.value for c in query.channels]))
        
        if query.is_read is not None:
            db_query = db_query.filter(UserNotification.is_read == query.is_read)
        
        if query.priority:
            db_query = db_query.filter(UserNotification.priority == query.priority)
        
        # Count total
        total_count = db_query.count()
        
        # Apply sorting and pagination
        sort_column = getattr(UserNotification, query.sort_by, UserNotification.created_at)
        if query.sort_order == "desc":
            db_query = db_query.order_by(desc(sort_column))
        else:
            db_query = db_query.order_by(asc(sort_column))
        
        offset = (query.page - 1) * query.limit
        db_notifications = db_query.offset(offset).limit(query.limit).all()
        
        notifications = [UserNotificationSummary.from_orm(n) for n in db_notifications]
        return notifications, total_count
    
    async def mark_as_read(self, notification_id: int) -> bool:
        """Mark notification as read."""
        db_notification = (
            self.db.query(UserNotification)
            .filter(UserNotification.id == notification_id)
            .first()
        )
        
        if not db_notification:
            return False
        
        db_notification.mark_as_read()
        self.db.commit()
        return True
    
    async def mark_multiple_as_read(self, notification_ids: List[int]) -> int:
        """Mark multiple notifications as read."""
        count = (
            self.db.query(UserNotification)
            .filter(UserNotification.id.in_(notification_ids))
            .update({'is_read': True, 'read_at': func.now()})
        )
        self.db.commit()
        return count
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        count = (
            self.db.query(UserNotification)
            .filter(
                and_(
                    UserNotification.user_id == user_id,
                    UserNotification.is_read == False
                )
            )
            .update({'is_read': True, 'read_at': func.now()})
        )
        self.db.commit()
        return count
    
    async def delete(self, notification_id: int) -> bool:
        """Delete notification."""
        db_notification = (
            self.db.query(UserNotification)
            .filter(UserNotification.id == notification_id)
            .first()
        )
        
        if not db_notification:
            return False
        
        self.db.delete(db_notification)
        self.db.commit()
        return True
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        return (
            self.db.query(func.count(UserNotification.id))
            .filter(
                and_(
                    UserNotification.user_id == user_id,
                    UserNotification.is_read == False
                )
            )
            .scalar() or 0
        )
    
    async def cleanup_expired(self) -> int:
        """Clean up expired notifications."""
        count = (
            self.db.query(UserNotification)
            .filter(
                and_(
                    UserNotification.expires_at.isnot(None),
                    UserNotification.expires_at < func.now()
                )
            )
            .delete()
        )
        self.db.commit()
        return count


# Note: Session and API Key repositories would be implemented similarly
# For brevity, I'm including simplified stubs

class UserSessionRepository(UserSessionRepositoryInterface):
    """Repository for user session operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_session(self, user_id: int, session_data: Dict[str, Any]) -> str:
        """Create a new user session."""
        # Implementation would create session record
        session_id = str(uuid.uuid4())
        # Create UserSession record
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        # Implementation would fetch session
        return None
    
    # ... other methods would be implemented


class UserApiKeyRepository(UserApiKeyRepositoryInterface):
    """Repository for user API key operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create(self, user_id: int, key_data: ApiKeyCreate) -> ApiKeyDetail:
        """Create a new API key."""
        # Implementation would create API key
        # Generate key, hash it, store in database
        pass
    
    # ... other methods would be implemented


# Log CRUD creation
logger.info("Users domain CRUD operations initialized")

# Export all repositories
__all__ = [
    "UserRepository",
    "UserPreferenceRepository",
    "UserWatchlistRepository",
    "UserAlertRepository", 
    "UserNotificationRepository",
    "UserSessionRepository",
    "UserApiKeyRepository"
] 