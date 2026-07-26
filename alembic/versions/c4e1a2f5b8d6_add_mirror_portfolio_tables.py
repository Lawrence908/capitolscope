"""Add mirror portfolio tables (user-defined member-mirroring portfolios)

Creates mirror_portfolios (owned by a user) and mirror_portfolio_members
(the congress members a mirror tracks). Combined holdings/returns are computed
on the fly from those members' trades, so only the definition is stored.

Revision ID: c4e1a2f5b8d6
Revises: b3d9f0a1c2e4
Create Date: 2026-07-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e1a2f5b8d6'
down_revision = 'b3d9f0a1c2e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mirror_portfolios',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_mirror_portfolios_user_id', 'mirror_portfolios', ['user_id'])
    op.create_index('idx_mirror_portfolios_active', 'mirror_portfolios', ['is_active'])

    op.create_table(
        'mirror_portfolio_members',
        sa.Column('mirror_portfolio_id', sa.UUID(), nullable=False),
        sa.Column('member_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['mirror_portfolio_id'], ['mirror_portfolios.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['congress_members.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mirror_portfolio_id', 'member_id', name='uq_mirror_portfolio_member'),
    )
    op.create_index('idx_mirror_portfolio_members_portfolio', 'mirror_portfolio_members', ['mirror_portfolio_id'])
    op.create_index('idx_mirror_portfolio_members_member', 'mirror_portfolio_members', ['member_id'])


def downgrade() -> None:
    op.drop_index('idx_mirror_portfolio_members_member', table_name='mirror_portfolio_members')
    op.drop_index('idx_mirror_portfolio_members_portfolio', table_name='mirror_portfolio_members')
    op.drop_table('mirror_portfolio_members')
    op.drop_index('idx_mirror_portfolios_active', table_name='mirror_portfolios')
    op.drop_index('idx_mirror_portfolios_user_id', table_name='mirror_portfolios')
    op.drop_table('mirror_portfolios')
