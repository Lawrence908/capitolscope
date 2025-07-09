"""Add role column to users table

Revision ID: 20250109_063000
Revises: 816125db32dc
Create Date: 2025-01-09 06:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250109_063000'
down_revision = '816125db32dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the UserRole enum type
    user_role_enum = sa.Enum('USER', 'MODERATOR', 'ADMIN', 'SUPER_ADMIN', name='userrole')
    user_role_enum.create(op.get_bind())
    
    # Add the role column to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', user_role_enum, nullable=False, server_default='USER'))
    
    # Add index for the role column
    op.create_index('idx_user_role', 'users', ['role'])
    
    # Add check constraint for user role
    op.create_check_constraint(
        'check_user_role',
        'users',
        "role IN ('USER', 'MODERATOR', 'ADMIN', 'SUPER_ADMIN')"
    )


def downgrade() -> None:
    # Drop the check constraint
    op.drop_constraint('check_user_role', 'users', type_='check')
    
    # Drop the index
    op.drop_index('idx_user_role', table_name='users')
    
    # Remove the role column
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('role')
    
    # Drop the enum type
    sa.Enum(name='userrole').drop(op.get_bind()) 