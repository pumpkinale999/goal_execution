# PRA · SDA 步骤呈现迭代

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源）
- **版本**：**v0.1.3**（2026-08-22）
- **里程碑**：**PRA-SDA-STEP**（步骤模板）
- **状态**：**现网**（MS1–MS4 齐；[实现闸总评](./PRA-SDA步骤呈现评价.md)）
- **共识真源**：[PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md) **v0.1.0**
- **评价**：[PRA-SDA步骤呈现评价.md](./PRA-SDA步骤呈现评价.md)（文档闸 + 实现闸）
- **适用**：active_agent · platform-docs · skstudio（进度行）；**不改** goal_execution

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md) | 四层 / 槽位 / 模板 / 写契约 **已拍板** |
| [PRA-SDA步骤呈现评价.md](./PRA-SDA步骤呈现评价.md) | 文档闸 · 实现闸 |
| [PRA产品设计.md](./PRA产品设计.md) | §4.8.6 时间线 |
| [PRA-实现与测试.md](./PRA-实现与测试.md) | DoD / 测追溯挂链 |
| `active_agent/docs/SDA.md` | 仓内指针 |

> **一句话**：`sda_step_render` 模板化履历括号；chase/escalate 写齐人/因；legacy 仅投影；进度行跟末步。

---

## 0. 共识冻结（摘录 · v0.1.0）

实现不得偏离共识全文；要点：

- 履历 = 槽位 + `STEP_TEMPLATES`；`what`/`why` 共用 `slot_clause`  
- `chased`：`n` + `user_ids`；`owner_escalated` stopped → why **`升不动，仍为`** + who=`owner`；步骤名不变  
- **不**刷 `timeline_events`；legacy 收 `legacy_*`  
- 本刀 **不做**：标题句库、CTA、非延迟 act、新 step_key、inform 正文  

---

## 1. 目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | `_step_dict` 主路径改为 `render_step`；11 step_key 皆有模板 |
| **G2** | 新 chase 行 detail **含**被催人 id；新 stopped 行 detail **含**「升不动」+ owner |
| **G3** | 旧 chase（仅 `n`）经 legacy 仍能投影出人 |
| **G4** | 卡头进度行 = 末步 label + detail（与 timeline 一致） |
| **G5** | 槽位不变量单测 + 写路径 payload 测 + 一条 chase E2E 绿 |

---

## 2. 实现切片

| MS | 交付 | 仓 | 状态 |
| -- | ---- | -- | ---- |
| **MS1 · 渲染内核** | `app/services/sda_step_render.py`；`sda.py` → `render_step`；STEP-T01/T04 | active_agent | ✅ |
| **MS2 · 写路径** | `chase_payload`；`chase_due_actions` / escalate 契约；STEP-T02/T05 | active_agent | ✅ |
| **MS3 · 进度行** | `formatSdaProgress`；`SdaEventStream`；STEP-T03 vitest | skstudio | ✅ |
| **MS4 · 文档** | 产品 §4.8.6 · 实现总账 · `docs/SDA.md` · 本文现网 | platform-docs · AA | ✅ |

**发布**：`active_agent` + docs；FE 进度行同发。**不要** `./up-prod.sh all` 除非 intentionally。

---

## 3. 测试追溯（Normative）

| ID | 断言 | 落点 | 状态 |
| -- | ---- | ---- | ---- |
| **STEP-T01** | 表驱动 required 槽；stopped 禁仅时间；system≠who | `tests/test_sda_step_render.py` | ✅ |
| **STEP-T02** | chase `n`+`user_ids`；escalate 两分支 | `tests/test_m3_action.py` | ✅ |
| **STEP-T03** | 进度行含 detail；升不动截断保留 | `frontend/.../sdaProgress.test.ts` | ✅ |
| **STEP-T04** | legacy `{"n":1}` + fallback → 含人 | `test_sda_step_render` | ✅ |
| **STEP-T05** | chase×3 → card chased 含执行人；esc 含升不动或 → | `tests/test_m5_sda.py` | ✅ |

---

## 4. DoD

- [x] **MS1**：`sda_step_render` + STEP-T01/T04 绿  
- [x] **MS2**：写路径 + STEP-T02 绿  
- [x] **MS3**：进度行 + STEP-T03  
- [x] **MS4**：产品/实现/`docs/SDA.md` 与共识对齐  
- [x] **STEP-T05** 绿  
- [x] 生产冒烟：营销计划锚点（§7；见评价实现闸）  
- [x] 本文标 **现网**

---

## 5. Follow-up（不挡本迭代）

| ID | 项 |
| -- | -- |
| **STEP-F1** | 非延迟 `awaiting_work` 补 `act` 句库 |
| **STEP-F2** | 标题 `_problem_for` 与步骤 `what` 对齐评审 |
| **STEP-F3** | CTA 文案表独立文档化 |
| **STEP-F4** | cancelled `reason` 码表人话（若需要） |
| **STEP-F5** | 产品若要坚持改「已升级」中文名 → 单独切片 |
| **STEP-F6** | **分槽补丁（进行中）**：mute/延迟 act/transition 人槽纪律 → [PRA-SDA-SLOT](./PRA-SDA步骤呈现分槽迭代.md) |

---

## 6. 风险

| 风险 | 缓解 |
| ---- | ---- |
| legacy 用「当前」executor 与历史不完全一致 | 文档标明次优；不刷库；新行必正确 |
| FE 未发时进度行仍只显示 label | MS3 已同发 |
| 旧测只 assert step_key | STEP-T05 已补 detail |

---

## 7. 冒烟锚点（生产）

| 项 | 值 |
| -- | -- |
| 项目 | 慢病平台1.0的营销计划 · `13f22ef0-35cf-4145-8a03-16d97e483936` |
| Action | **470** · `fix_definition` · `sda:75a95d69-d8e6-4311-b8d8-31657a3434ac` |
| 期望 | 催促行可见被催人（legacy→郑超/`50`）；已升级行含「升不动」+ owner；进度行与末步同文 |

---

## 8. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-21 | **v0.1.0** | 初稿：MS1–MS4 · STEP-T01..T05 · DoD · 营销计划锚点 |
| 2026-08-21 | **v0.1.1** | MS1 落地：`sda_step_render` + T01/T04 |
| 2026-08-21 | **v0.1.2** | MS2–MS4 齐：写路径 · FE 进度行 · 现网 · DoD 全勾 |
| 2026-08-22 | **v0.1.3** | Follow-up **STEP-F6** → [分槽迭代 PRA-SDA-SLOT](./PRA-SDA步骤呈现分槽迭代.md) |
