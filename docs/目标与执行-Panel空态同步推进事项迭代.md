# 目标与执行 · Panel 空态 · 同步推进事项迭代

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源 · **现网**）
- **版本**：**v0.1.0**（2026-08-26）
- **里程碑**：**PS-PANEL-SYNC**（PS-MS1～MS4）
- **状态**：**现网**
- **适用对象**：产品、skstudio / goal_execution / active_agent 研发、QA

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | **§4.9.10** |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) | **§10.50 · §10.51** |
| [目标与执行-Panel空态同步推进事项评价.md](./目标与执行-Panel空态同步推进事项评价.md) | 文档闸 + 实现闸 |
| [PRA产品设计.md](./PRA产品设计.md) | **§4.9.4** Panel 空态摘要 |
| [openapi/ge-v1.yaml](./openapi/ge-v1.yaml) | **1.32.0** |

> **一句话**：进展表有内容但 SDA 空 → 治理者在 Panel 点 **主动同步推进事项** → GE heal + AA rescan → 推进票出现。

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| C1 | 空态紧挨「项目进展」表下方 · `execution-detail-meta` · **非** 列表 footer |
| C2 | 治理者文案 + 内联按钮 **`主动同步推进事项`** · testid `execution-sda-sync-execution-state` |
| C3 | 参与者纯文案 · **无** 按钮 |
| C4 | 显隐：`sda/events` **原始空** · 非 loading/error · 项目 Panel（非 define） |
| C5 | GE `POST …/recompute-phases` 与 GET graph **共用** `heal_active_project_graph_state` |
| C6 | BFF `POST …/sync-execution-state` 编排：heal → sense_scan → decide_queue |
| C7 | 显式同步 **不** 走 GE outbox · **不** 写 `planned_*` |

---

## PS-MS1 · GE 图自愈收口（goal_execution）

### 实现

| 交付 | 路径 |
| ---- | ---- |
| `HealSummary` + `heal_active_project_graph_state` | `goal_execution/app/services/ge_graph.py` |
| GET graph 重构为共用 heal | `goal_execution/app/routes_ge.py` |
| `POST /api/v1/ge/projects/{id}/recompute-phases` | 同上 · `require_govern_project` · AuditEvent `recompute_phases` |

### 测试

| ID | 状态 |
| ---- | ---- |
| **GE-T212** | ☑ `tests/ge/test_stuck_phase_heal.py` |
| **GE-T215** | ☑ 同上（治理者 200 · 参与者 403） |
| GE-T213/T214 回归 | ☑ |

### DoD

- [x] GE-T215 绿
- [x] OpenAPI **1.32.0** runtime
- [x] §10.51 #1–2 ☑

---

## PS-MS2 · BFF 编排（skstudio backend）

### 实现

| 交付 | 路径 |
| ---- | ---- |
| `POST /api/v1/ge/projects/{id}/sync-execution-state` | `skstudio/backend/app/api/routes_ge_bff.py` |

### 测试

| ID | 状态 |
| ---- | ---- |
| **BFF-PS-T01** | ☑ 三步编排顺序 |
| **BFF-PS-T02** | ☑ GE 403 不调 AA |

### DoD

- [x] BFF-PS-T01/T02 绿
- [x] §10.51 #3 ☑

---

## PS-MS3 · Panel 空态 UI（skstudio frontend）

### 实现

| 交付 | 路径 |
| ---- | ---- |
| `SdaPanelEmptyState` | `frontend/src/execution/components/SdaPanelEmptyState.tsx` |
| `SdaEventStream` 空态分支 | `frontend/src/execution/components/SdaEventStream.tsx` |
| `syncExecutionState` | `frontend/src/execution/api/client.ts` |
| `canGovernProject={graphEditable}` | `frontend/src/execution/pages/ProjectCanvasPage.tsx` |

### 测试

| ID | 状态 |
| ---- | ---- |
| **PANEL-UI-T01** | ☑ vitest |
| **PANEL-UI-T02** | ☑ vitest |
| **PANEL-UI-T03** | ☑ vitest（syncing 禁用） |

### DoD

- [x] PANEL-UI-T01～T03 绿
- [x] §10.51 #4 ☑

---

## PS-MS4 · Chrome 冒烟与文档收口

### 实现

| 交付 | 路径 |
| ---- | ---- |
| Playwright E2E | `frontend/e2e/execution/panel-empty-sync.spec.ts` |

### 测试

| ID | 状态 |
| ---- | ---- |
| **PS-E2E-1** | ☑ 空 SDA + 同步按钮 |
| **PS-E2E-2** | ☑ 点同步 → SDA 卡出现 |
| **PS-E2E-3** | ☑ 参与者无按钮 |

**Chromium 冒烟（2026-08-26）**：`npx playwright test e2e/execution/panel-empty-sync.spec.ts --project=chromium` — **3/3 通过**。

### 全栈手工清单（Follow-up · 生产）

| 步骤 | 预期 |
| ---- | ---- |
| PM 打开 CTA `c670751f-f642-4d12-a7f6-9e78ad741099` | 进展表有完成行 · SDA 空 · 见同步按钮 |
| 点 **主动同步推进事项** | ≤90s 内出现 `deliver_gate` 类 SDA 卡 |
| 参与者账号 | 纯文案 · 无按钮 |

### DoD

- [x] PS-E2E-1～3 绿
- [x] 评价文档升 **v0.2.0 实现闸**
- [ ] 生产 CTA 项目手工冒烟（待发版后）

---

## 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-26 | **v0.1.0** | PS-MS1～MS4 齐 · 现网 |
