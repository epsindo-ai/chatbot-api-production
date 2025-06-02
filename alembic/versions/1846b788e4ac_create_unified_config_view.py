"""create_unified_config_view

Revision ID: 1846b788e4ac
Revises: e47f7b78e8b0
Create Date: 2025-05-14 06:06:02.021484

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1846b788e4ac'
down_revision = 'e47f7b78e8b0'
branch_labels = None
depends_on = None


def upgrade():
    # Create a view that combines admin_config and llm_config
    op.execute("""
    CREATE OR REPLACE VIEW unified_config AS
    SELECT 
        'admin' as config_type,
        key as name,
        value::jsonb as value,
        description,
        created_at,
        updated_at
    FROM 
        admin_config
    UNION ALL
    SELECT 
        'llm' as config_type,
        name,
        jsonb_build_object(
            'model_name', model_name,
            'temperature', temperature,
            'top_p', top_p,
            'max_tokens', max_tokens,
            'extra_params', extra_params
        ) as value,
        description,
        created_at,
        updated_at
    FROM 
        llm_config
    """)


def downgrade():
    # Drop the view
    op.execute("DROP VIEW IF EXISTS unified_config") 