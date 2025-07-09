"""Add missing enum types

Revision ID: 816125db32dc
Revises: d66bb0f18e50
Create Date: 2025-07-09 06:18:48.013482

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '816125db32dc'
down_revision = 'd66bb0f18e50'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, create the enum types
    notification_type_enum = sa.Enum('TRADE_ALERT', 'PORTFOLIO_UPDATE', 'NEWS_DIGEST', 'SYSTEM_ANNOUNCEMENT', 'SUBSCRIPTION_UPDATE', name='notificationtype')
    notification_channel_enum = sa.Enum('EMAIL', 'SMS', 'PUSH', 'IN_APP', name='notificationchannel')
    auth_provider_enum = sa.Enum('EMAIL', 'GOOGLE', 'GITHUB', 'TWITTER', name='authprovider')
    user_status_enum = sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION', name='userstatus')
    
    notification_type_enum.create(op.get_bind())
    notification_channel_enum.create(op.get_bind())
    auth_provider_enum.create(op.get_bind())
    user_status_enum.create(op.get_bind())
    
    # Now alter the columns to use the enum types
    with op.batch_alter_table('user_notifications', schema=None) as batch_op:
        batch_op.alter_column('notification_type',
               existing_type=sa.VARCHAR(length=30),
               type_=notification_type_enum,
               existing_nullable=False,
               postgresql_using='notification_type::notificationtype')
        batch_op.alter_column('channel',
               existing_type=sa.VARCHAR(length=10),
               type_=notification_channel_enum,
               existing_nullable=False,
               postgresql_using='channel::notificationchannel')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('auth_provider',
               existing_type=sa.VARCHAR(length=20),
               type_=auth_provider_enum,
               existing_nullable=False,
               postgresql_using='auth_provider::authprovider')
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=30),
               type_=user_status_enum,
               existing_nullable=False,
               postgresql_using='status::userstatus')


def downgrade() -> None:
    # Revert columns back to VARCHAR
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('status',
               existing_type=sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING_VERIFICATION', name='userstatus'),
               type_=sa.VARCHAR(length=30),
               existing_nullable=False)
        batch_op.alter_column('auth_provider',
               existing_type=sa.Enum('EMAIL', 'GOOGLE', 'GITHUB', 'TWITTER', name='authprovider'),
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)

    with op.batch_alter_table('user_notifications', schema=None) as batch_op:
        batch_op.alter_column('channel',
               existing_type=sa.Enum('EMAIL', 'SMS', 'PUSH', 'IN_APP', name='notificationchannel'),
               type_=sa.VARCHAR(length=10),
               existing_nullable=False)
        batch_op.alter_column('notification_type',
               existing_type=sa.Enum('TRADE_ALERT', 'PORTFOLIO_UPDATE', 'NEWS_DIGEST', 'SYSTEM_ANNOUNCEMENT', 'SUBSCRIPTION_UPDATE', name='notificationtype'),
               type_=sa.VARCHAR(length=30),
               existing_nullable=False)
    
    # Drop the enum types
    sa.Enum(name='userstatus').drop(op.get_bind())
    sa.Enum(name='authprovider').drop(op.get_bind())
    sa.Enum(name='notificationchannel').drop(op.get_bind())
    sa.Enum(name='notificationtype').drop(op.get_bind())
