"""update_subscription_tier_values_to_uppercase

Revision ID: 06f5070a9246
Revises: 8443018f38cb
Create Date: 2025-07-28 03:07:27.841416

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '06f5070a9246'
down_revision = '8443018f38cb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, alter the column to be a string temporarily
    op.alter_column('users', 'subscription_tier',
                    type_=sa.String(),
                    existing_type=sa.Enum('free', 'pro', 'premium', 'enterprise', name='subscription_tier_enum'))
    
    # Drop the old enum type
    op.execute("DROP TYPE subscription_tier_enum CASCADE")
    
    # Create new enum type with uppercase values
    op.execute("CREATE TYPE subscription_tier_enum AS ENUM ('FREE', 'PRO', 'PREMIUM', 'ENTERPRISE')")
    
    # Update existing subscription_tier values from lowercase to uppercase
    op.execute("UPDATE users SET subscription_tier = 'FREE' WHERE subscription_tier = 'free'")
    op.execute("UPDATE users SET subscription_tier = 'PRO' WHERE subscription_tier = 'pro'")
    op.execute("UPDATE users SET subscription_tier = 'PREMIUM' WHERE subscription_tier = 'premium'")
    op.execute("UPDATE users SET subscription_tier = 'ENTERPRISE' WHERE subscription_tier = 'enterprise'")
    
    # Alter the column to use the new enum type
    op.alter_column('users', 'subscription_tier',
                    type_=sa.Enum('FREE', 'PRO', 'PREMIUM', 'ENTERPRISE', name='subscription_tier_enum'),
                    postgresql_using="subscription_tier::subscription_tier_enum",
                    existing_type=sa.String())


def downgrade() -> None:
    # Convert back to lowercase
    op.execute("UPDATE users SET subscription_tier = 'free' WHERE subscription_tier = 'FREE'")
    op.execute("UPDATE users SET subscription_tier = 'pro' WHERE subscription_tier = 'PRO'")
    op.execute("UPDATE users SET subscription_tier = 'premium' WHERE subscription_tier = 'PREMIUM'")
    op.execute("UPDATE users SET subscription_tier = 'enterprise' WHERE subscription_tier = 'ENTERPRISE'")
    
    # Alter the column to be a string temporarily
    op.alter_column('users', 'subscription_tier',
                    type_=sa.String(),
                    existing_type=sa.Enum('FREE', 'PRO', 'PREMIUM', 'ENTERPRISE', name='subscription_tier_enum'))
    
    # Drop the uppercase enum type
    op.execute("DROP TYPE subscription_tier_enum CASCADE")
    
    # Recreate the lowercase enum type
    op.execute("CREATE TYPE subscription_tier_enum AS ENUM ('free', 'pro', 'premium', 'enterprise')")
    
    # Alter the column back to lowercase enum
    op.alter_column('users', 'subscription_tier',
                    type_=sa.Enum('free', 'pro', 'premium', 'enterprise', name='subscription_tier_enum'),
                    postgresql_using="subscription_tier::subscription_tier_enum",
                    existing_type=sa.String()) 