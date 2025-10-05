"""Add email verification system

Revision ID: add_email_verification
Revises: add_sessions_001
Create Date: 2025-08-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_email_verification'
down_revision = 'add_sessions_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email and verification fields to users table
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('verification_grace_expires_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create unique index on email
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create email_verifications table
    op.create_table('email_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('verification_token', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('resend_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_verifications_verification_token'), 'email_verifications', ['verification_token'], unique=True)
    op.create_index(op.f('ix_email_verifications_user_id'), 'email_verifications', ['user_id'], unique=False)
    
    # Create email_resend_tracking table for rate limiting
    op.create_table('email_resend_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('attempt_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_resend_tracking_user_id'), 'email_resend_tracking', ['user_id'], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    def safe_drop_index(index_name, table_name):
        indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        if index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
    # Drop email_resend_tracking table
    op.drop_index(op.f('ix_email_resend_tracking_user_id'), table_name='email_resend_tracking')
    op.drop_table('email_resend_tracking')
    
    # Drop email_verifications table
    op.drop_index(op.f('ix_email_verifications_user_id'), table_name='email_verifications')
    op.drop_index(op.f('ix_email_verifications_verification_token'), table_name='email_verifications')
    op.drop_table('email_verifications')
    
    # Remove columns from users table
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'verification_grace_expires_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'email')
