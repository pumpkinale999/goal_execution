# 目标与执行 · GE 组织遗留维护（ORG-DEPT-GE-MAINT）

- **文档类型**：产品共识 + 实现/测试规格（本迭代真源）
- **版本**：**v1.0.0**（2026-08-29）
- **里程碑**：**ORG-DEPT-GE-MAINT**
- **状态**：**代码就绪（MS1–MS4）· 待合码 / tag / 生产发版**
- **适用对象**：产品、skstudio / goal_execution 研发、QA、运维
- **代码范围**：`goal_execution` · `skstudio` · `platform-docs`
- **上位现网**：写路径 `v29.01.02` · 读路径 `v29.01.03`

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [平台控制面与Postgres迁移共识.md](../../platform_docs/平台控制面与Postgres迁移共识.md) | D2 / M3 |
| [目标与执行-组织组合读路径去GE本库依赖迭代.md](./目标与执行-组织组合读路径去GE本库依赖迭代.md) | F1/F2 现网后遗留 |
| [目标与执行-GE组织遗留维护评价.md](./目标与执行-GE组织遗留维护评价.md) | 四闸评价 |

> **一句话**：上报链 callback 展开 · GE 死 org 清仓 · stamp 硬拒 · 组织详情「目标」tab — 本地测绿，待成对发版。

---

## 0. 共识冻结清单

（C1–C13 同 v0.1.0。）

---

## 3. 实现切片与 DoD

| 切片 | 状态 |
| ---- | ---- |
| **MS0** 文档 | ✅ |
| **MS1 · REPORT-CHAIN** | ✅ GE 仅 assignee；`deviation_report_chain`；GE-T260 / SK-T260～262 |
| **MS2 · PURGE** | ✅ 删 `models/org` 等；CI `check_no_ge_org_imports`；GE-T270 |
| **MS3 · STAMP** | ✅ `ensure_dev_schema` refuse；`up-prod` 默认 upgrade；GE-T280 |
| **MS4 · UI-PORTFOLIO** | ✅ 部门/团队/人员「目标」tab；UI-T280（tabs 测） |
| **MS5** 现网收口 | ⏳ 待合码 · tag（建议 `v29.01.04`）· 先 GE 后 skstudio · 冒烟 |

### 3.1 关键路径摘要

| 能力 | 路径 |
| ---- | ---- |
| 上报链展开 | `skstudio/.../deviation_report_chain.py` + `routes_ge_ws.ge_deviation_notify` |
| GE 收件人 | `ge_deviations.notification_recipients` |
| CI ban | `goal_execution/scripts/check_no_ge_org_imports.py` |
| stamp | `goal_execution/scripts/ensure_dev_schema.py` |
| UI | `meOrgNodeDetailTabs` · `MeOrgNodeDetail` · `MeOrgPersonDetailPage` |

### 3.2 发版签收清单（MS5）

| 项 | 动作 |
| -- | ---- |
| Tag | 建议 `v29.01.04`（双仓同日） |
| 顺序 | 先 GE，后 skstudio |
| 冒烟 | 激活偏差 → assignee+上级 PA；部门详情「目标」tab；upgrade 后 org 表不存在 |
| 评价 | 生产闸闭后升 **Accepted · 现网** |

---

## 6. 修订记录

| 日期 | 版本 | 说明 |
| ---- | ---- | ---- |
| 2026-08-29 | **v1.0.0** | MS1–MS4 代码就绪；MS5 待发版 |
| 2026-08-29 | **v0.2.0** | MS1 |
| 2026-08-29 | **v0.1.0** | 共识冻结 |
