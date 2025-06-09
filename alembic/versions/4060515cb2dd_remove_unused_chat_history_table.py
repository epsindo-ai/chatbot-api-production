"""remove_unused_chat_history_table

Revision ID: 4060515cb2dd
Revises: fa7090d9473e
Create Date: 2025-06-09 06:41:41.512706

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4060515cb2dd'
down_revision = 'fa7090d9473e'
branch_labels = None
depends_on = None


def upgrade():
    # Remove unused chat_history table (if it exists)
    op.execute("DROP TABLE IF EXISTS chat_history")


def downgrade():
    # Recreate chat_history table for downgrade
    op.create_table('chat_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('meta_data', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_history_id'), 'chat_history', ['id'], unique=False) 