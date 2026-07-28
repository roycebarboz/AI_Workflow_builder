"""add workflow graph column

Revision ID: a1c4f9e2d8b7
Revises: b2f203ca121e
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4f9e2d8b7'
down_revision: Union[str, Sequence[str], None] = 'b2f203ca121e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'workflows',
        sa.Column('graph', sa.JSON(), nullable=False, server_default='{}'),
    )
    op.alter_column('workflows', 'graph', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('workflows', 'graph')
