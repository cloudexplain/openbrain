"""Add folders table for document organization

Revision ID: 685203ca3cfd
Revises: f13a764bb6fe
Create Date: 2025-09-19 08:47:05.977880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '685203ca3cfd'
down_revision = 'f13a764bb6fe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create folders table (without user FK since users table doesn't exist)
    op.create_table(
        'folders',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),  # No FK constraint
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('color', sa.String(7), default='#4F46E5', nullable=False),  # Default indigo color
        sa.Column('parent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('folders.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Add folder_id column to documents table
    op.add_column('documents', sa.Column('folder_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('folders.id'), nullable=True))

    # Create indexes for better performance
    op.create_index('idx_folders_user_id', 'folders', ['user_id'])
    op.create_index('idx_folders_parent_id', 'folders', ['parent_id'])
    op.create_index('idx_documents_folder_id', 'documents', ['folder_id'])


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_documents_folder_id', 'documents')
    op.drop_index('idx_folders_parent_id', 'folders')
    op.drop_index('idx_folders_user_id', 'folders')

    # Remove folder_id column from documents
    op.drop_column('documents', 'folder_id')

    # Drop folders table
    op.drop_table('folders')