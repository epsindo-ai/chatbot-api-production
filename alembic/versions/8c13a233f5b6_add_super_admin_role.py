"""add super admin role

Revision ID: 8c13a233f5b6
Revises: 4060515cb2dd
Create Date: 2025-06-12 07:02:19.534100

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c13a233f5b6'
down_revision = '4060515cb2dd'
branch_labels = None
depends_on = None


def upgrade():
    # Add SUPER_ADMIN to the UserRole enum - note the case matches existing enum values
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum and updating all references
    # For production, consider a more complex migration strategy
    pass 