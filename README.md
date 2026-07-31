# goal_execution

项目治理服务（目标与执行）— 独立进程 **:8092**。规格见 [platform-docs](https://github.com/pumpkinale999/platform-docs)《目标与执行及其组织支撑》。

**组织权威在 skstudio**（`/api/v1/org` · `org_local`）。本仓不再挂载 `/api/v1/org/*`；`app/routes_org.py` 仅作历史/导入参考。

## Architecture

```text
skstudio UI (JWT)     ──► /api/v1/org（skstudio）· /ge-api/ge/*（经 BFF → 本服务）
skstudio BFF          ──► goal_execution REST（service token + X-Actor-User-Id）
                              │
                              ▼
                    Postgres DB `goal_execution`（DATABASE_URL）
```

运行时 **Postgres only**（`REQUIRE_POSTGRES=1`）。鉴权：仅 service token（拒用户 JWT · AUTH-BFF-01）。

## Mac / Linux 开发

| 依赖 | macOS | Linux (Ubuntu) |
| ---- | ----- | -------------- |
| Python ≥3.11 | `brew install python@3.11` | `apt install python3.11 python3.11-venv` |
| PostgreSQL 16 | `brew install postgresql@16` | 见 platform-docs §2.7 |

```bash
./scripts/dev-goal-execution.sh
./scripts/dev-goal-execution.sh --check-only
```

schema：`scripts/ensure_dev_schema.py`（create_all + alembic stamp；勿对空库盲跑历史 Alembic）。

生产：`deploy/ubuntu/ge-deploy.sh` + `goal-execution.env.example`（须填 `DATABASE_URL`）。
