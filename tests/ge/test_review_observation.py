"""GE M6.4: submit/sign/reject enqueue observation outbox."""

from __future__ import annotations

from unittest.mock import patch

from tests.conftest import jwt_headers
from tests.ge.conftest import (
    U_LISI,
    U_PM,
    U_WANGWU,
    U_ZHANGSAN,
    create_project,
    gate_item_id_by_name,
    get_graph,
    material_submit_payload,
)


def _outbox_kinds(project_id: str) -> list[str]:
    from app.db import get_session_factory
    from app.models.observation_mount import GeObservationOutbox

    db = get_session_factory()()
    try:
        kinds = []
        for row in db.query(GeObservationOutbox).order_by(GeObservationOutbox.created_at.desc()).all():
            payload = row.payload or {}
            if payload.get("project_id") == project_id:
                kinds.append(str(payload.get("change_kind") or ""))
        return kinds
    finally:
        db.close()


def test_submit_sign_reject_enqueue_observation(client):
    with patch("app.services.observation_mount.schedule_flush_soon"):
        created = create_project(client, U_PM)
        project_id = created["id"]
        graph = get_graph(client, project_id, U_PM)
        gi_x = gate_item_id_by_name(graph, "诊断报告")

        submit = client.post(
            f"/api/v1/ge/gate-items/{gi_x}/submit",
            headers=jwt_headers(U_ZHANGSAN),
            json=material_submit_payload("report for observation"),
        )
        assert submit.status_code == 200, submit.text

        sign = client.post(
            f"/api/v1/ge/gate-items/{gi_x}/sign",
            headers=jwt_headers(U_LISI),
        )
        assert sign.status_code == 200, sign.text

        graph2 = get_graph(client, project_id, U_PM)
        gi_y = gate_item_id_by_name(graph2, "接口规格")
        client.post(
            f"/api/v1/ge/gate-items/{gi_y}/submit",
            headers=jwt_headers(U_LISI),
            json=material_submit_payload("spec for observation"),
        )
        reject = client.post(
            f"/api/v1/ge/gate-items/{gi_y}/reject",
            headers=jwt_headers(U_WANGWU),
            json={"reject_reason": "needs more detail in the summary field here"},
        )
        assert reject.status_code == 200, reject.text

    kinds = _outbox_kinds(project_id)
    assert "gate_item_submit" in kinds
    assert "gate_item_sign" in kinds
    assert "gate_item_reject" in kinds
