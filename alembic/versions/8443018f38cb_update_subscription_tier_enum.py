"""update_subscription_tier_enum

Revision ID: 8443018f38cb
Revises: beaeff2be89f
Create Date: 2025-07-28 02:47:47.752658

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '8443018f38cb'
down_revision = 'beaeff2be89f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the new enum type
    subscription_tier_enum = postgresql.ENUM('free', 'pro', 'premium', 'enterprise', name='subscription_tier_enum')
    subscription_tier_enum.create(op.get_bind())
    
    # Drop the old check constraint
    op.drop_constraint('check_subscription_tier', 'users', type_='check')
    
    # Alter the column to use the new enum type
    op.alter_column('users', 'subscription_tier',
                    type_=subscription_tier_enum,
                    postgresql_using="subscription_tier::subscription_tier_enum",
                    existing_type=sa.String(20))


def downgrade() -> None:
    # Revert the column back to string
    op.alter_column('users', 'subscription_tier',
                    type_=sa.String(20),
                    existing_type=postgresql.ENUM('free', 'pro', 'premium', 'enterprise', name='subscription_tier_enum'))
    
    # Re-add the old check constraint
    op.create_check_constraint(
        'check_subscription_tier',
        'users',
        "subscription_tier IN ('free', 'pro', 'premium', 'enterprise')"
    )
    
    # Drop the enum type
    subscription_tier_enum = postgresql.ENUM('free', 'pro', 'premium', 'enterprise', name='subscription_tier_enum')
    subscription_tier_enum.drop(op.get_bind()) 