"""add_specific_notification_fields_to_user_preferences

Revision ID: 842029b32a9b
Revises: 06f5070a9246
Create Date: 2025-07-28 10:37:12.988178

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '842029b32a9b'
down_revision = '06f5070a9246'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add specific notification fields to user_preferences table
    op.add_column('user_preferences', sa.Column('trade_alerts', sa.Boolean(), nullable=True))
    op.add_column('user_preferences', sa.Column('weekly_summary', sa.Boolean(), nullable=True))
    op.add_column('user_preferences', sa.Column('multiple_buyer_alerts', sa.Boolean(), nullable=True))
    op.add_column('user_preferences', sa.Column('high_value_alerts', sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Remove the specific notification fields
    op.drop_column('user_preferences', 'high_value_alerts')
    op.drop_column('user_preferences', 'multiple_buyer_alerts')
    op.drop_column('user_preferences', 'weekly_summary')
    op.drop_column('user_preferences', 'trade_alerts')
