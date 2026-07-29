"""add workflow versioning

Revision ID: c3d5e1f7a9b4
Revises: a1c4f9e2d8b7
Create Date: 2026-07-28 00:00:00.000001

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d5e1f7a9b4'
down_revision: Union[str, Sequence[str], None] = 'a1c4f9e2d8b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'workflow_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('graph', sa.JSON(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('enabled_tools', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('workflows', sa.Column('current_version_id', sa.String(), nullable=True))

    # Backfill: give every pre-existing workflow an initial version snapshot
    # of its current state, so `current_version_id` is never null for a row
    # that already has data. Goes through sa.Table/insert() rather than raw
    # text() so the JSON columns get encoded correctly by the dialect.
    workflows_t = sa.table(
        'workflows',
        sa.column('id', sa.String()),
        sa.column('graph', sa.JSON()),
        sa.column('system_prompt', sa.Text()),
        sa.column('enabled_tools', sa.JSON()),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('current_version_id', sa.String()),
    )
    versions_t = sa.table(
        'workflow_versions',
        sa.column('id', sa.String()),
        sa.column('workflow_id', sa.String()),
        sa.column('graph', sa.JSON()),
        sa.column('system_prompt', sa.Text()),
        sa.column('enabled_tools', sa.JSON()),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )

    connection = op.get_bind()
    workflows = connection.execute(
        sa.select(
            workflows_t.c.id,
            workflows_t.c.graph,
            workflows_t.c.system_prompt,
            workflows_t.c.enabled_tools,
            workflows_t.c.created_at,
        )
    ).fetchall()
    for workflow_id, graph, system_prompt, enabled_tools, created_at in workflows:
        version_id = str(uuid.uuid4())
        connection.execute(
            versions_t.insert().values(
                id=version_id,
                workflow_id=workflow_id,
                graph=graph,
                system_prompt=system_prompt,
                enabled_tools=enabled_tools,
                created_at=created_at,
            )
        )
        connection.execute(
            workflows_t.update()
            .where(workflows_t.c.id == workflow_id)
            .values(current_version_id=version_id)
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('workflows', 'current_version_id')
    op.drop_table('workflow_versions')
