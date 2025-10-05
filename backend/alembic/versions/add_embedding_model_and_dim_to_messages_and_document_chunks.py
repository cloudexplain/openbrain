"""Add embedding_model and embedding_dim to messages and document_chunks

Revision ID: 4b2c8d9e1f3a
Revises: remove_user_management
Create Date: 2025-09-24 16:01:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4b2c8d9e1f3a'
down_revision = 'remove_user_management'
branch_labels = None
depends_on = None

def upgrade():
    # messages
    op.add_column(
        "messages",
        sa.Column("embedding_model", sa.String(), nullable=True)
    )
    op.add_column(
        "messages",
        sa.Column("embedding_dim", sa.Integer(), nullable=True)
    )

    # document_chunks
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(), nullable=True)
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_dim", sa.Integer(), nullable=True)
    )

def downgrade():
    op.drop_column("document_chunks", "embedding_dim")
    op.drop_column("document_chunks", "embedding_model")

    op.drop_column("messages", "embedding_dim")
    op.drop_column("messages", "embedding_model")