"""Project definition completeness assessment (PRA SenseEvent-shaped gaps).

Authoritative source for SDA sense / verify and Define-canvas red marks.
GE owns graph semantics (phase envelope, produces, assignees); AA only opens tickets.
"""

from __future__ import annotations

from typing import Any

from app.constants import (
    SYSTEM_END_PHASE_NAME,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_GATE_ITEM_NAMES,
    SYSTEM_START_PHASE_NAME,
    SYSTEM_START_TASK_TITLE,
)

_INACTIVE = frozenset({"cancelled", "archived"})


def _nonempty(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _phase_persisted_end(phase: dict[str, Any]) -> str | None:
    return _nonempty(phase.get("planned_end"))


def _full_window(phase: dict[str, Any]) -> bool:
    return bool(_nonempty(phase.get("planned_start")) and _nonempty(phase.get("planned_end")))


def _is_system_start_end_produce(task: dict[str, Any]) -> bool:
    if not task.get("is_system"):
        return False
    title = str(task.get("title") or "")
    return title in (SYSTEM_START_TASK_TITLE, SYSTEM_END_TASK_TITLE)


def _effective_assignee(task: dict[str, Any], pm_user_id: str | None) -> str:
    if _is_system_start_end_produce(task) and pm_user_id:
        return str(pm_user_id)
    return _nonempty(task.get("assignee_user_id")) or ""


def _is_start_gate_orphan_allowed(gi: dict[str, Any]) -> bool:
    """§3.4.3/§3.4.4：仅开始系统关卡（团队共识）允许暂无签收路由。"""
    return bool(gi.get("is_system")) and str(gi.get("name") or "") in SYSTEM_START_GATE_ITEM_NAMES


def _gate_has_signer_route(
    gi_id: str,
    gi: dict[str, Any],
    *,
    all_tasks: list[dict[str, Any]],
    pm_user_id: str | None,
) -> bool:
    """True when eligible_signers non-empty or any prereq consumer Task has assignee."""
    signers = gi.get("eligible_signers")
    if isinstance(signers, list) and any(_nonempty(s) for s in signers):
        return True
    for task in all_tasks:
        prereqs = [str(p) for p in (task.get("prerequisites") or [])]
        if gi_id not in prereqs:
            continue
        if _effective_assignee(task, pm_user_id):
            return True
    return False


def _gap(
    *,
    type_: str,
    concern_key: str,
    scope_id: str,
    evidence: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    return {
        "type": type_,
        "concern_key": concern_key,
        "scope_kind": "project",
        "scope_id": scope_id,
        "evidence": evidence,
        "message": message,
    }


def assess_definition_gaps_from_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Return PRA-shaped definition gaps for a ProjectGraph dict."""
    project = graph.get("project") or {}
    project_id = str(project.get("id") or "")
    if not project_id:
        return []
    status = str(project.get("status") or "active")
    if status in _INACTIVE:
        return []

    scope_name = _nonempty(project.get("name"))
    scope_bits: dict[str, Any] = {"scope_name": scope_name} if scope_name else {}
    pm_user_id = _nonempty(project.get("pm_user_id"))
    phases: list[dict[str, Any]] = list(graph.get("phases") or [])
    all_tasks: list[dict[str, Any]] = [
        t for phase in phases for t in list(phase.get("tasks") or [])
    ]
    gaps: list[dict[str, Any]] = []

    if len(phases) < 3:
        gaps.append(
            _gap(
                type_="definition.stages_lt_3",
                concern_key=f"pra:def:stages:{project_id}",
                scope_id=project_id,
                evidence={**scope_bits, "stage_count": len(phases), "required": 3, "entity_kind": "project", "entity_id": project_id},
                message=f"阶段数不足（当前 {len(phases)}，至少 3）",
            )
        )

    start_phase: dict[str, Any] | None = None
    end_phase: dict[str, Any] | None = None

    for phase in phases:
        phase_id = str(phase.get("id") or "")
        phase_name = str(phase.get("name") or "")
        is_system = bool(phase.get("is_system"))
        stage_bits = {**scope_bits, "stage_id": phase_id, "stage_name": phase_name}
        if is_system and phase_name == SYSTEM_START_PHASE_NAME:
            start_phase = phase
        if is_system and phase_name == SYSTEM_END_PHASE_NAME:
            end_phase = phase

        items = list(phase.get("gate_items") or [])
        tasks = list(phase.get("tasks") or [])

        if not items:
            gaps.append(
                _gap(
                    type_="definition.stage_incomplete",
                    concern_key=f"pra:def:stage:{phase_id}",
                    scope_id=project_id,
                    evidence={**stage_bits, "missing": "gate", "entity_kind": "stage", "entity_id": phase_id},
                    message="缺少门控项",
                )
            )
        else:
            for gi in items:
                gi_id = str(gi.get("id") or "")
                gi_name = str(gi.get("name") or "")
                gate_bits = {
                    **stage_bits,
                    "gate_id": gi_id,
                    "gate_name": gi_name,
                    "entity_kind": "gate",
                    "entity_id": gi_id,
                }
                producers = [
                    t
                    for t in tasks
                    if gi_id in (t.get("produces") or [])
                ]
                if not producers:
                    gaps.append(
                        _gap(
                            type_="definition.stage_incomplete",
                            concern_key=f"pra:def:stage:{phase_id}:gate:{gi_id}",
                            scope_id=project_id,
                            evidence={**gate_bits, "missing": "producer_task"},
                            message="缺少产出任务",
                        )
                    )
                # §3.4.4 签收完备：无签收路由则定义不过（项目启动 orphan 例外）
                if not _is_start_gate_orphan_allowed(gi) and not _gate_has_signer_route(
                    gi_id,
                    gi,
                    all_tasks=all_tasks,
                    pm_user_id=pm_user_id,
                ):
                    gaps.append(
                        _gap(
                            type_="definition.stage_incomplete",
                            concern_key=f"pra:def:signer:gate:{gi_id}",
                            scope_id=project_id,
                            evidence={**gate_bits, "missing": "signer_route"},
                            message="缺少签收路由（无下游前置任务/签收人）",
                        )
                    )
                if not _nonempty(gi.get("planned_due")):
                    gaps.append(
                        _gap(
                            type_="definition.missing_deadline",
                            concern_key=f"pra:def:due:gate:{gi_id}",
                            scope_id=project_id,
                            evidence=dict(gate_bits),
                            message="缺少截止日",
                        )
                    )

        if not is_system and not _phase_persisted_end(phase):
            gaps.append(
                _gap(
                    type_="definition.missing_deadline",
                    concern_key=f"pra:def:due:stage:{phase_id}",
                    scope_id=project_id,
                    evidence={
                        **stage_bits,
                        "entity_kind": "stage",
                        "entity_id": phase_id,
                        "missing": "window_end",
                    },
                    message="缺少截止日",
                )
            )

        for task in tasks:
            task_id = str(task.get("id") or "")
            if not _effective_assignee(task, pm_user_id):
                gaps.append(
                    _gap(
                        type_="definition.missing_assignee",
                        concern_key=f"pra:def:assignee:task:{task_id}",
                        scope_id=project_id,
                        evidence={
                            **stage_bits,
                            "entity_kind": "task",
                            "entity_id": task_id,
                            "task_id": task_id,
                            "task_title": task.get("title"),
                            "missing": "assignee",
                        },
                        message="缺少负责人",
                    )
                )

    # System phase envelope (project bounds): start/end must each have full persisted window.
    envelope_ok = True
    if start_phase is not None and not _full_window(start_phase):
        envelope_ok = False
        sid = str(start_phase.get("id") or "")
        missing = "window_start" if not _nonempty(start_phase.get("planned_start")) else "window_end"
        if not _nonempty(start_phase.get("planned_start")) and not _nonempty(start_phase.get("planned_end")):
            missing = "window"
        gaps.append(
            _gap(
                type_="definition.missing_deadline",
                concern_key=f"pra:def:due:stage:{sid}",
                scope_id=project_id,
                evidence={
                    **scope_bits,
                    "stage_id": sid,
                    "stage_name": SYSTEM_START_PHASE_NAME,
                    "entity_kind": "stage",
                    "entity_id": sid,
                    "missing": missing,
                },
                message="开始阶段计划窗口未齐",
            )
        )
    if end_phase is not None and not _full_window(end_phase):
        envelope_ok = False
        eid = str(end_phase.get("id") or "")
        missing = "window_start" if not _nonempty(end_phase.get("planned_start")) else "window_end"
        if not _nonempty(end_phase.get("planned_start")) and not _nonempty(end_phase.get("planned_end")):
            missing = "window"
        gaps.append(
            _gap(
                type_="definition.missing_deadline",
                concern_key=f"pra:def:due:stage:{eid}",
                scope_id=project_id,
                evidence={
                    **scope_bits,
                    "stage_id": eid,
                    "stage_name": SYSTEM_END_PHASE_NAME,
                    "entity_kind": "stage",
                    "entity_id": eid,
                    "missing": missing,
                },
                message="结束阶段计划窗口未齐",
            )
        )
    if start_phase is None or end_phase is None:
        envelope_ok = False

    if not envelope_ok:
        gaps.append(
            _gap(
                type_="definition.missing_deadline",
                concern_key=f"pra:def:due:project:{project_id}",
                scope_id=project_id,
                evidence={
                    **scope_bits,
                    "entity_kind": "project",
                    "entity_id": project_id,
                    "missing": "envelope",
                },
                message="项目计划包络未齐（开始/结束阶段窗口）",
            )
        )

    return gaps


def attach_definition_gaps(graph: dict[str, Any]) -> dict[str, Any]:
    """Mutate graph to include definition_gaps (same list as the dedicated endpoint)."""
    graph["definition_gaps"] = assess_definition_gaps_from_graph(graph)
    return graph


def definition_gaps_response(graph: dict[str, Any]) -> dict[str, Any]:
    gaps = assess_definition_gaps_from_graph(graph)
    project_id = str((graph.get("project") or {}).get("id") or "")
    return {"project_id": project_id, "gaps": gaps, "gap_count": len(gaps)}
