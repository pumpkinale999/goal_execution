"""GE-T51–T57 · system lifecycle tasks (M20)."""

from __future__ import annotations

from app.constants import (
    SYSTEM_END_GATE_ITEM_NAME,
    SYSTEM_END_SIGN_TASK_TITLE,
    SYSTEM_END_TASK_TITLE,
    SYSTEM_START_GATE_ITEM_NAME,
    SYSTEM_START_TASK_TITLE,
)
from tests.conftest import jwt_headers
from tests.ge.conftest import (
    TEST_PROJECT_NOTE_ID,
    U_LISI,
    U_PM,
    U_WANGWU,
    U_ZHANGSAN,
    create_project,
    get_graph,
    material_submit_payload,
    phase_by_name,
    structured_submit_payload,
    task_id_by_title,
)


def test_create_project_seeds_system_lifecycle(client):
    """GE-T51"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    end = phase_by_name(graph, "结束")
    start_task = next(t for t in start["tasks"] if t["title"] == SYSTEM_START_TASK_TITLE)
    end_task = next(t for t in end["tasks"] if t["title"] == SYSTEM_END_TASK_TITLE)
    end_sign_task = next(t for t in end["tasks"] if t["title"] == SYSTEM_END_SIGN_TASK_TITLE)
    start_gi = next(gi for gi in start["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)
    end_gi = next(gi for gi in end["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    assert start_task["is_system"] is True
    assert end_task["is_system"] is True
    assert end_sign_task["is_system"] is True
    assert start_task["assignee_user_id"] == U_PM
    assert end_task["assignee_user_id"] == U_PM
    assert end_sign_task["assignee_user_id"] == U_PM
    assert start_gi["is_system"] is True
    assert end_gi["is_system"] is True
    assert start_gi["id"] in start_task["produces"]
    assert end_gi["id"] in end_task["produces"]
    assert end_gi["id"] in end_sign_task["prerequisites"]
    assert start_gi["id"] in (start["gate"]["includes"] or [])
    assert end_gi["id"] in (end["gate"]["includes"] or [])
    assert created["graph_summary"]["task_count"] == 6
    assert created["graph_summary"]["gate_item_count"] == 4


def test_system_gate_orphan_allowed_business_orphan_rejected(client):
    """GE-T52"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start_gi = next(
        gi for gi in phase_by_name(graph, "开始")["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME
    )
    end_gi = next(
        gi for gi in phase_by_name(graph, "结束")["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME
    )
    assert start_gi["eligible_signers"] == []
    assert end_gi["eligible_signers"] == [U_PM]

    bad = {
        "name": "orphan",
        "pm_user_id": U_PM,
        "project_note_id": TEST_PROJECT_NOTE_ID,
        "phases": [
            {
                "sequence": 1,
                "name": "P1",
                "gate_items": [{"key": "X", "name": "X", "form": "material", "planned_due": "2026-06-10"}],
                "tasks": [
                    {
                        "key": "A",
                        "title": "A",
                        "assignee_user_id": U_ZHANGSAN,
                        "produces": ["X"],
                    }
                ],
            }
        ],
    }
    resp = client.post("/api/v1/ge/projects", headers=jwt_headers(U_PM), json=bad)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "gate_item_orphan_signer"


def test_system_task_and_gate_item_immutable(client):
    """GE-T53"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    task = next(t for t in start["tasks"] if t["title"] == SYSTEM_START_TASK_TITLE)
    gi = next(gi for gi in start["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)

    del_task = client.delete(f"/api/v1/ge/tasks/{task['id']}", headers=jwt_headers(U_PM))
    assert del_task.status_code == 403
    assert del_task.json()["detail"] == "system_task_immutable"

    patch_title = client.patch(
        f"/api/v1/ge/tasks/{task['id']}",
        headers=jwt_headers(U_PM),
        json={"title": "改名"},
    )
    assert patch_title.status_code == 403

    del_gi = client.delete(f"/api/v1/ge/gate-items/{gi['id']}", headers=jwt_headers(U_PM))
    assert del_gi.status_code == 403
    assert del_gi.json()["detail"] == "system_gate_item_immutable"

    patch_name = client.patch(
        f"/api/v1/ge/gate-items/{gi['id']}",
        headers=jwt_headers(U_PM),
        json={"name": "改名"},
    )
    assert patch_name.status_code == 403
    assert patch_name.json()["detail"] == "system_gate_item_immutable"

    # planned_due 可改（须落在开始阶段有效窗口内）
    start_end = start.get("effective_planned_end") or start.get("planned_end")
    assert start_end
    patch_due = client.patch(
        f"/api/v1/ge/gate-items/{gi['id']}",
        headers=jwt_headers(U_PM),
        json={"planned_due": start_end},
    )
    assert patch_due.status_code == 200, patch_due.text
    updated = next(
        item
        for ph in patch_due.json()["phases"]
        for item in ph["gate_items"]
        if item["id"] == gi["id"]
    )
    assert updated["planned_due"] == start_end

    remove_produce = client.delete(
        f"/api/v1/ge/tasks/{task['id']}/produces/{gi['id']}",
        headers=jwt_headers(U_PM),
    )
    assert remove_produce.status_code == 403

    add_gi = client.post(
        f"/api/v1/ge/projects/{created['id']}/phases/{start['id']}/gate-items",
        headers=jwt_headers(U_PM),
        json={"name": "extra", "planned_due": "2026-07-01"},
    )
    assert add_gi.status_code == 403


def test_start_gate_blocks_first_business_phase(client):
    """GE-T54"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    start = phase_by_name(graph, "开始")
    plan = phase_by_name(graph, "方案")
    assert start["gate"]["is_open"] is False
    assert plan["status"] == "pending"


def test_end_gate_blocks_project_completion(client):
    """GE-T55"""
    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    end = phase_by_name(graph, "结束")
    assert end["gate"]["is_open"] is False
    assert graph["project"]["status"] == "active"


def test_system_startup_submit_after_sign_route(client):
    """GE-T56"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    start = phase_by_name(graph, "开始")
    start_gi = next(gi for gi in start["gate_items"] if gi["name"] == SYSTEM_START_GATE_ITEM_NAME)
    start_task_id = task_id_by_title(graph, SYSTEM_START_TASK_TITLE)
    signer_task_id = task_id_by_title(graph, "编写诊断报告")

    link = client.post(
        f"/api/v1/ge/tasks/{signer_task_id}/prerequisites",
        headers=jwt_headers(U_PM),
        json={"gate_item_id": start_gi["id"]},
    )
    assert link.status_code == 200, link.text

    submit = client.post(
        f"/api/v1/ge/gate-items/{start_gi['id']}/submit",
        headers=jwt_headers(U_PM),
        json=structured_submit_payload(True, "项目启动确认"),
    )
    assert submit.status_code == 200, submit.text

    sign = client.post(
        f"/api/v1/ge/gate-items/{start_gi['id']}/sign",
        headers=jwt_headers(U_ZHANGSAN),
    )
    assert sign.status_code == 200, sign.text

    after = get_graph(client, project_id, U_PM)
    assert phase_by_name(after, "开始")["gate"]["is_open"] is True
    assert phase_by_name(after, "方案")["status"] == "active"


def test_backfill_ensures_system_entities_even_with_other_content(client):
    """GE-T57"""
    from scripts.backfill_system_tasks import backfill_project

    from app.db import session_scope
    from app.models.ge import (
        GeGateGateItemInclude,
        GeGateItem,
        GeProject,
        GeTask,
        GeTaskGateItemProduce,
    )
    from app.services.ge_system_tasks import needs_system_start_seed

    created = create_project(client, U_PM, bootstrap_startup=False)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    start = phase_by_name(graph, "开始")
    start_gate_id = start["gate"]["id"]

    with session_scope() as db:
        project = db.get(GeProject, project_id)
        assert project is not None
        system_task = (
            db.query(GeTask)
            .filter(GeTask.phase_id == start["id"], GeTask.is_system.is_(True))
            .one()
        )
        system_gi = (
            db.query(GeGateItem)
            .filter(GeGateItem.phase_id == start["id"], GeGateItem.is_system.is_(True))
            .one()
        )
        db.query(GeTaskGateItemProduce).filter(
            GeTaskGateItemProduce.task_id == system_task.id
        ).delete()
        db.query(GeGateGateItemInclude).filter(
            GeGateGateItemInclude.gate_item_id == system_gi.id
        ).delete()
        db.delete(system_task)
        db.delete(system_gi)
        db.add(
            GeGateItem(
                id="legacy-charter-gi",
                phase_id=start["id"],
                name="project charter",
                form="material",
                status="signed",
                payload='{"target_state":"已确认","target_value":true}',
                planned_due="2026-07-01",
                is_system=False,
                created_at="2026-06-01T00:00:00Z",
                updated_at="2026-06-01T00:00:00Z",
            )
        )
        db.add(GeGateGateItemInclude(gate_id=start_gate_id, gate_item_id="legacy-charter-gi"))
        db.add(
            GeTask(
                id="legacy-charter-task",
                project_id=project_id,
                phase_id=start["id"],
                assignee_user_id=U_PM,
                title="撰写 charter",
                status="done",
                canvas_order=0,
                is_system=False,
                created_at="2026-06-01T00:00:00Z",
                updated_at="2026-06-01T00:00:00Z",
            )
        )
        db.add(GeTaskGateItemProduce(task_id="legacy-charter-task", gate_item_id="legacy-charter-gi"))
        db.flush()
        assert needs_system_start_seed(db, start["id"]) is True
        result = backfill_project(db, project, dry_run=False)
        assert result.startswith("ok:seeded_start=True")

    after = get_graph(client, project_id, U_PM)
    start_after = phase_by_name(after, "开始")
    titles = {task["title"] for task in start_after["tasks"]}
    gi_names = {gi["name"] for gi in start_after["gate_items"]}
    assert SYSTEM_START_TASK_TITLE in titles
    assert SYSTEM_START_GATE_ITEM_NAME in gi_names
    assert "project charter" in gi_names
    assert "撰写 charter" in titles


def test_end_sign_route_prerequisite_immutable(client):
    """GE-T63"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    end = phase_by_name(graph, "结束")
    end_gi = next(gi for gi in end["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    sign_task_id = task_id_by_title(graph, SYSTEM_END_SIGN_TASK_TITLE)

    remove = client.delete(
        f"/api/v1/ge/tasks/{sign_task_id}/prerequisites/{end_gi['id']}",
        headers=jwt_headers(U_PM),
    )
    assert remove.status_code == 403
    assert remove.json()["detail"] == "system_sign_route_immutable"


def test_system_end_sign_task_assignee_immutable(client):
    """GE-T63"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    graph = get_graph(client, created["id"], U_PM)
    sign_task_id = task_id_by_title(graph, SYSTEM_END_SIGN_TASK_TITLE)

    patch = client.patch(
        f"/api/v1/ge/tasks/{sign_task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_ZHANGSAN},
    )
    assert patch.status_code == 403
    assert patch.json()["detail"] == "system_sign_route_immutable"


def test_patch_project_syncs_system_lifecycle_task_assignees(client):
    """GE-T63 · PM 变更时启动/复盘/确认结项负责人同步为新 PM"""
    created = create_project(client, U_PM, bootstrap_startup=False)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    sign_task_id = task_id_by_title(graph, SYSTEM_END_SIGN_TASK_TITLE)
    start_task_id = task_id_by_title(graph, SYSTEM_START_TASK_TITLE)
    end_task_id = task_id_by_title(graph, SYSTEM_END_TASK_TITLE)

    patch = client.patch(
        f"/api/v1/ge/projects/{project_id}",
        headers=jwt_headers(U_PM),
        json={"pm_user_id": U_ZHANGSAN},
    )
    assert patch.status_code == 200, patch.text

    after = get_graph(client, project_id, U_ZHANGSAN)
    start = phase_by_name(after, "开始")
    end = phase_by_name(after, "结束")
    start_task = next(t for t in start["tasks"] if t["id"] == start_task_id)
    end_task = next(t for t in end["tasks"] if t["id"] == end_task_id)
    sign_task = next(t for t in end["tasks"] if t["id"] == sign_task_id)
    end_gi = next(gi for gi in end["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    assert start_task["assignee_user_id"] == U_ZHANGSAN
    assert end_task["assignee_user_id"] == U_ZHANGSAN
    assert sign_task["assignee_user_id"] == U_ZHANGSAN
    assert end_gi["eligible_signers"] == [U_ZHANGSAN]


def test_graph_get_heals_empty_system_task_assignee(client):
    """GET graph 回填系统任务空负责人 → 项目 PM"""
    from app.db import get_session_factory
    from app.models.ge import GeTask

    created = create_project(client, U_PM, bootstrap_startup=False)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    start_task_id = task_id_by_title(graph, SYSTEM_START_TASK_TITLE)

    factory = get_session_factory()
    with factory() as db:
        task = db.get(GeTask, start_task_id)
        assert task is not None
        task.assignee_user_id = None
        db.commit()

    after = get_graph(client, project_id, U_PM)
    start = phase_by_name(after, "开始")
    start_task = next(t for t in start["tasks"] if t["id"] == start_task_id)
    assert start_task["assignee_user_id"] == U_PM


def test_system_start_end_assignee_heal_to_pm(client):
    """启动/复盘可将空负责人写回 PM；不可改成非 PM"""
    from app.db import get_session_factory
    from app.models.ge import GeTask

    created = create_project(client, U_PM, bootstrap_startup=False)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    start_task_id = task_id_by_title(graph, SYSTEM_START_TASK_TITLE)
    end_task_id = task_id_by_title(graph, SYSTEM_END_TASK_TITLE)

    factory = get_session_factory()
    with factory() as db:
        for tid in (start_task_id, end_task_id):
            row = db.get(GeTask, tid)
            assert row is not None
            row.assignee_user_id = None
        db.commit()

    heal_start = client.patch(
        f"/api/v1/ge/tasks/{start_task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_PM},
    )
    assert heal_start.status_code == 200, heal_start.text
    start_after = next(
        t for p in heal_start.json()["phases"] for t in p["tasks"] if t["id"] == start_task_id
    )
    assert start_after["assignee_user_id"] == U_PM

    reject = client.patch(
        f"/api/v1/ge/tasks/{end_task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_ZHANGSAN},
    )
    assert reject.status_code == 403
    assert reject.json()["detail"] == "system_task_assignee_locked_to_pm"

    heal_end = client.patch(
        f"/api/v1/ge/tasks/{end_task_id}",
        headers=jwt_headers(U_PM),
        json={"assignee_user_id": U_PM},
    )
    assert heal_end.status_code == 200, heal_end.text
    end_after = next(t for p in heal_end.json()["phases"] for t in p["tasks"] if t["id"] == end_task_id)
    assert end_after["assignee_user_id"] == U_PM


def test_closure_gate_pm_submit_sign_without_manual_route(client):
    """GE-T63"""
    from tests.ge.conftest import bootstrap_closure_gate, gate_item_id_by_name, material_submit_payload

    created = create_project(client, U_PM)
    project_id = created["id"]
    graph = get_graph(client, project_id, U_PM)
    gi_x = gate_item_id_by_name(graph, "诊断报告")
    client.post(
        f"/api/v1/ge/gate-items/{gi_x}/submit",
        headers=jwt_headers(U_ZHANGSAN),
        json=material_submit_payload("report"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_x}/sign", headers=jwt_headers(U_LISI))

    graph2 = get_graph(client, project_id, U_PM)
    gi_y = gate_item_id_by_name(graph2, "接口规格")
    client.post(
        f"/api/v1/ge/gate-items/{gi_y}/submit",
        headers=jwt_headers(U_LISI),
        json=material_submit_payload("spec"),
    )
    client.post(f"/api/v1/ge/gate-items/{gi_y}/sign", headers=jwt_headers(U_WANGWU))

    bootstrap_closure_gate(client, project_id, U_PM)
    final = get_graph(client, project_id, U_PM)
    end = phase_by_name(final, "结束")
    end_gi = next(gi for gi in end["gate_items"] if gi["name"] == SYSTEM_END_GATE_ITEM_NAME)
    assert end_gi["status"] == "signed"
    assert final["project"]["status"] == "completed"
    assert end["gate"]["is_open"] is True
