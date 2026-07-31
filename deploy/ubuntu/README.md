# goal_execution — Ubuntu 部署

与 skstudio / knowledge_base 同机配套。Nginx **`/ge-api/`** 反代到 **skstudio**（再 BFF → 本服务 `:8092`），**不要**把 `/ge-api` 直接指到 8092。

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

`deploy` 调用 `scripts/ensure_dev_schema.py`（ORM create_all + alembic stamp）。  
**禁止**对空 Postgres 执行历史 `alembic upgrade head`。

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
