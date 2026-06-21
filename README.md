# goal_execution

Project governance service (organization + goal & execution) — independent repo/process per [目标与执行及其组织支撑(实现与测试)](https://github.com/pumpkinale999/skstudio/blob/main/docs/目标与执行及其组织支撑(实现%20与测试).md) **v1.1.4**.

**M1（当前）**: repo 脚手架 · `GET /api/v1/health` · Alembic 布局 · JWT/service 鉴权骨架 · OpenAPI 镜像。

**M1 目标（规格 §1.6）**: P0 org 表 + BFF 联调 · P0b 默认目标链 · P1 执行链（见 skstudio 姊妹文档 Milestone M1–M7）。

skstudio UI、BFF、WS 扇出与 Playwright E2E 在 **skstudio** 仓库（`frontend/e2e/execution/`）。

## Architecture

```text
skstudio UI (JWT)     ──► goal_execution REST (participant ge + org public read)
skstudio BFF          ──► goal_execution REST (governance · service token + X-Actor-User-Id)
                              │
                              ▼
                    {data_root}/goal-execution/ge.db
```

## Mac / Linux 开发

| 依赖 | macOS | Linux (Ubuntu) |
| ---- | ----- | -------------- |
| Python ≥3.11 | `brew install python@3.11` | `apt install python3.11 python3.11-venv` |

**一键开发**（默认 `~/.hermes/goal-execution/`；自动 venv、`.env`）：

```bash
./scripts/dev-goal-execution.sh
./scripts/dev-goal-execution.sh --check-only
```

**与 skstudio 四联调**：见 [skstudio `开发和部署.md` §2.5](https://github.com/pumpkinale999/skstudio/blob/main/docs/开发和部署.md)。

## Spec links

| 文档 | 说明 |
| --- | --- |
| [需求 v2.1.3](https://github.com/pumpkinale999/skstudio/blob/main/docs/目标与执行及其组织支撑(需求).md) | ER · UI · 产品决策 |
| [实现与测试 v1.1.4](https://github.com/pumpkinale999/skstudio/blob/main/docs/目标与执行及其组织支撑(实现与测试).md) | DDL · API · Milestone · DoD |
| `openapi/ge-v1.yaml` | P1 OpenAPI 真源（skstudio `docs/openapi/` 镜像） |
