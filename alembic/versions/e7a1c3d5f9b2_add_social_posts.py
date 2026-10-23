"""Add social_posts and social_post_trades (X bot drafts + dedup)

Revision ID: e7a1c3d5f9b2
Revises: d5f2a3b6c7e8
Create Date: 2026-10-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7a1c3d5f9b2'
down_revision = 'd5f2a3b6c7e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'social_posts',
        sa.Column('platform', sa.String(length=20), nullable=False, server_default='x'),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('thread', sa.JSON(), nullable=True),
        sa.Column('link_url', sa.String(length=500), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('member_id', sa.UUID(), nullable=True),
        sa.Column('external_id', sa.String(length=64), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['member_id'], ['congress_members.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_social_posts_status', 'social_posts', ['status'])
    op.create_index('ix_social_posts_member_id', 'social_posts', ['member_id'])
    op.create_index('ix_social_posts_posted_at', 'social_posts', ['posted_at'])

    op.create_table(
        'social_post_trades',
        sa.Column('post_id', sa.UUID(), nullable=False),
        sa.Column('trade_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['social_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trade_id'], ['congressional_trades.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_id', name='uq_social_post_trades_trade_id'),
    )
    op.create_index('ix_social_post_trades_post_id', 'social_post_trades', ['post_id'])


def downgrade() -> None:
    op.drop_index('ix_social_post_trades_post_id', table_name='social_post_trades')
    op.drop_table('social_post_trades')
    op.drop_index('ix_social_posts_posted_at', table_name='social_posts')
    op.drop_index('ix_social_posts_member_id', table_name='social_posts')
    op.drop_index('ix_social_posts_status', table_name='social_posts')
    op.drop_table('social_posts')
