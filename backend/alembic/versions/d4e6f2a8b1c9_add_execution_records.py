"""add execution records

Revision ID: d4e6f2a8b1c9
Revises: c3d5e1f7a9b4
Create Date: 2026-07-28 00:00:00.000002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e6f2a8b1c9'
down_revision: Union[str, Sequence[str], None] = 'c3d5e1f7a9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'execution_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_version_id', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transcript', sa.JSON(), nullable=False),
        sa.Column('tool_calls', sa.JSON(), nullable=False),
        sa.Column('final_response', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_version_id'], ['workflow_versions.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('execution_records')
