"""fix_llm_config_table_add_id_field

Revision ID: 6533613daee3
Revises: 4f6b1fa00461
Create Date: 2025-06-25 18:15:43.539427

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '6533613daee3'
down_revision = '4f6b1fa00461'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing primary key on 'name'
    op.drop_constraint('llm_config_new_pkey', 'llm_config', type_='primary')
    
    # Add the id column
    op.add_column('llm_config', sa.Column('id', sa.Integer(), nullable=False, server_default='1'))
    
    # Create new primary key on 'id'
    op.create_primary_key('pk_llm_config_id', 'llm_config', ['id'])
    
    # Update any NULL extra_params to empty JSON object
    connection = op.get_bind()
    connection.execute(
        text("UPDATE llm_config SET extra_params = '{}' WHERE extra_params IS NULL")
    )


def downgrade():
    # Remove primary key constraint
    op.drop_constraint('pk_llm_config_id', 'llm_config', type_='primary')
    
    # Remove the id column
    op.drop_column('llm_config', 'id')
    
    # Recreate the original primary key on 'name'
    op.create_primary_key('llm_config_new_pkey', 'llm_config', ['name']) 