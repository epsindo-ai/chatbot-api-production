"""add_rag_context_to_messages

Revision ID: 525a987d73b4
Revises: e6df1afb4373
Create Date: 2025-05-09 04:45:37.903633

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '525a987d73b4'
down_revision = 'e6df1afb4373'
branch_labels = None
depends_on = None


def upgrade():
    # Add column to store retrieved RAG context in messages
    op.add_column('messages', sa.Column('rag_context', sa.Text(), nullable=True))
    
    # Add column to store retrieved document IDs
    op.add_column('messages', sa.Column('retrieved_doc_ids', sa.JSON(), nullable=True))
    
    # Add index to improve query performance when searching for messages with RAG context
    op.create_index(op.f('ix_messages_rag_context'), 'messages', ['rag_context'], unique=False, postgresql_where=sa.text('rag_context IS NOT NULL'))


def downgrade():
    # Remove index first
    op.drop_index(op.f('ix_messages_rag_context'), table_name='messages')
    
    # Remove columns
    op.drop_column('messages', 'retrieved_doc_ids')
    op.drop_column('messages', 'rag_context') 