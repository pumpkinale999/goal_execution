"""Default middle-phase (方案) graph for project create and shell backfill."""

from __future__ import annotations

from typing import Any

from app.constants import (
    PROPOSAL_GATE_ITEM_NAME,
    PROPOSAL_PHASE_NAME,
    PROPOSAL_RESEARCH_TASK_TITLE,
    PROPOSAL_REVIEW_TASK_TITLE,
    SAMPLE_PHASE_NAME,
)

PROPOSAL_SOLUTION_KEY = "proposal_solution"
SHELL_PHASE_NAMES = frozenset({PROPOSAL_PHASE_NAME, SAMPLE_PHASE_NAME})


def is_empty_shell_phase(phase: dict[str, Any]) -> bool:
    name = str(phase.get("name") or "").strip()
    if name not in SHELL_PHASE_NAMES:
        return False
    return not (phase.get("gate_items") or []) and not (phase.get("tasks") or [])


from app.services.ge_schedule_validate import midpoint_plan_date


def default_proposal_phase_body(
    *,
    pm_user_id: str,
    planned_start: str,
    planned_end: str,
    sequence: int = 1,
) -> dict[str, Any]:
    """Business phase body: 解决方案 + 调研/评审 tasks (评审 produces 解决方案)."""
    return {
        "sequence": sequence,
        "name": PROPOSAL_PHASE_NAME,
        "planned_start": planned_start,
        "planned_end": planned_end,
        "gate_items": [
            {
                "key": PROPOSAL_SOLUTION_KEY,
                "name": PROPOSAL_GATE_ITEM_NAME,
                "form": "material",
                "planned_due": midpoint_plan_date(planned_start, planned_end),
            }
        ],
        "tasks": [
            {
                "title": PROPOSAL_RESEARCH_TASK_TITLE,
                "assignee_user_id": pm_user_id,
                "produces": [],
                "prerequisites": [],
            },
            {
                "title": PROPOSAL_REVIEW_TASK_TITLE,
                "assignee_user_id": pm_user_id,
                "produces": [PROPOSAL_SOLUTION_KEY],
                "prerequisites": [],
            },
        ],
    }


def normalize_business_phases_for_create(
    phases: list[dict[str, Any]] | None,
    *,
    pm_user_id: str,
    lifecycle_start: str,
    lifecycle_end: str,
) -> list[dict[str, Any]]:
    """Inject/fill default 方案 when phases empty or single empty shell."""
    raw = list(phases or [])
    if not raw:
        return [
            default_proposal_phase_body(
                pm_user_id=pm_user_id,
                planned_start=lifecycle_start,
                planned_end=lifecycle_end,
                sequence=1,
            )
        ]
    if len(raw) == 1 and is_empty_shell_phase(raw[0]):
        seq = int(raw[0].get("sequence") or 1)
        return [
            default_proposal_phase_body(
                pm_user_id=pm_user_id,
                planned_start=lifecycle_start,
                planned_end=lifecycle_end,
                sequence=seq,
            )
        ]
    return raw
