"""add_headline_to_conversation

Revision ID: 65964cf21eb4
Revises: 
Create Date: 2023-05-06 

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65964cf21eb4'
down_revision = None  # This might be different; keep the value that was generated
branch_labels = None
depends_on = None


def upgrade():
    # Add the headline column to the conversations table
    op.add_column('conversations', sa.Column('headline', sa.String(255), nullable=True, comment="Auto-generated headline for the conversation"))


def downgrade():
    # Remove the headline column from the conversations table
    op.drop_column('conversations', 'headline') 