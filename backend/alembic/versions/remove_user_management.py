"""Remove user management tables and columns

Revision ID: remove_user_management
Revises: f13a764bb6fe
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'remove_user_management'
down_revision = 'f13a764bb6fe'
branch_labels = None
depends_on = None


def upgrade():
    # Remove user_id foreign key constraints and columns from all tables
    # Use SQL to safely drop constraints and columns if they exist

    conn = op.get_bind()

    # Drop possible FK names for chats
    conn.execute(text("ALTER TABLE chats DROP CONSTRAINT IF EXISTS fk_chats_user_id;"))
    conn.execute(text("ALTER TABLE chats DROP CONSTRAINT IF EXISTS chats_user_id_fkey;"))

    # Drop possible FK names for documents
    conn.execute(text("ALTER TABLE documents DROP CONSTRAINT IF EXISTS fk_documents_user_id;"))
    conn.execute(text("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_user_id_fkey;"))

    # Drop possible FK names for tags
    conn.execute(text("ALTER TABLE tags DROP CONSTRAINT IF EXISTS fk_tags_user_id;"))
    conn.execute(text("ALTER TABLE tags DROP CONSTRAINT IF EXISTS tags_user_id_fkey;"))

    # Drop columns if they exist
    conn.execute(text("ALTER TABLE chats DROP COLUMN IF EXISTS user_id;"))
    conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS user_id;"))
    conn.execute(text("ALTER TABLE tags DROP COLUMN IF EXISTS user_id;"))

    # Drop tables if they exist
    conn.execute(text("DROP TABLE IF EXISTS email_resend_tracking CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS email_verifications CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))


def downgrade():
    # This is a destructive migration - downgrade would lose all data
    # Not implementing downgrade as removing users is intended to be permanent
    pass