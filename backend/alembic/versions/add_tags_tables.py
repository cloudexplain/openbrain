"""Add tags and document_tags tables

Revision ID: add_tags_tables
Revises: 926edfec6224
Create Date: 2025-08-15 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_tags_tables'
down_revision = '926edfec6224'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table
    op.create_table('tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create index on tag name for faster searches
    op.create_index('idx_tags_name', 'tags', ['name'])
    
    # Create document_tags junction table
    op.create_table('document_tags',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('document_id', 'tag_id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_document_tags_document', 'document_tags', ['document_id'])
    op.create_index('idx_document_tags_tag', 'document_tags', ['tag_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_document_tags_tag', table_name='document_tags')
    op.drop_index('idx_document_tags_document', table_name='document_tags')
    op.drop_index('idx_tags_name', table_name='tags')
    
    # Drop tables
    op.drop_table('document_tags')
    op.drop_table('tags')