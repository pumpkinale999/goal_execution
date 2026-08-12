"""Goal & execution REST routes (P0b–P1 · §4)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, attributes

from app.auth import AuthUser
from app.db import db_ok
from app.deps import get_current_user, get_db, require_reviewer, require_service_user
from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_access import (
    can_govern_project,
    can_read_project,
    can_struct_objective,
    can_struct_program,
    filter_projects_for_user,
)
from app.services.ge_goal_subtree_governor import is_goal_subtree_governor
from app.services.ge_graph import build_project_graph, load_project_graph, now_iso, reconcile_project_completion
from app.services.ge_system_tasks import sync_system_lifecycle_task_assignees
from app.services.ge_graph_edit import (
    add_gate_item,
    add_phase,
    add_prerequisite_link,
    add_produce_link,
    add_task,
    delete_gate_item,
    delete_phase,
    delete_task,
    graph_deletable_flag,
    graph_editable_flag,
    patch_gate_item,
    patch_phase,
    patch_task,
    remove_prerequisite_link,
    remove_produce_link,
    reorder_phase_tasks,
)
from app.services.ge_orchestrator import (
    bind_project_note_id,
    patch_project,
    migrate_project_program,
    reject_gate_item,
    sign_gate_item,
    soft_delete_project,
    submit_gate_item,
)
from app.services.ge_deviations import get_deviation, open_deviation, patch_deviation
from app.services.ge_strategic import (
    assess_objective,
    assess_program,
    create_objective,
    create_objective_year,
    create_program,
    delete_objective,
    delete_program,
    objective_out,
    patch_objective,
    patch_program,
    program_out,
)
from app.services.ge_strategic_lifecycle import (
    refresh_lifecycle_batch,
    refresh_lifecycle_entities,
    refresh_lifecycle_on_read,
)
from app.schemas.org import ReorderRequest
from app.services.ge_sort_order import (
    annual_root_sort_key,
    reorder_objective,
    reorder_program,
    reorder_project,
    sibling_projects,
)
from app.services.ge_project_create import create_project
from app.services.ge_queues import build_project_queue_counts, build_queues
from app.services.ge_m12_read import get_gate_item_context, get_task_context, list_audit_events
from app.services.ge_people_summary import (
    get_objective_people_summary,
    get_program_people_summary,
    get_project_people_summary,
)
from app.services.ge_project_members import (
    add_member,
    create_role_option,
    delete_member,
    list_members,
    list_role_options,
    patch_member,
)
from app.services.ge_project_access import build_project_access_for_user

router = APIRouter(prefix="/ge", tags=["ge"])


@router.get("/objectives")
def list_objectives(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    # GE-PERF.1: one-shot load + in-memory tree (no per-node sibling_* queries)
    all_objectives = db.query(GeObjective).all()
    all_programs = db.query(GeProgram).all()
    refresh_lifecycle_entities(db, all_objectives, all_programs)

    obj_by_id = {obj.id: obj for obj in all_objectives}
    # Attach without lazy-load (accessing .objective would SELECT)
    for program in all_programs:
        attributes.set_committed_value(
            program, "objective", obj_by_id.get(program.objective_id)
        )

    children_by_parent: dict[str | None, list[GeObjective]] = {}
    for obj in all_objectives:
        children_by_parent.setdefault(obj.parent_id, []).append(obj)
    for siblings in children_by_parent.values():
        siblings.sort(key=lambda o: (o.sort_order, o.name))

    programs_by_objective: dict[str, list[GeProgram]] = {}
    for program in all_programs:
        programs_by_objective.setdefault(program.objective_id, []).append(program)
    for programs in programs_by_objective.values():
        programs.sort(key=lambda p: (p.sort_order, p.name))

    def program_meta(program: GeProgram) -> dict[str, Any]:
        refresh_lifecycle_on_read(db, program)
        return program_out(program, db)

    def build_node(obj: GeObjective) -> dict[str, Any]:
        refresh_lifecycle_on_read(db, obj)
        programs = (
            []
            if obj.level == "company"
            else [program_meta(p) for p in programs_by_objective.get(obj.id, [])]
        )
        return {
            **objective_out(obj),
            "programs": programs,
            "children": [build_node(child) for child in children_by_parent.get(obj.id, [])],
        }

    roots = sorted(children_by_parent.get(None, []), key=annual_root_sort_key)
    # Build before commit — expire_on_commit would otherwise re-SELECT every row
    tree = [build_node(obj) for obj in roots]
    db.commit()
    return tree


@router.get("/programs")
def list_programs(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    refresh_lifecycle_batch(db)
    programs = db.query(GeProgram).order_by(GeProgram.sort_order, GeProgram.name).all()
    db.commit()
    return [program_out(p, db) for p in programs]


@router.get("/programs/{program_id}")
def get_program(
    program_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    program = db.get(GeProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail={"detail": "not_found"})
    refresh_lifecycle_on_read(db, program)
    db.commit()
    projects = sibling_projects(db, program_id)
    visible = filter_projects_for_user(db, projects, user)
    return {
        **program_out(program, db),
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "status": p.status,
                "pm_user_id": p.pm_user_id,
                "program_id": p.program_id,
                "sort_order": p.sort_order,
            }
            for p in visible
        ],
    }


@router.get("/projects")
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    program_id: str | None = Query(default=None),
    program_ids: Annotated[list[str] | None, Query()] = None,
) -> list[dict[str, Any]]:
    """List projects; optional ``program_ids`` (explode) / ``program_id`` (GE-PERF2.2)."""
    filter_ids: list[str] = []
    if program_ids is not None:
        filter_ids.extend(pid for pid in program_ids if pid)
    if program_id:
        filter_ids.append(program_id)
    # Explicit empty program_ids (and no program_id) → [] not full list (C14 / §3.3.1)
    if program_ids is not None and not filter_ids:
        return []

    q = db.query(GeProject).filter(GeProject.deleted_at.is_(None))
    if filter_ids:
        q = q.filter(GeProject.program_id.in_(list(dict.fromkeys(filter_ids))))
    projects = q.order_by(GeProject.program_id, GeProject.sort_order, GeProject.name).all()
    visible = filter_projects_for_user(db, projects, user)
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "pm_user_id": p.pm_user_id,
            "program_id": p.program_id,
            "created_by_user_id": p.created_by_user_id,
            "project_note_id": p.project_note_id,
            "sort_order": p.sort_order,
        }
        for p in visible
    ]


@router.get("/me/project-access")
def my_project_access(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    all_visible: int = Query(default=0, ge=0, le=1),
) -> dict[str, Any]:
    """K27.6 · batch access for BFF service+actor (GE-AUTHZ-T08)."""
    force = bool(all_visible) and user.is_reviewer
    return build_project_access_for_user(db, user, force_member_all=force)


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def post_project(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    # Create is BFF-only (service token + X-Actor-User-Id + optional Is-Reviewer).
    if user.auth_method != "service":
        raise HTTPException(status_code=403, detail={"detail": "service_token_required"})
    return create_project(db, user=user, body=body)


@router.get("/projects/{project_id}")
def get_project(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_participant"})
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "pm_user_id": project.pm_user_id,
        "program_id": project.program_id,
        "created_by_user_id": project.created_by_user_id,
        "project_note_id": project.project_note_id,
        "sort_order": project.sort_order,
    }


@router.get("/projects/{project_id}/graph")
def get_project_graph(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    view: Annotated[str, Query()] = "canvas",
) -> dict[str, Any]:
    """Project graph. ``view=sense`` skips Canvas ``effective_status`` (PRA / AA)."""
    project = load_project_graph(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_participant"})
    if project.status == "active" and reconcile_project_completion(db, project_id):
        db.commit()
        project = load_project_graph(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    if sync_system_lifecycle_task_assignees(
        db,
        project_id=project.id,
        pm_user_id=project.pm_user_id,
        now=now_iso(),
    ):
        db.commit()
        project = load_project_graph(db, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    sense_view = str(view or "canvas").strip().lower() == "sense"
    graph = build_project_graph(
        db,
        project,
        actor_user_id=None if sense_view else user.user_id,
        is_governor=False if sense_view else can_govern_project(db, project, user),
    )
    if not sense_view:
        graph["graph_editable"] = graph_editable_flag(db, project, user)
        graph["graph_deletable"] = graph_deletable_flag(db, project, user)
    from app.services.ge_assess_definition import attach_definition_gaps

    return attach_definition_gaps(graph)


@router.get("/projects/{project_id}/definition-gaps")
def get_project_definition_gaps(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Authoritative definition completeness gaps (PRA SenseEvent-shaped).

    Builds one sense-style graph (no ``effective_status``) then assesses — same list as
    ``graph.definition_gaps`` on ``GET …/graph?view=sense``.
    """
    project = load_project_graph(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    if not can_read_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_participant"})
    graph = build_project_graph(db, project, actor_user_id=None, is_governor=False)
    from app.services.ge_assess_definition import definition_gaps_response

    return definition_gaps_response(graph)


@router.patch("/projects/{project_id}")
def patch_project_route(
    project_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return patch_project(db, project_id, user, body)


@router.patch("/projects/{project_id}/program")
def patch_project_program_route(
    project_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return migrate_project_program(db, project_id, user, body)


@router.patch("/projects/{project_id}/project-note")
def bind_project_note_route(
    project_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return bind_project_note_id(db, project_id, user, body)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> None:
    soft_delete_project(db, project_id, user)


@router.post("/projects/{project_id}/phases")
def post_project_phase(
    project_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return add_phase(db, project_id, body, user)


@router.patch("/phases/{phase_id}")
def patch_phase_route(
    phase_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return patch_phase(db, phase_id, body, user)


@router.delete("/phases/{phase_id}")
def delete_phase_route(
    phase_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return delete_phase(db, phase_id, user)


@router.post("/projects/{project_id}/phases/{phase_id}/tasks")
def post_project_phase_task(
    project_id: str,
    phase_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return add_task(db, project_id, phase_id, body, user)


@router.put("/projects/{project_id}/phases/{phase_id}/tasks/order")
def put_project_phase_task_order(
    project_id: str,
    phase_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return reorder_phase_tasks(db, project_id, phase_id, body, user)


@router.post("/projects/{project_id}/phases/{phase_id}/gate-items")
def post_project_phase_gate_item(
    project_id: str,
    phase_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return add_gate_item(db, project_id, phase_id, body, user)


@router.patch("/tasks/{task_id}")
def patch_task_route(
    task_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return patch_task(db, task_id, body, user)


@router.delete("/tasks/{task_id}")
def delete_task_route(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return delete_task(db, task_id, user)


@router.post("/tasks/{task_id}/produces")
def post_task_produce(
    task_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    gate_item_id = str(body.get("gate_item_id") or "")
    if not gate_item_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return add_produce_link(db, task_id, gate_item_id, user)


@router.delete("/tasks/{task_id}/produces/{gate_item_id}")
def delete_task_produce(
    task_id: str,
    gate_item_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return remove_produce_link(db, task_id, gate_item_id, user)


@router.post("/tasks/{task_id}/prerequisites")
def post_task_prerequisite(
    task_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    gate_item_id = str(body.get("gate_item_id") or "")
    if not gate_item_id:
        raise HTTPException(status_code=400, detail={"detail": "invalid_request"})
    return add_prerequisite_link(db, task_id, gate_item_id, user)


@router.delete("/tasks/{task_id}/prerequisites/{gate_item_id}")
def delete_task_prerequisite(
    task_id: str,
    gate_item_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return remove_prerequisite_link(db, task_id, gate_item_id, user)


@router.post("/gates/{gate_id}/includes")
def post_gate_include(
    gate_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    del gate_id, body, db, user
    raise HTTPException(status_code=410, detail={"detail": "gate_includes_automatic"})


@router.delete("/gates/{gate_id}/includes/{gate_item_id}")
def delete_gate_include(
    gate_id: str,
    gate_item_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    del gate_id, gate_item_id, db, user
    raise HTTPException(status_code=410, detail={"detail": "gate_includes_automatic"})


@router.post("/gate-items/{gate_item_id}/submit")
def post_submit(
    gate_item_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return submit_gate_item(db, gate_item_id, user, body)


@router.post("/gate-items/{gate_item_id}/sign")
def post_sign(
    gate_item_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return sign_gate_item(db, gate_item_id, user)


@router.patch("/gate-items/{gate_item_id}")
def patch_gate_item_route(
    gate_item_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return patch_gate_item(db, gate_item_id, body, user)


@router.delete("/gate-items/{gate_item_id}")
def delete_gate_item_route(
    gate_item_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return delete_gate_item(db, gate_item_id, user)


@router.post("/gate-items/{gate_item_id}/reject")
def post_reject(
    gate_item_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return reject_gate_item(db, gate_item_id, user, body)


@router.post("/tasks/{task_id}/start", status_code=status.HTTP_410_GONE)
def post_start(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    raise HTTPException(status_code=410, detail={"detail": "task_start_deprecated"})


@router.post("/tasks/{task_id}/done", status_code=status.HTTP_410_GONE)
def post_done(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    raise HTTPException(status_code=410, detail={"detail": "task_done_deprecated"})


@router.post("/gate-items/{gate_item_id}/deviations/open")
def post_open_deviation(
    gate_item_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return open_deviation(db, gate_item_id, user, body or {})


@router.get("/deviations/{deviation_id}")
def get_deviation_route(
    deviation_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return get_deviation(db, deviation_id, user)


@router.patch("/deviations/{deviation_id}")
def patch_deviation_route(
    deviation_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return patch_deviation(db, deviation_id, user, body)


@router.get("/me/queues")
def get_my_queues(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return build_queues(db, user.user_id)


@router.get("/me/project-queue-counts")
def get_my_project_queue_counts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """GE-PERF2.1 · tree badge counts (no queue row arrays)."""
    return build_project_queue_counts(db, user.user_id)


@router.get("/audit-events")
def get_audit_events(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict[str, Any]]:
    return list_audit_events(db, entity_type=entity_type, entity_id=entity_id, limit=limit, user=user)


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return get_task_context(db, task_id, user)


@router.get("/gate-items/{gate_item_id}")
def get_gate_item(
    gate_item_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return get_gate_item_context(db, gate_item_id, user)


@router.post("/objectives/years", status_code=status.HTTP_201_CREATED)
def post_objective_year(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_reviewer)],
) -> dict[str, Any]:
    return create_objective_year(db, body, actor_user_id=user.user_id)


@router.post("/objectives/{objective_id}/assess")
def post_assess_objective(
    objective_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_reviewer)],
) -> dict[str, Any]:
    return assess_objective(db, objective_id, body, actor_user_id=user.user_id)


@router.post("/programs/{program_id}/assess")
def post_assess_program(
    program_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_reviewer)],
) -> dict[str, Any]:
    return assess_program(db, program_id, body, actor_user_id=user.user_id)


@router.get("/objectives/{objective_id}/people-summary")
def get_objective_people_summary_route(
    objective_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    include_completed: int = Query(default=0, ge=0, le=1),
    include_archived: int = Query(default=0, ge=0, le=1),
) -> dict[str, Any]:
    return get_objective_people_summary(
        db,
        objective_id,
        user,
        include_completed=bool(include_completed),
        include_archived=bool(include_archived),
    )


@router.get("/programs/{program_id}/people-summary")
def get_program_people_summary_route(
    program_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    include_completed: int = Query(default=0, ge=0, le=1),
    include_archived: int = Query(default=0, ge=0, le=1),
) -> dict[str, Any]:
    return get_program_people_summary(
        db,
        program_id,
        user,
        include_completed=bool(include_completed),
        include_archived=bool(include_archived),
    )


@router.get("/projects/{project_id}/people-summary")
def get_project_people_summary_route(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
    include_completed: int = Query(default=0, ge=0, le=1),
) -> dict[str, Any]:
    return get_project_people_summary(
        db,
        project_id,
        user,
        include_completed=bool(include_completed),
    )


@router.get("/project-role-options")
def get_project_role_options_route(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return list_role_options(db)


@router.post("/project-role-options", status_code=status.HTTP_201_CREATED)
def post_project_role_option_route(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_reviewer)],
) -> dict[str, Any]:
    return create_role_option(db, body, user=user)


@router.get("/projects/{project_id}/members")
def get_project_members_route(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return list_members(db, project_id, user)


@router.post("/projects/{project_id}/members", status_code=status.HTTP_201_CREATED)
def post_project_member_route(
    project_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return add_member(db, project_id, body, user)


@router.patch("/projects/{project_id}/members/{user_id}")
def patch_project_member_route(
    project_id: str,
    user_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return patch_member(db, project_id, user_id, body, user)


@router.delete("/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_member_route(
    project_id: str,
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> None:
    delete_member(db, project_id, user_id, user)


def _require_struct_objective(db: Session, user: AuthUser, objective_id: str) -> None:
    if not can_struct_objective(db, user, objective_id=objective_id):
        raise HTTPException(status_code=403, detail={"detail": "not_goal_subtree_governor"})


def _require_struct_program(
    db: Session,
    user: AuthUser,
    *,
    program_id: str | None = None,
    objective_id: str | None = None,
) -> None:
    if not can_struct_program(db, user, program_id=program_id, objective_id=objective_id):
        raise HTTPException(status_code=403, detail={"detail": "not_goal_subtree_governor"})


@router.post("/objectives", status_code=status.HTTP_201_CREATED)
def post_objective(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    parent_id = str(body.get("parent_id") or "").strip()
    if not parent_id:
        raise HTTPException(status_code=400, detail={"detail": "parent_id_required"})
    _require_struct_objective(db, user, parent_id)
    return create_objective(db, body)


@router.patch("/objectives/{objective_id}")
def patch_objective_route(
    objective_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_struct_objective(db, user, objective_id)
    return patch_objective(db, objective_id, body)


@router.post("/programs", status_code=status.HTTP_201_CREATED)
def post_program(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    objective_id = str(body.get("objective_id") or "").strip()
    if not objective_id:
        raise HTTPException(status_code=400, detail={"detail": "objective_id_required"})
    _require_struct_program(db, user, objective_id=objective_id)
    return create_program(db, body)


@router.patch("/programs/{program_id}")
def patch_program_route(
    program_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_struct_program(db, user, program_id=program_id)
    return patch_program(db, program_id, body)


@router.post("/objectives/{objective_id}/reorder")
def reorder_objective_route(
    objective_id: str,
    body: ReorderRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_struct_objective(db, user, objective_id)
    now = now_iso()
    obj = reorder_objective(db, objective_id, body.direction)  # type: ignore[arg-type]
    obj.updated_at = now
    db.commit()
    db.refresh(obj)
    return objective_out(obj)


@router.post("/programs/{program_id}/reorder")
def reorder_program_route(
    program_id: str,
    body: ReorderRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    _require_struct_program(db, user, program_id=program_id)
    now = now_iso()
    program = reorder_program(db, program_id, body.direction)  # type: ignore[arg-type]
    program.updated_at = now
    db.commit()
    db.refresh(program)
    return program_out(program, db)


@router.post("/projects/{project_id}/reorder")
def reorder_project_route(
    project_id: str,
    body: ReorderRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    project = db.get(GeProject, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"detail": "project_not_found"})
    if not can_govern_project(db, project, user):
        raise HTTPException(status_code=403, detail={"detail": "not_project_governor"})
    now = now_iso()
    project = reorder_project(db, project_id, body.direction)  # type: ignore[arg-type]
    project.updated_at = now
    db.commit()
    db.refresh(project)
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "pm_user_id": project.pm_user_id,
        "program_id": project.program_id,
        "sort_order": project.sort_order,
    }


@router.delete("/objectives/{objective_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_objective_route(
    objective_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> None:
    _require_struct_objective(db, user, objective_id)
    delete_objective(db, objective_id)


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program_route(
    program_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> None:
    _require_struct_program(db, user, program_id=program_id)
    delete_program(db, program_id)


@router.get("/health")
def ge_health() -> dict[str, bool | str]:
    """GE-AUTHZ-API M2 · E3."""
    return {
        "ok": db_ok(),
        "db_ok": db_ok(),
        "service": "goal_execution",
    }


@router.post("/observation/subscriptions")
def register_observation_subscription(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    """PRA M4: register active_agent (or other) as write-mount subscriber."""
    from app.services.observation_mount import register_subscription

    try:
        row = register_subscription(
            db,
            name=str(body.get("name") or ""),
            target_url=str(body.get("target_url") or ""),
            service_token=str(body.get("service_token") or ""),
            mount_point=str(body.get("mount_point") or "after_project_graph_write"),
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail={"detail": str(e)}) from e
    return {
        "id": row.id,
        "name": row.name,
        "mount_point": row.mount_point,
        "target_url": row.target_url,
        "enabled": row.enabled,
    }


@router.post("/observation/outbox/flush")
def flush_observation_outbox(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    from app.services.observation_mount import deliver_pending

    result = deliver_pending(db)
    db.commit()
    return result


@router.post("/observation/outbox/requeue")
def requeue_observation_outbox(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    """CODE-005 M4: requeue dead outbox rows after fixing subscriber auth (default error_substr=401)."""
    from app.services.observation_mount import requeue_dead_outbox

    try:
        result = requeue_dead_outbox(
            db,
            error_substr=str(body.get("error_substr") if body.get("error_substr") is not None else "401"),
            limit=int(body.get("limit") or 200),
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail={"detail": str(e)}) from e
    return result


@router.get("/observation/outbox")
def list_observation_outbox(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthUser, Depends(require_service_user)],
    status_filter: str | None = Query(default=None),
) -> dict[str, Any]:
    from app.models.observation_mount import GeObservationOutbox

    q = db.query(GeObservationOutbox)
    if status_filter:
        q = q.filter(GeObservationOutbox.status == status_filter)
    rows = q.order_by(GeObservationOutbox.created_at.desc()).limit(100).all()
    return {
        "items": [
            {
                "id": r.id,
                "idempotency_key": r.idempotency_key,
                "mount_point": r.mount_point,
                "status": r.status,
                "attempts": r.attempts,
                "last_error": r.last_error,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    }


@router.get("/goal-subtree-governor/check")
def check_goal_subtree_governor(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
    user_id: str = Query(...),
    objective_id: str | None = Query(default=None),
    program_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
) -> dict[str, bool]:
    """Pure goal-tree query — ignores caller is_reviewer (GE-AUTHZ-T07)."""
    return {
        "is_governor": is_goal_subtree_governor(
            db,
            user_id=user_id,
            objective_id=objective_id,
            program_id=program_id,
            project_id=project_id,
        )
    }


@router.get("/users/{user_id}/project-access")
def user_project_access(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _svc: Annotated[AuthUser, Depends(require_service_user)],
    all_visible: bool = Query(
        default=False,
        description="When true, return every non-deleted project with role=member (reviewer BFF).",
    ),
) -> dict[str, Any]:
    """K27.6 · batch access table for BFF (service token) · GE-AUTHZ M2 E1."""
    subject = AuthUser(user_id=str(user_id).strip(), auth_method="service", is_reviewer=False)
    return build_project_access_for_user(
        db,
        subject,
        force_member_all=bool(all_visible),
    )
