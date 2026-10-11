# PRA · 目标看板 work_state 物化缓存迭代

- **文档类型**：产品共识 + 实现/测试规格（本迭代真源）
- **版本**：**v1.0.0**（2026-08-27 · BOARD-MS1）
- **里程碑**：**PRA-BOARD-CACHE**（方案 A · 单点写）
- **状态**：**Accepted**（代码已合 active_agent；待发版）
- **适用对象**：产品、active_agent / skstudio BFF / QA
- **代码范围**：`active_agent`（**本波不改** goal_execution / skstudio FE；BFF 超时另开）
- **发版 tag**：`v29.00.44`（active_agent · platform-docs）

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [PRA产品设计.md](./PRA产品设计.md) | **§4.10.2 / §4.10.4**（延迟桶 + AA 读缓存） |
| [PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) | **§4.4** 看板延迟桶同源；**A3** 只读 `project_work_state` |
| [PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) | **§4.6 R8** 读路径禁止跑满 Sense+Decide |
| [PRA-实现与测试.md](./PRA-实现与测试.md) | **§4.10** 验收表 B10+ |
| [PRA-项目办事态机迭代.md](./PRA-项目办事态机迭代.md) | **WS-T07** 看板半截无票进延迟桶 |
| Release | [migration/release-v29.00.44.md](./migration/release-v29.00.44.md) |

> **一句话**：看板打「延迟」桶不再 per-project 拉 GE sense graph；`project_work_state` 在 **`scan_project` 唯一写入** 物化表，看板批量读 `in_delay`。

---

## 0. 背景与方案

| 现象 | 根因 |
| ---- | ---- |
| 公司目标看板「看板加载失败」 | AA `build_*_board` 对每可见项目 `load_scan_bundle` → N 次 `GET …/graph?view=sense`；57 项目 ~15s，skstudio BFF **10s** 超时 |
| 子目标/专项看板长时间「加载中…」 | 同上，项目数较少时勉强过线 |

**方案 A（Accepted）**：物化 `project_work_state_cache`；看板读缓存。**禁止**在读路径多点写缓存或回退 per-project 现算（冷启动见 §0.3）。

### 0.1 架构（Normative）

```text
写路径（唯一写入点）
  GE observation / cron sense_scan / SDA 写后 _rescan_project
    → revalidate_project
    → scan_project
    → reconcile_project
    → refresh_project_work_state_cache   ← 仅此函数写表

读路径
  GET …/programs/{id}/board
  GET …/objectives/{id}/board
    → GE board-projects / program.projects（1 次）
    → AA 开放 Action 意图（1 次 SQL）
    → project_ids_in_delay_work（1 次 SQL，读 project_work_state_cache）
```

### 0.2 共识冻结

| # | 共识 |
| - | ---- |
| C1 | **写**：仅 `refresh_project_work_state_cache`，且**只**由 `scan_project` 在 `reconcile_project` 之后调用 |
| C2 | **读**：`project_ids_in_delay_work` 批量查 `in_delay=true`；**禁止**看板路径 `load_scan_bundle` |
| C3 | **延迟桶语义**与 [办事态机共识 §4.4](./PRA-项目办事态机共识.md)：开放 remediate 票 **或** `work_state ∈ DELAY_*`（经缓存 `in_delay`） |
| C4 | 有开放定义 → **只进定义**；与 §3.3.0 L1 一致 |
| C5 | 表由 `create_all` + `migrate_m5_schema` 增量建；Postgres 真源 |
| C6 | **本波不改** skstudio BFF 10s 超时（Follow-up）；发版后须跑 `sense_scan` 预热 |

### 0.3 冷启动与一致性（Normative）

| 场景 | 行为 |
| ---- | ---- |
| 部署后首次打开看板、项目从未被 scan | 缓存无行 → **不算** `in_delay_work`；有开放 remediate 票仍进延迟桶 |
| cron `sense_scan` 或任意写路径触发 `revalidate` | 缓存更新；看板 refetch 后桶正确 |
| 缓存与 live 图短暂不一致 | **可接受**（eventual consistency）；真源以下次 scan 为准 |

**发版后**：执行至少一轮 `sense_scan`（或等待 cron 1h）再验收公司级大看板。

---

## BOARD-MS1 · 实现

### 数据表

`project_work_state_cache`（PK `project_id`）

| 列 | 说明 |
| -- | ---- |
| `work_state` | `NEEDS_DEFINITION` / `DELAY_*` / `EXECUTING` / `TERMINAL` |
| `in_delay` | `work_state ∈ {DELAY_NEEDS_REMEDIATE, DELAY_NEEDS_REPORT}` |
| `computed_at` | UTC |
| `source` | 末次写入来源（`cron` / `write` / `scan:*` 等） |

### 代码触点

| 交付 | 路径 |
| ---- | ---- |
| ORM | `app/models/orm.py` · `ProjectWorkStateCache` |
| 写/读服务 | `app/services/work_state_cache.py` |
| 唯一写调用 | `app/services/sense.py` · `scan_project`（reconcile 后） |
| 看板读 | `app/services/program_board.py` · `objective_board.py` → `_ids_in_delay_work(db, …)` |
| Postgres 迁移 | `scripts/migrate_m5_schema.py` |

### 测试

| ID | 断言 | 落点 |
| -- | ---- | ---- |
| **BC-T01** | refresh + 批量 `in_delay` 读 | `tests/test_work_state_cache.py` |
| **BC-T02** | upsert 覆盖 `source` / `EXECUTING` | 同上 |
| **WS-T07** | 半截无票 scan 后看板进 **延迟** | `tests/test_pra_ws1_ms3.py`（先 scan 再 board） |
| B1–B5 | 打桶互斥不变 | `tests/test_program_board.py` |

### DoD

- [x] 表 + migrate + 单点写 + 看板读缓存
- [x] BC-T01/T02 · WS-T07 · B1–B5 绿
- [x] 产品 §4.10.2/4.10.4 · 实现 §4.10 · 本迭代文档 · release note 对齐
- [ ] **发版** active_agent `v29.00.44` + `migrate_m5_schema` + `sense_scan` 预热
- [ ] **冒烟** 公众公司目标看板 <10s、无 503（BFF 超时未调时以预热后为准）

---

## Follow-up（不挡本波）

| ID | 项 |
| -- | -- |
| **BC-F1** | skstudio BFF board 路径超时 30s（止血） |
| **BC-F2** | FE 看板 503 可重试 + 长加载文案 |
| **BC-F3** | 一次性 `revalidate` 全库 backfill 脚本（运维可选；内部仍只调 R1） |

---

## 修订记录

| 版本 | 日期 | 说明 |
| ---- | ---- | ---- |
| **v1.0.0** | 2026-08-27 | BOARD-MS1 Accepted；方案 A 单点写；文档与代码对齐 |
