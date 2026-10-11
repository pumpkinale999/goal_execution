# PRA · 项目办事态机迭代

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源）
- **版本**：**v0.2.1**（2026-08-21）
- **里程碑**：**PRA-WS1**（Work State）
- **状态**：**现网**（生产 AA 已发 · audit dry-run 半截无票=0 · 慢病锚点有去补救 Owner=1722）
- **共识真源**：[PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) **v0.3.0**（含 §4.6 写后重评）
- **续作**：[PRA-项目办事态机写后重评迭代.md](./PRA-项目办事态机写后重评迭代.md) **PRA-WS1.1** · [评价](./PRA-项目办事态机写后重评评价.md)
- **适用**：active_agent · platform-docs；**本切片不改** goal_execution / skstudio（除文档挂链）

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) | 问题/架构/办事态表/细则 **已拍板** |
| [PRA产品设计.md](./PRA产品设计.md) | §3.3.0 / §3.3.1；INV-3 例外挂链 |
| [PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md) | INV-3 **修订**（本迭代） |
| [PRA-实现与测试.md](./PRA-实现与测试.md) | DoD / 测追溯 |

> **一句话**：`project_work_state` 同源驱动 Sense / Decide / reconcile / 看板延迟 / healthy；半截保留「去补救」；stage 与 envelope 清票分轨；只发 AA。

---

## 0. 共识冻结（摘录 · v0.2.1）

实现不得偏离共识全文；要点：

- 五态枚举钉死；混态：定义 > 半截/逾期 > 报告链 > 执行中  
- **stage** INV-3 认办事态+热项；**envelope** 只认窗口  
- GE `is_overdue` 不动；Sense **合成热项** 开票；健康/看板同源  
- B3：报告 done 后仅 **再次半截** 才回「去补救」；有可达 rem-task 未 close 偏差 → EXECUTING  
- 发版：仅 AA；dry-run；无票≥20 分批 apply；扩 `pra_invariant_audit`  

---

## 1. 目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | 半截项目 scan/list 后 **必有** 开放 `remediate_stage`（L1 除外） |
| **G2** | INV-3 **不得** 仅因 `is_overdue=false` 杀 stage 票 |
| **G3** | 离开延迟态后仍可 cancel 陈旧 stage/envelope（分谓词） |
| **G4** | 单入口；Sense/Decide/reconcile/看板/healthy 同读 |
| **G5** | 生产 audit+限流 apply；慢病可验证 |

---

## 2. 实现切片

| MS | 交付 | 仓 | 状态 |
| -- | ---- | -- | ---- |
| **MS1 · 态机内核** | `app/packs/pra/project_work_state.py`；WS-T01 | active_agent | ✅ |
| **MS2 · reconcile** | INV-3 分轨；WS-T02/T03/T09 | active_agent | ✅ |
| **MS3 · Sense/Decide/看板/健康** | 合成热项；board/`project_is_healthy`；WS-T04～T07/T10 | active_agent | ✅ |
| **MS4 · 存量 + 发版准备** | 扩 `pra_invariant_audit`；`--limit`；WS-T08 | active_agent · docs | ✅ 代码；发版另开 |

**发布**：只发 `active_agent` + docs。**不要** `./up-prod.sh all`。

---

## 3. 测试追溯（Normative）

| ID | 断言 | 落点 |
| -- | ---- | ---- |
| **WS-T01** | 真值表 | `tests/test_project_work_state.py` ✅ |
| **WS-T02** | 半截不 cancel | `tests/test_reconcile_project.py` ✅ |
| **WS-T03** | 无热可 cancel | 同上 ✅ |
| **WS-T09** | envelope 分轨 | 同上 ✅ |
| **WS-T04** | L1 | `tests/test_pra_ws1_ms3.py` ✅ |
| **WS-T05** | scan 开票 Owner=PM | 同上 ✅ |
| **WS-T06** | 报告态 | 同上 ✅ |
| **WS-T07** | 看板延迟 | 同上 ✅ |
| **WS-T10** | healthy | 同上 ✅ |
| **WS-T08** | audit dry-run / limit | `tests/test_pra_invariant_audit_ws1.py` ✅ |

---

## 4. DoD

- [x] **MS1**：`project_work_state` + WS-T01 绿  
- [x] **MS2**：INV-3 修订 + WS-T02/T03/T09 绿  
- [x] **MS3**：Sense/Decide/看板/健康 + WS-T04～T07/T10 绿  
- [x] **MS4**：audit 扩半截无票 + `--limit` + WS-T08 绿  
- [x] 上位 [PRA-一致性合约](./PRA-一致性合约迭代.md) INV-3 办事态谓词  
- [x] 生产 dry-run（半截无票=0，跳过全库 apply）；慢病锚点冒烟；本文/共识标 **现网**  

---

## 5. Follow-up（不挡本迭代）

| ID | 项 |
| -- | -- |
| **WS-F1** | graph `needs_remediate_work` |
| **WS-F2** | 只 open 超时 / 报告后偏差未 close → inform PM |
| **WS-F3** | Panel 暴露 `work_state` → **WS1.1** [写后重评](./PRA-项目办事态机写后重评迭代.md) **RV-F2** |
| **WS-F4** | FE focus 半截 gate |
| **WS-F5** | 专用 Sense event_type（仅当合成热项可观测不够） |
| **WS-F6** | 写后统一 `revalidate_project` → **[PRA-WS1.1](./PRA-项目办事态机写后重评迭代.md)** |
| **WS-F7** | 看板读物化 `work_state` → **[PRA-BOARD-CACHE](./PRA-目标看板work_state缓存迭代.md)** **v1.0.0**（scan 单点写） |

---

## 6. 风险

| 风险 | 缓解 |
| ---- | ---- |
| 补票风暴 | dry-run；≥20 分批 |
| L1 下半截无票 | 预期；先清定义 |
| 旧测空 overdue 必杀 | 已改期望 |

---

## 7. 冒烟锚点（生产）

| 项 | 值 |
| -- | -- |
| 项目 | 慢病平台1.0 · `bc670909-a826-45ea-a724-3241df1102d4` |
| PM | `1722`（段佶坊） |
| 期望 | 「团队共识」半截门控对应 stage 有开放「去补救」；Owner=1722 |

---

## 8. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-22 | — | 挂链共识 v0.3.0 / WS1.1 写后重评；Follow-up WS-F3/F6 |
| 2026-08-21 | **v0.2.1** | 生产发版 + 慢病冒烟；状态 → **现网** |
| 2026-08-21 | **v0.2.0** | MS1–MS4 代码+测齐；DoD 勾选；待生产发版 |
| 2026-08-21 | **v0.1.2** | MS1 |
| 2026-08-21 | **v0.1.1** | 对齐共识 v0.2.1 |
| 2026-08-21 | **v0.1.0** | 初稿 |
