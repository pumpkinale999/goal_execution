"""GE-AUTHZ-T15 / T16 · M8 portfolio domain authz via §3.2 headers.

ORG-DEPT-GE-VAL-F1: authz tests must not seed GE org_* as portfolio authority.
"""

from __future__ import annotations

from app.services.ge_portfolio_authz import (
    HDR_PORTFOLIO_DEPTS,
    HDR_PORTFOLIO_TEAMS,
    HDR_TARGET_DEPT,
    HDR_TARGET_TEAM,
)
from tests.conftest import service_headers


def test_ge_authz_t15_department_requires_claim_or_reviewer(client):
    dept_id = "m8-dept-a"
    stranger = client.get(
        f"/api/v1/ge/portfolios/departments/{dept_id}",
        headers=service_headers("stranger"),
    )
    assert stranger.status_code == 403

    allowed = client.get(
        f"/api/v1/ge/portfolios/departments/{dept_id}",
        headers={
            **service_headers("mgr-1"),
            HDR_PORTFOLIO_DEPTS: dept_id,
        },
    )
    assert allowed.status_code == 200, allowed.text

    reviewer = client.get(
        f"/api/v1/ge/portfolios/departments/{dept_id}",
        headers=service_headers("rev", is_reviewer=True),
    )
    assert reviewer.status_code == 200


def test_ge_authz_t15_migrate_reviewer_only(client):
    source = "m8-src"
    denied = client.post(
        f"/api/v1/ge/portfolios/departments/{source}/migrate-primary-objectives",
        headers={
            **service_headers("mgr-1"),
            HDR_PORTFOLIO_DEPTS: f"{source},m8-tgt",
        },
        json={"target_department_id": "m8-tgt"},
    )
    assert denied.status_code == 403

    ok = client.post(
        f"/api/v1/ge/portfolios/departments/{source}/migrate-primary-objectives",
        headers=service_headers("rev", is_reviewer=True),
        json={"target_department_id": "m8-tgt"},
    )
    assert ok.status_code == 200, ok.text


def test_ge_authz_t16_missing_headers_not_silent_allow(client):
    dept_id = "m8-missing"
    resp = client.get(
        f"/api/v1/ge/portfolios/departments/{dept_id}",
        headers=service_headers("actor-x"),
    )
    assert resp.status_code == 403
    detail = resp.json().get("detail")
    assert detail == "portfolio_forbidden" or (
        isinstance(detail, dict) and detail.get("detail") == "portfolio_forbidden"
    )


def test_ge_authz_t15_user_portfolio_self_or_target_claims(client):
    self_ok = client.get(
        "/api/v1/ge/portfolios/users/actor-self",
        headers=service_headers("actor-self"),
    )
    assert self_ok.status_code == 200, self_ok.text

    other_denied = client.get(
        "/api/v1/ge/portfolios/users/other-user",
        headers=service_headers("actor-self"),
    )
    assert other_denied.status_code == 403

    other_ok = client.get(
        "/api/v1/ge/portfolios/users/other-user",
        headers={
            **service_headers("actor-self"),
            HDR_PORTFOLIO_DEPTS: "d-other",
            HDR_TARGET_DEPT: "d-other",
        },
    )
    assert other_ok.status_code == 200, other_ok.text

    team_ok = client.get(
        "/api/v1/ge/portfolios/users/other-user",
        headers={
            **service_headers("actor-self"),
            HDR_PORTFOLIO_TEAMS: "t-other",
            HDR_TARGET_TEAM: "t-other",
        },
    )
    assert team_ok.status_code == 200, team_ok.text
