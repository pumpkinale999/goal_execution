#!/usr/bin/env python3
"""Live GE authz smoke: reviewer / objective·sub·program owner / PM / member.

Calls GE :8092 with service + X-Actor-* headers (authz truth). Creates an
isolated fixture under 快速增长, asserts the matrix, then cleans up.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib import error, request

GE = os.environ.get("GOAL_EXECUTION_URL", "http://127.0.0.1:8092").rstrip("/") + "/api/v1/ge"
SKSTUDIO_ENV = Path(os.environ.get("SKSTUDIO_ENV", "/Users/skbx090/projects/skstudio/backend/.env"))

PARENT_COMPANY = "dbe7a068-89e8-4e4c-8194-1a1bb99bd562"  # 快速增长
DEPT = "84e84e3f-51ec-49b9-9418-da80a30aa9c1"
LIVE_PROG = "cb1d36f9-aa3c-412c-b551-b573387ae2e7"  # 建立渠道网络 owner=2
LIVE_SUB = "70043d60-63e6-4ef3-914c-b9d7a0383874"  # 影像成功 owner=3
LIVE_P_ANNE_PM = "946bbbab-f4d8-4632-a451-3a2c3290b546"
LIVE_P_876 = "0ac4a043-a636-4e91-bc8e-6c1fb72fcfb6"

OBJ_OWNER = "1315"  # 快速增长
SUB_OWNER = "3425"  # ge_smoke_sub
PROG_OWNER = "3429"  # ge_smoke_prog
PM = "3433"  # ge_smoke_pm
MEM = "3437"  # ge_smoke_mem
REV = "3441"  # simulated reviewer via header only


def _service_token() -> str:
    env = os.environ.get("GOAL_EXECUTION_SERVICE_TOKEN")
    if env:
        return env.strip()
    text = SKSTUDIO_ENV.read_text()
    m = re.search(r"GOAL_EXECUTION_SERVICE_TOKEN=(.+)", text)
    if not m:
        raise SystemExit("GOAL_EXECUTION_SERVICE_TOKEN not found")
    return m.group(1).strip().strip('"').strip("'")


TOK = _service_token()
RESULTS: list[tuple[bool, str, str]] = []
CLEANUP_PROJECTS: list[str] = []
CLEANUP_PROGRAM: str | None = None
CLEANUP_OBJECTIVE: str | None = None
CLEANUP_YEAR: str | None = None


def call(
    method: str,
    path: str,
    actor: str,
    *,
    reviewer: bool = False,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    req = request.Request(
        GE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOK}",
            "X-Actor-User-Id": str(actor),
            "X-Actor-Is-Reviewer": "1" if reviewer else "0",
            "Content-Type": "application/json",
        },
    )
    try:
        with request.urlopen(req) as resp:
            raw = resp.read().decode()
            payload: Any = json.loads(raw) if raw else None
            return resp.status, payload
    except error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else None
        except Exception:
            payload = {"raw": raw[:300]}
        return exc.code, payload


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((bool(cond), name, detail))
    print(("PASS" if cond else "FAIL"), "-", name, (f":: {detail}" if detail else ""))


def expect(
    name: str,
    method: str,
    path: str,
    actor: str,
    want: set[int],
    *,
    reviewer: bool = False,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    code, payload = call(method, path, actor, reviewer=reviewer, body=body)
    ok = code in want
    detail = f"got {code} want {sorted(want)}"
    if not ok:
        detail += f" body={json.dumps(payload, ensure_ascii=False)[:180]}"
    check(name, ok, detail)
    return code, payload


def create_project(actor: str, program_id: str, name: str, *, reviewer: bool = False, pm: str = PM) -> str | None:
    code, payload = call(
        "POST",
        "/projects",
        actor,
        reviewer=reviewer,
        body={
            "name": name,
            "program_id": program_id,
            "pm_user_id": pm,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    if code == 201 and isinstance(payload, dict) and payload.get("id"):
        pid = str(payload["id"])
        CLEANUP_PROJECTS.append(pid)
        return pid
    return None


def make_non_empty(project_id: str, actor: str, *, reviewer: bool = False) -> str | None:
    """Add a non-system task so project_is_empty is False."""
    code, graph = call("GET", f"/projects/{project_id}/graph", actor, reviewer=reviewer)
    if code != 200 or not isinstance(graph, dict):
        return None
    phases = graph.get("phases") or []
    phase_id = next((p["id"] for p in phases if not p.get("is_system")), None)
    if not phase_id:
        return None
    code, _payload = call(
        "POST",
        f"/projects/{project_id}/phases/{phase_id}/tasks",
        actor,
        reviewer=reviewer,
        body={"title": "smoke-task", "assignee_user_id": PM},
    )
    return phase_id if code in (200, 201) else None


def cleanup() -> None:
    print("\n===== CLEANUP =====")
    for pid in list(CLEANUP_PROJECTS):
        code, payload = call("DELETE", f"/projects/{pid}", "2", reviewer=True)
        print("delete project", pid[:8], code)
    if CLEANUP_PROGRAM:
        code, payload = call("DELETE", f"/programs/{CLEANUP_PROGRAM}", "2", reviewer=True)
        print("delete program", code, payload)
    if CLEANUP_OBJECTIVE:
        code, payload = call("DELETE", f"/objectives/{CLEANUP_OBJECTIVE}", "2", reviewer=True)
        print("delete objective", code, payload)
    if CLEANUP_YEAR:
        code, payload = call("DELETE", f"/objectives/{CLEANUP_YEAR}", "2", reviewer=True)
        print("delete year", code, payload)


def main() -> int:
    global CLEANUP_PROGRAM, CLEANUP_OBJECTIVE, CLEANUP_YEAR
    print("===== SETUP =====")
    code, obj = call(
        "POST",
        "/objectives",
        "2",
        reviewer=True,
        body={
            "name": f"GE权限冒烟子目标-{uuid.uuid4().hex[:6]}",
            "parent_id": PARENT_COMPANY,
            "owner_user_id": SUB_OWNER,
            "level": "sub",
            "period_granularity": "year",
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "lifecycle_status": "active",
            "primary_department_id": DEPT,
        },
    )
    check("setup create sub-objective", code == 201, f"{code} {obj}")
    if code != 201:
        return 1
    sub_id = str(obj["id"])
    CLEANUP_OBJECTIVE = sub_id

    code, prog = call(
        "POST",
        "/programs",
        "2",
        reviewer=True,
        body={
            "name": f"GE权限冒烟专项-{uuid.uuid4().hex[:6]}",
            "objective_id": sub_id,
            "owner_user_id": PROG_OWNER,
            "period_granularity": "quarter",
            "period_start": "2027-01-01",
            "period_end": "2027-03-31",
            "lifecycle_status": "active",
            "primary_department_id": DEPT,
        },
    )
    check("setup create program", code == 201, f"{code} {prog}")
    if code != 201:
        cleanup()
        return 1
    prog_id = str(prog["id"])
    CLEANUP_PROGRAM = prog_id

    proj_id = create_project("2", prog_id, "GE权限冒烟项目", reviewer=True)
    check("setup create project", bool(proj_id), str(proj_id))
    assert proj_id

    code, roles = call("GET", "/project-role-options", "2", reviewer=True)
    role_opts = (roles or {}).get("role_options") or []
    member_role = next((r for r in role_opts if r.get("slug") == "member"), None)
    if member_role is None and role_opts:
        member_role = next((r for r in role_opts if r.get("slug") != "project_manager"), role_opts[0])
    check("setup role-options", member_role is not None, str(roles)[:200])
    role_id = str((member_role or {}).get("id") or "")

    code, mem = call(
        "POST",
        f"/projects/{proj_id}/members",
        PM,
        body={"user_id": MEM, "role_option_id": role_id},
    )
    check("setup add member as PM", code == 201, f"{code} {mem}")

    phase_id = make_non_empty(proj_id, PM)
    check("setup make non-empty (task)", bool(phase_id), f"phase={phase_id}")

    print("\n===== MATRIX =====")

    # Reviewer
    expect("rev GET project", "GET", f"/projects/{proj_id}", REV, {200}, reviewer=True)
    expect("rev PATCH project", "PATCH", f"/projects/{proj_id}", REV, {200}, reviewer=True, body={"name": "GE权限冒烟项目"})
    rid = create_project(REV, prog_id, f"rev-{uuid.uuid4().hex[:6]}", reviewer=True)
    check("rev create project", bool(rid))
    code, year = call(
        "POST",
        "/objectives/years",
        REV,
        reviewer=True,
        body={"planning_year": 2099, "name": f"冒烟年-{uuid.uuid4().hex[:4]}"},
    )
    if code == 201 and isinstance(year, dict) and year.get("id"):
        CLEANUP_YEAR = str(year["id"])
    check("rev can POST years", code == 201, f"{code} {year}")
    expect("non-rev years DENIED", "POST", "/objectives/years", OBJ_OWNER, {403}, body={"planning_year": 2098, "name": "x"})

    # Company / objective owner (ancestor governor)
    expect("objOwner GET", "GET", f"/projects/{proj_id}", OBJ_OWNER, {200})
    oid = create_project(OBJ_OWNER, prog_id, f"obj-{uuid.uuid4().hex[:6]}")
    check("objOwner create project", bool(oid))
    expect("objOwner PATCH", "PATCH", f"/projects/{proj_id}", OBJ_OWNER, {200}, body={"name": "GE权限冒烟项目"})
    if phase_id:
        code, payload = call(
            "POST",
            f"/projects/{proj_id}/phases/{phase_id}/tasks",
            OBJ_OWNER,
            body={"title": "gov-task", "assignee_user_id": PM},
        )
        check("objOwner canvas not forbidden", code != 403, f"{code} {payload}")

    # Sub owner
    expect("subOwner GET", "GET", f"/projects/{proj_id}", SUB_OWNER, {200})
    sid = create_project(SUB_OWNER, prog_id, f"sub-{uuid.uuid4().hex[:6]}")
    check("subOwner create project", bool(sid))
    expect("subOwner PATCH program", "PATCH", f"/programs/{prog_id}", SUB_OWNER, {200}, body={"name": prog.get("name")})
    expect("subOwner assess DENIED", "POST", f"/programs/{prog_id}/assess", SUB_OWNER, {403}, body={})
    expect(
        "subOwner cannot create on LIVE prog",
        "POST",
        "/projects",
        SUB_OWNER,
        {403},
        body={
            "name": "fail",
            "program_id": LIVE_PROG,
            "pm_user_id": PM,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )

    # Program owner
    expect("progOwner GET", "GET", f"/projects/{proj_id}", PROG_OWNER, {200})
    pid2 = create_project(PROG_OWNER, prog_id, f"prog-{uuid.uuid4().hex[:6]}")
    check("progOwner create project", bool(pid2))
    expect("progOwner PATCH project", "PATCH", f"/projects/{proj_id}", PROG_OWNER, {200}, body={"name": "GE权限冒烟项目"})
    expect(
        "progOwner cannot create sub-objective",
        "POST",
        "/objectives",
        PROG_OWNER,
        {403},
        body={
            "name": "fail-obj",
            "parent_id": PARENT_COMPANY,
            "owner_user_id": PROG_OWNER,
            "level": "sub",
            "period_granularity": "year",
            "period_start": "2027-01-01",
            "period_end": "2027-12-31",
            "lifecycle_status": "active",
            "primary_department_id": DEPT,
        },
    )
    expect("progOwner people-summary", "GET", f"/programs/{prog_id}/people-summary", PROG_OWNER, {200})
    expect("pm people-summary program DENIED", "GET", f"/programs/{prog_id}/people-summary", PM, {403})

    # PM
    expect("pm GET", "GET", f"/projects/{proj_id}", PM, {200})
    expect("pm PATCH", "PATCH", f"/projects/{proj_id}", PM, {200}, body={"name": "GE权限冒烟项目"})
    expect(
        "pm create DENIED",
        "POST",
        "/projects",
        PM,
        {403},
        body={
            "name": "pm-fail",
            "program_id": prog_id,
            "pm_user_id": PM,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    if phase_id:
        code, payload = call(
            "POST",
            f"/projects/{proj_id}/phases/{phase_id}/tasks",
            PM,
            body={"title": "pm-task-2", "assignee_user_id": PM},
        )
        check("pm canvas not forbidden", code != 403, f"{code} {payload}")
    expect("pm people-summary project", "GET", f"/projects/{proj_id}/people-summary", PM, {200})
    # empty project: PM may delete; non-empty: PM 409
    empty_id = create_project(PROG_OWNER, prog_id, f"empty-{uuid.uuid4().hex[:6]}")
    if empty_id:
        expect("pm DELETE empty OK", "DELETE", f"/projects/{empty_id}", PM, {200, 204})
        if empty_id in CLEANUP_PROJECTS:
            CLEANUP_PROJECTS.remove(empty_id)
    expect("pm DELETE non-empty DENIED", "DELETE", f"/projects/{proj_id}", PM, {409})
    # governor force delete a disposable non-empty child
    doomed = create_project(PROG_OWNER, prog_id, f"doom-{uuid.uuid4().hex[:6]}")
    if doomed:
        make_non_empty(doomed, PM)
        expect("progOwner force DELETE non-empty", "DELETE", f"/projects/{doomed}", PROG_OWNER, {200, 204})
        if doomed in CLEANUP_PROJECTS:
            CLEANUP_PROJECTS.remove(doomed)

    # Member
    expect("mem GET", "GET", f"/projects/{proj_id}", MEM, {200})
    expect("mem GET graph", "GET", f"/projects/{proj_id}/graph", MEM, {200})
    expect("mem PATCH DENIED", "PATCH", f"/projects/{proj_id}", MEM, {403}, body={"name": "hijack"})
    expect(
        "mem create DENIED",
        "POST",
        "/projects",
        MEM,
        {403},
        body={
            "name": "mem-fail",
            "program_id": prog_id,
            "pm_user_id": PM,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    if phase_id:
        expect(
            "mem canvas DENIED",
            "POST",
            f"/projects/{proj_id}/phases/{phase_id}/tasks",
            MEM,
            {403},
            body={"title": "x", "assignee_user_id": MEM},
        )
    expect(
        "mem add member DENIED",
        "POST",
        f"/projects/{proj_id}/members",
        MEM,
        {403},
        body={"user_id": "1", "role_option_id": role_id},
    )
    code, prog_body = call("GET", f"/programs/{prog_id}", MEM)
    ids = {p.get("id") for p in (prog_body or {}).get("projects") or []}
    check("mem sees own project in program.projects", proj_id in ids, str(ids))
    code, prog_rev = call("GET", f"/programs/{prog_id}", REV, reviewer=True)
    ids_r = {p.get("id") for p in (prog_rev or {}).get("projects") or []}
    check("rev sees >=2 projects in program", len(ids_r) >= 2, str(ids_r))

    # Outsider
    expect("outsider GET DENIED", "GET", f"/projects/{proj_id}", "999999", {403, 404})

    # Live tree regression
    expect("anne GET 876", "GET", f"/projects/{LIVE_P_876}", "1", {200})
    expect("anne PATCH 876 DENIED", "PATCH", f"/projects/{LIVE_P_876}", "1", {403}, body={"name": "测试项目876"})
    expect("anne GET own PM project", "GET", f"/projects/{LIVE_P_ANNE_PM}", "1", {200})
    expect("anne PATCH own PM project", "PATCH", f"/projects/{LIVE_P_ANNE_PM}", "1", {200}, body={"name": "发展民营渠道2"})
    expect(
        "anne create under live DENIED",
        "POST",
        "/projects",
        "1",
        {403},
        body={
            "name": "anne-fail",
            "program_id": LIVE_PROG,
            "pm_user_id": "1",
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    vic = create_project("2", LIVE_PROG, f"vic-{uuid.uuid4().hex[:6]}", pm="2")
    check("victor(no rev bit) create under live prog", bool(vic))
    sub3 = create_project("3", LIVE_PROG, f"sub3-{uuid.uuid4().hex[:6]}", pm="2")
    check("影像成功 owner create under live prog", bool(sub3))
    expect(
        "smoke-sub owner cannot create under live",
        "POST",
        "/projects",
        SUB_OWNER,
        {403},
        body={
            "name": "cross-fail",
            "program_id": LIVE_PROG,
            "pm_user_id": PM,
            "phases": [{"sequence": 1, "name": "方案", "gate_items": [], "tasks": []}],
        },
    )
    # ancestor of live: company owner 1315 can create under live prog
    live_anc = create_project(OBJ_OWNER, LIVE_PROG, f"anc-{uuid.uuid4().hex[:6]}", pm="2")
    check("company owner create under live prog", bool(live_anc))

    cleanup()

    print("\n===== SUMMARY =====")
    failed = [r for r in RESULTS if not r[0]]
    print(f"passed {len(RESULTS) - len(failed)}/{len(RESULTS)}")
    for _, name, detail in failed:
        print("FAIL", name, "::", detail)
    report = {
        "passed": len(RESULTS) - len(failed),
        "total": len(RESULTS),
        "failed": [{"name": n, "detail": d} for _, n, d in failed],
        "all": [{"ok": ok, "name": n, "detail": d} for ok, n, d in RESULTS],
    }
    Path("/tmp/ge_authz_smoke_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("report: /tmp/ge_authz_smoke_report.json")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        cleanup()
        raise
