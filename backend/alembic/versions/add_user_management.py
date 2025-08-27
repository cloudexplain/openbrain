"""Add user management

Revision ID: add_user_management
Revises: add_tags_tables
Create Date: 2025-08-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_management'
down_revision = 'add_tags_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Add user_id column to chats table
    op.add_column('chats', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_chats_user_id', 'chats', 'users', ['user_id'], ['id'])
    
    # Add user_id column to documents table
    op.add_column('documents', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_documents_user_id', 'documents', 'users', ['user_id'], ['id'])
    
    # Add user_id column to tags table and remove unique constraint on name
    op.drop_constraint('tags_name_key', 'tags', type_='unique')
    op.add_column('tags', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_tags_user_id', 'tags', 'users', ['user_id'], ['id'])
    # Create composite unique constraint for user_id + name
    op.create_unique_constraint('uq_tags_user_id_name', 'tags', ['user_id', 'name'])


def downgrade() -> None:
    # Drop composite unique constraint from tags
    op.drop_constraint('uq_tags_user_id_name', 'tags', type_='unique')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_tags_user_id', 'tags', type_='foreignkey')
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey')
    op.drop_constraint('fk_chats_user_id', 'chats', type_='foreignkey')
    
    # Remove user_id columns
    op.drop_column('tags', 'user_id')
    op.drop_column('documents', 'user_id')
    op.drop_column('chats', 'user_id')
    
    # Restore original unique constraint on tags name
    op.create_unique_constraint('tags_name_key', 'tags', ['name'])
    
    # Drop users table
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')