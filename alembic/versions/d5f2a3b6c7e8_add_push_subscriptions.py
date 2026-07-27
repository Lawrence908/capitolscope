"""Add push_subscriptions table (Web Push device registrations)

Revision ID: d5f2a3b6c7e8
Revises: c4e1a2f5b8d6
Create Date: 2026-07-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f2a3b6c7e8'
down_revision = 'c4e1a2f5b8d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'push_subscriptions',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh_key', sa.Text(), nullable=False),
        sa.Column('auth_key', sa.Text(), nullable=False),
        sa.Column('user_agent', sa.String(length=300), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint', name='uq_push_subscription_endpoint'),
    )
    op.create_index('idx_push_subscriptions_user_id', 'push_subscriptions', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_push_subscriptions_user_id', table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
