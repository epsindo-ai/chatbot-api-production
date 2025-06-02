"""add_display_file_id_to_conversation

Revision ID: a5b24d901c7e
Revises: 1846b788e4ac
Create Date: 2023-12-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5b24d901c7e'
down_revision = '1846b788e4ac'
branch_labels = None
depends_on = None


def upgrade():
    # Add display_file_id column to conversations table
    op.add_column('conversations', sa.Column('display_file_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_conversations_display_file_id", 
        "conversations", 
        "file_storage", 
        ["display_file_id"], 
        ["id"]
    )


def downgrade():
    # Remove foreign key constraint and column
    op.drop_constraint("fk_conversations_display_file_id", "conversations", type_="foreignkey")
    op.drop_column('conversations', 'display_file_id') 