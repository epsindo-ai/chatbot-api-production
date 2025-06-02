"""remove_id_from_llm_config

Revision ID: e47f7b78e8b0
Revises: b5e249901a7a
Create Date: 2025-05-14 06:05:17.862950

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'e47f7b78e8b0'
down_revision = 'b5e249901a7a'
branch_labels = None
depends_on = None


def upgrade():
    # Create a temporary table without the ID column
    op.execute("""
    CREATE TABLE llm_config_new (
        name VARCHAR NOT NULL PRIMARY KEY,
        model_name VARCHAR NOT NULL,
        temperature FLOAT,
        top_p FLOAT,
        max_tokens INTEGER,
        description TEXT,
        extra_params JSON,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """)
    
    # Copy data from the old table to the new one
    op.execute("""
    INSERT INTO llm_config_new (
        name, model_name, temperature, top_p, max_tokens, 
        description, extra_params, created_at, updated_at
    )
    SELECT 
        name, model_name, temperature, top_p, max_tokens, 
        description, extra_params, created_at, updated_at
    FROM llm_config
    """)
    
    # Drop the old table
    op.drop_table('llm_config')
    
    # Rename the new table to the original name
    op.rename_table('llm_config_new', 'llm_config')


def downgrade():
    # Create a temporary table with the ID column
    op.execute("""
    CREATE TABLE llm_config_old (
        id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR NOT NULL,
        model_name VARCHAR NOT NULL,
        temperature FLOAT,
        top_p FLOAT,
        max_tokens INTEGER,
        description TEXT,
        extra_params JSON,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
        updated_at TIMESTAMP WITH TIME ZONE
    )
    """)
    
    # Copy data from the current table to the new one
    op.execute("""
    INSERT INTO llm_config_old (
        id, name, model_name, temperature, top_p, max_tokens, 
        description, extra_params, created_at, updated_at
    )
    SELECT 
        1, name, model_name, temperature, top_p, max_tokens, 
        description, extra_params, created_at, updated_at
    FROM llm_config
    """)
    
    # Drop the current table
    op.drop_table('llm_config')
    
    # Rename the temporary table to the original name
    op.rename_table('llm_config_old', 'llm_config') 