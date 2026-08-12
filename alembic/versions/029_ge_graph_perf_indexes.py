"""029: indexes for project graph load/prefetch (GE-PERF-GRAPH).

Revision ID: 029_ge_graph_perf_idx
Revises: 028_dev_rem_task_null
"""

from __future__ import annotations

from alembic import op

revision = "029_ge_graph_perf_idx"
down_revision = "028_dev_rem_task_null"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_ge_tasks_project_id ON ge_tasks(project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ge_gate_items_phase_id ON ge_gate_items(phase_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ge_deviations_project_status "
        "ON ge_deviations(project_id, status)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ge_deviations_project_status")
    op.execute("DROP INDEX IF EXISTS ix_ge_gate_items_phase_id")
    op.execute("DROP INDEX IF EXISTS ix_ge_tasks_project_id")
