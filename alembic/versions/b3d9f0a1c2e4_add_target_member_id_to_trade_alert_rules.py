"""Add target_member_id (UUID) to trade_alert_rules and backfill from conditions

The member_trades alert path previously stored the congress member UUID inside
the JSON ``conditions.member_uuid`` field while the alert engine matched on the
integer ``target_id`` column, so member alerts never fired. This adds a proper
UUID column, backfills existing rows, and lets the engine match member to member.

Revision ID: b3d9f0a1c2e4
Revises: 7e4a2b8c1d0f
Create Date: 2026-07-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3d9f0a1c2e4'
down_revision = '7e4a2b8c1d0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'trade_alert_rules',
        sa.Column('target_member_id', sa.UUID(), nullable=True),
    )
    op.create_index(
        'ix_trade_alert_rules_target_member_id',
        'trade_alert_rules',
        ['target_member_id'],
    )
    # Backfill from the legacy JSON conditions.member_uuid for member_trades rules.
    # conditions is a plain JSON (not JSONB) column, so use ->> (valid on json)
    # and a regex guard rather than the jsonb-only ? existence operator.
    op.execute(
        """
        UPDATE trade_alert_rules
        SET target_member_id = (conditions->>'member_uuid')::uuid
        WHERE alert_type = 'member_trades'
          AND target_member_id IS NULL
          AND (conditions->>'member_uuid') ~ '^[0-9a-fA-F-]{36}$'
        """
    )


def downgrade() -> None:
    op.drop_index('ix_trade_alert_rules_target_member_id', table_name='trade_alert_rules')
    op.drop_column('trade_alert_rules', 'target_member_id')
