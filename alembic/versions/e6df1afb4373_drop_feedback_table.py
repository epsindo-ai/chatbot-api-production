"""drop_feedback_table

Revision ID: e6df1afb4373
Revises: 6ee941de99bf
Create Date: 2025-05-09 04:21:14.003186

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = 'e6df1afb4373'
down_revision = '6ee941de99bf'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the feedback table
    op.drop_index('ix_feedback_id', table_name='feedback')
    op.drop_table('feedback')


def downgrade():
    # Recreate the feedback table if needed
    op.create_table('feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_feedback_id', 'feedback', ['id'], unique=False) 