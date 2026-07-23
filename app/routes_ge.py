"""Goal & execution REST routes (P0b–P1 · §4)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth import AuthUser
from app.deps import get_current_user, get_db, require_service_user
from app.models.ge import GeObjective, GeProgram, GeProject
from app.services.ge_access import can_govern_project, can_read_project, filter_projects_for_user
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
from app.services.ge_strategic_lifecycle import refresh_lifecycle_batch, refresh_lifecycle_on_read
from app.schemas.org import ReorderRequest
from app.services.ge_sort_order import (
    annual_root_sort_key,
    reorder_objective,
    reorder_program,
    reorder_project,
    sibling_objectives,
    sibling_programs,
    sibling_projects,
)
from app.services.ge_project_create import create_project
from app.services.ge_queues import build_queues
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

router = APIRouter(prefix="/ge", tags=["ge"])


@router.get("/objectives")
def list_objectives(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    refresh_lifecycle_batch(db)
    db.query(GeObjective).options(joinedload(GeObjective.programs)).all()

    def program_meta(program: GeProgram) -> dict[str, Any]:
        refresh_lifecycle_on_read(db, program)
        return program_out(program, db)

    def build_node(obj: GeObjective) -> dict[str, Any]:
        refresh_lifecycle_on_read(db, obj)
        children = sibling_objectives(db, obj.id)
        programs = (
            []
            if obj.level == "company"
            else [program_meta(p) for p in sibling_programs(db, obj.id)]
        )
        return {
            **objective_out(obj),
            "programs": programs,
            "children": [build_node(child) for child in children],
        }

    roots = sorted(sibling_objectives(db, None), key=annual_root_sort_key)
    db.commit()
    return [build_node(obj) for obj in roots]


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
) -> list[dict[str, Any]]:
    projects = (
        db.query(GeProject)
        .filter(GeProject.deleted_at.is_(None))
        .order_by(GeProject.program_id, GeProject.sort_order, GeProject.name)
        .all()
    )
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


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def post_project(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
    if user.auth_method != "jwt":
        raise HTTPException(status_code=403, detail={"detail": "service_token_required"})
    return create_project(db, actor_user_id=user.user_id, body=body)


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
    }


@router.get("/projects/{project_id}/graph")
def get_project_graph(
    project_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> dict[str, Any]:
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
    graph = build_project_graph(
        db,
        project,
        actor_user_id=user.user_id,
        is_governor=can_govern_project(db, project, user),
    )
    graph["graph_editable"] = graph_editable_flag(db, project, user)
    graph["graph_deletable"] = graph_deletable_flag(db, project, user)
    return graph


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
    user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return create_objective_year(db, body, actor_user_id=user.user_id)


@router.post("/objectives/{objective_id}/assess")
def post_assess_objective(
    objective_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return assess_objective(db, objective_id, body, actor_user_id=user.user_id)


@router.post("/programs/{program_id}/assess")
def post_assess_program(
    program_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthUser, Depends(require_service_user)],
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
    user: Annotated[AuthUser, Depends(get_current_user)],
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


@router.post("/objectives", status_code=status.HTTP_201_CREATED)
def post_objective(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return create_objective(db, body)


@router.patch("/objectives/{objective_id}")
def patch_objective_route(
    objective_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return patch_objective(db, objective_id, body)


@router.post("/programs", status_code=status.HTTP_201_CREATED)
def post_program(
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return create_program(db, body)


@router.patch("/programs/{program_id}")
def patch_program_route(
    program_id: str,
    body: dict[str, Any],
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
    return patch_program(db, program_id, body)


@router.post("/objectives/{objective_id}/reorder")
def reorder_objective_route(
    objective_id: str,
    body: ReorderRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
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
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
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
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> dict[str, Any]:
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
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> None:
    delete_objective(db, objective_id)


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program_route(
    program_id: str,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[AuthUser, Depends(require_service_user)],
) -> None:
    delete_program(db, program_id)
