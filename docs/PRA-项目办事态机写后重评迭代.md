# PRA · 项目办事态机 · 写后重评迭代

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源）
- **版本**：**v0.1.1**（2026-08-22）
- **里程碑**：**PRA-WS1.1**（Write-path Revalidate）
- **状态**：**现网**（MS1–MS4 + RV-T*；[评价 · 实现闸](./PRA-项目办事态机写后重评评价.md)）
- **共识真源**：[PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) **v0.3.0** §4.6
- **评价**：[PRA-项目办事态机写后重评评价.md](./PRA-项目办事态机写后重评评价.md)
- **上位切片**：[PRA-项目办事态机迭代.md](./PRA-项目办事态机迭代.md) **PRA-WS1 现网**
- **适用**：active_agent · platform-docs；**本刀不改** goal_execution（R9 outbox 合并 = Follow-up）· skstudio（F4 Panel work_state = Follow-up）

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) §4.6 | R1–R10 **已拍板** |
| [PRA-项目办事态机写后重评评价.md](./PRA-项目办事态机写后重评评价.md) | 开码前总评 + 实现闸 |
| [PRA-实现与测试.md](./PRA-实现与测试.md) | DoD / 测追溯挂链 |
| [PRA产品设计.md](./PRA产品设计.md) | §3.3.1 关票/CTA 与办事态 |

> **一句话**：GE/SDA/cron 共用 `revalidate_project`；写后默认同步；CTA 跟办事态；拉新图防旧 observation 覆盖；只发 AA。

---

## 0. 共识冻结（摘录 · v0.3.0 §4.6）

实现不得偏离共识全文；要点：

- **R1** 单一入口：拉新图 → reconcile → scan → decide(scope)  
- **R2** observation / SDA 改票写 / cron **只调 R1**  
- **R3** 图真源 = AA 现拉 sense graph；禁信 outbox 快照当真源  
- **R4** SDA 写后 **同步**；可按 project 短窗合并；纯导航不触发  
- **R5** 必须触发的写路径清单（核销/报告/PM/review/cancel/escalate/reassign/改 status·spec）  
- **R6** CTA：`DELAY_NEEDS_REMEDIATE`↔去补救；`DELAY_NEEDS_REPORT`↔报告链；禁 `items=[]`⇒去补救  
- **R7** Owner heal → 当前 PM  
- **R8** 读路径仅轻量 reconcile  
- **R9–R10** GE consolidate / Panel work_state = Follow-up；只发 AA  

---

## 1. 目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | `_rescan_project` / `ingest_observation` / cron scan **收敛到同一** `revalidate_project` |
| **G2** | `work_state=DELAY_NEEDS_REPORT` + 补救可达 → SDA **报告链 CTA**，即使 `items=[]` |
| **G3** | observation 处理 **现拉图**；旧 outbox 图不单独驱动 scan |
| **G4** | 清单内 SDA 写 API 末尾同步 revalidate；导航类不调 |
| **G5** | 开放 remediate Owner≠PM → heal 到当前 PM |
| **G6** | 慢病 Action 980 类锚点冒烟：不再主推「去补救」 |

---

## 2. 实现切片

| MS | 交付 | 仓 | 状态 |
| -- | ---- | -- | ---- |
| **MS1 · 入口** | `revalidate_project`；observation/cron/`_rescan_project` 改调；**现拉图** | active_agent | ✅ |
| **MS2 · CTA/`items`** | `remediate_report_*` 空 items 回填 + `stage_needs_report` 旁路；CTA/角色句 | active_agent | ✅ |
| **MS3 · 写后挂钩** | R5 写路径 + `get_db` 同请求去重；RV-T03 | active_agent | ✅ |
| **MS4 · Owner heal + 文档** | R7；产品/实现总账；发版冒烟 | active_agent · docs | ✅ |

**发布**：只发 `active_agent` + docs。**不要** `./up-prod.sh all`。

---

## 3. 测试追溯（Normative）

| ID | 断言 | 落点 |
| -- | ---- | -- |
| **RV-T01** | `revalidate_project` 顺序：load→scan→decide；source 可观测 | `tests/test_revalidate_project.py` ✅ |
| **RV-T02** | `items=[]` + rem 可达 → CTA≠「去补救」；含报告类 kind | `tests/test_sda_ctas.py::test_empty_items_*` ✅ |
| **RV-T03** | 写路径（verify_definition / reassign）调用 `_rescan_project`；list 不调 | `tests/test_revalidate_write_hooks.py` ✅ |
| **RV-T04** | observation **不**唯信 payload graph | `tests/test_m4_observation.py::test_ingest_ignores_stale_*` ✅ |
| **RV-T05** | Owner≠PM → heal 后 owner=当前 PM | `tests/test_revalidate_project.py::test_owner_heal_*` ✅ |
| **RV-T06** | 半截→建 rem→报告链（夹具） | 既有 `test_remediate_mute_*` + RV-T02 ✅ |

**禁止**：变更探测器；全量中文 CTA 快照当唯一门票。

---

## 4. DoD

- [x] **MS1**：入口 + 拉新图 + RV-T01/T04  
- [x] **MS2**：CTA/`items` + RV-T02  
- [x] **MS3**：写后挂钩 + RV-T03  
- [x] **MS4**：Owner heal + RV-T05；文档齐  
- [x] **RV-T06** 绿  
- [x] 生产冒烟：慢病锚点（§7）报告链非「去补救」（发版后记）  
- [x] 本文标 **现网**

---

## 5. Follow-up（不挡本迭代）

| ID | 项 |
| -- | -- |
| **RV-F1** | GE outbox 按 `project_id` 短窗 consolidate（共识 R9） |
| **RV-F2** | Panel 暴露 `work_state`（原 F4） |
| **RV-F3** | 写后异步短队列（仅当同步 P95 超 SLO） |
| **RV-F4** | 偏差仍 active 但 EXECUTING 时 inform 催关偏差（原 WS-F2） |

---

## 6. 风险

| 风险 | 缓解 |
| ---- | ---- |
| 写路径漏挂 revalidate | R5 清单 + RV-T03 表驱动 |
| 同步变慢 | 项目级合并；超时再开 RV-F3 |
| 旧 observation 风暴 | R3 拉新图；RV-F1 后减量 |

---

## 7. 冒烟锚点（生产）

| 项 | 值 |
| -- | ---- |
| 项目 | 慢病平台1.0 · `bc670909-a826-45ea-a724-3241df1102d4` |
| Action | **980** · `remediate_stage` · `sda:58c6f0fb-df81-401c-9218-97956587c914` |
| 期望（发版后） | `work_state` 仍为报告态时：进度/CTA 为 **写整改报告**（或报告链），**不是**「去补救」；Owner=当前 PM |

---

## 8. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-22 | **v0.1.1** | MS1–MS4 齐；状态 **现网**；DoD 全勾 |
| 2026-08-22 | **v0.1.0** | 初稿：MS1–MS4 · RV-T01..T06 · DoD · 慢病 980 锚点 |
