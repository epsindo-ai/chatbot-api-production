"""add conversation_id to file_storage

Revision ID: 2299131efc52
Revises: 2d36b79bb67b
Create Date: 2025-05-06 07:47:19.033925

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2299131efc52'
down_revision = '2d36b79bb67b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file_storage', sa.Column('conversation_id', sa.String(), nullable=True))
    op.create_foreign_key(None, 'file_storage', 'conversations', ['conversation_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'file_storage', type_='foreignkey')
    op.drop_column('file_storage', 'conversation_id')
    # ### end Alembic commands ### 