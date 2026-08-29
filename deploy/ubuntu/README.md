# goal_execution — Ubuntu 部署

与 skstudio / knowledge_base 同机配套。浏览器经 skstudio **`/api/v1/ge/`** 到达本服务 `:8092`（**不要**把 Nginx 直接指到 8092；**无** `/ge-api`；skstudio **不再** mint GE 用户 JWT）。探活：`GET /api/v1/ge/health`。

**生产总入口**：[platform-docs/migration/production_deploy.md](https://github.com/pumpkinale999/platform-docs/blob/main/migration/production_deploy.md)。

## 前置

- Ubuntu + systemd + Python ≥3.11
- **Postgres** 库 `goal_execution` 已创建；进程可连
- 代码在 **`/opt/goal_execution`**（或 `APP_ROOT`）
- skstudio 将提供对齐的 `GOAL_EXECUTION_SERVICE_TOKEN` / JWT secret

## 首次上架

```bash
cd /opt/goal_execution
sudo ./deploy/ubuntu/ge-deploy.sh bootstrap
sudo vi /etc/goal-execution/goal-execution.env   # 必填 DATABASE_URL + REQUIRE_POSTGRES=1
sudo ./deploy/ubuntu/ge-deploy.sh configure     # 从 skstudio.env 同步 token / JWT
sudo ./deploy/ubuntu/ge-deploy.sh deploy        # pip + ensure_dev_schema + systemd
```

`goal-execution.env` 须设置（见 `goal-execution.env.example`）：

| 键 | 说明 |
|----|------|
| `DATABASE_URL` | `postgresql+psycopg://…/goal_execution` |
| `REQUIRE_POSTGRES` | `1` |
| `GOAL_EXECUTION_JWT_SECRET` | 与 skstudio `JWT_SECRET` 同值 |
| `GOAL_EXECUTION_SERVICE_TOKEN` | 与 skstudio 同值 |

**勿再配置** `GOAL_EXECUTION_DB_PATH`。组织 API **不在本服务**（权威在 skstudio `/api/v1/org`）。

## Schema

`deploy` 调用 `scripts/ensure_dev_schema.py`：

- **空库**（无 `alembic_version`）：ORM `create_all` + `alembic stamp head`
- **已在 head**：no-op
- **落后 head**：**拒绝 stamp**（exit 1），须先 `alembic upgrade head`

生产经 `up-prod.sh` 发版时 **默认**跑 `alembic upgrade head`（`GE_ALEMBIC_UPGRADE` 默认 `1`；设 `0` 跳过）。upgrade 后应断言 `org_departments` / `org_teams` / `user_org_*` **不存在**。

**禁止**用 stamp 把版本号「假前进」到含 DROP 的 revision 却不执行 DDL。

## 日常升级

```bash
cd /opt/goal_execution && git pull   # 或经 publish 工作流
sudo ./deploy/ubuntu/ge-deploy.sh deploy
sudo ./deploy/ubuntu/ge-deploy.sh health
```

## 文件

| 文件 | 用途 |
|------|------|
| `ge-deploy.sh` | bootstrap / configure / deploy / health |
| `goal-execution.env.example` | `/etc/goal-execution/goal-execution.env` |
| `goal-execution.service.in` | systemd 模板 |
