# PRA · 项目办事态机共识

- **文档类型**：产品/实现共识（切片真源）
- **版本**：**v0.3.0**（2026-08-22）
- **状态**：**现网（WS1）· 写后重评共识已拍板（WS1.1 · 待实现）**
- **上位**：[PRA产品设计.md](./PRA产品设计.md) §3.3 / §3.3.0 / §3.3.1 · [PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md) · [PRA-实现与测试.md](./PRA-实现与测试.md)
- **实现迭代**：[PRA-项目办事态机迭代.md](./PRA-项目办事态机迭代.md) **v0.2.1 现网** · [PRA-项目办事态机写后重评迭代.md](./PRA-项目办事态机写后重评迭代.md) **PRA-WS1.1**
- **评价**：[PRA-项目办事态机写后重评评价.md](./PRA-项目办事态机写后重评评价.md)

> **一句话**：用显式 **项目办事态机** 指导 SDA 生成与回收；GE 仍是图/偏差真源；半截偏差必须落在「去补救」态；**世界变了（GE/SDA 写）→ 同一 `revalidate_project` 收敛**。

---

## 1. 问题共识（已确认）

| # | 共识 |
| - | ---- |
| **P1** | 慢病平台1.0 空窗：**不是**「本来不该有处理偏差的 SDA」，而是 PM 应有的 `remediate_*`（CTA=去补救）被误 cancel。 |
| **P2** | 根因：偏差 **只 open、未 activate、无 `remediation_task_id`** → GE `is_overdue=false` → INV-3 视作「无 live overdue」→ `reconcile_schedule_cleared` 杀票。 |
| **P3** | 现网有 **优先级 + INV-1..4 + 单票微状态**，但 **缺少**「项目办事总态 → 合法 SDA」表；GE 与 AA 靠布尔投影拼接，缝上会空窗。 |
| **P4** | 现网 INV-3 口径与 §3.3.1「**未建补救任务 → 仍只出『去补救』**」冲突；**逻辑不对**，须改。 |

---

## 2. 架构共识（已拍板）

| # | 共识 |
| - | ---- |
| **A1** | **要**一台 **项目办事态机**，指导：此刻生成/保留/杀掉哪些 SDA。 |
| **A2** | **不要**用一台巨 FSM 取代 GE 的阶段/门控/任务/偏差状态机。GE = 图与偏差真源；AA = 办事编排与票务。 |
| **A3** | Sense 开票、Decide suppress、`reconcile_project` cancel、看板延迟桶、组合「健康」判定 **必须同源**：只读 `project_work_state(...)`（或由其派生的布尔），禁止各写各的 `is_overdue` if。 |
| **A4** | 新场景先改「办事态 × 合法 SDA」表，再改代码；禁止再堆与表冲突的 cancel 特例。 |
| **A5** | **双信号并存是故意的**：GE `is_overdue` = 日历/钟展示；AA 办事态 = 开票/清票/看板延迟。**禁止**为修空窗去改 GE `is_overdue`「统一信号」。 |

---

## 3. 办事态表（Normative）

由 GE 投影 + gaps **可判定**（枚举字符串本迭代钉死，勿随意改名）：

`NEEDS_DEFINITION` | `DELAY_NEEDS_REMEDIATE` | `DELAY_NEEDS_REPORT` | `EXECUTING` | `TERMINAL`

| 办事态 | 判定（要点） | 合法开放 SDA | 禁止 |
| ------ | ------------ | ------------ | ---- |
| **NEEDS_DEFINITION** | definition-gaps 非空 | 仅 `fix_definition` | remediate / deliver / review / notify |
| **DELAY_NEEDS_REMEDIATE** | 日历逾期 **或** **半截偏差**（下定义） | `remediate_stage`（CTA=**去补救**）；包络另见 §4.5 | 因「不逾期」cancel stage 票；不得进报告链 |
| **DELAY_NEEDS_REPORT** | 有可达 rem-task 且报告前置满足（`remediate_report_ready`） | remediate 报告/PM；可有 rem-task deliver | 无票空窗 |
| **EXECUTING** | 非上列延迟/定义，且非终态 | deliver / review / notify… | 开放定义/未闭环延迟票 |
| **TERMINAL** | 完成/取消/归档/软删不可达 | 无 | 任何开放票 |

### 3.1 半截偏差（Normative）

偏差 `open` **或** `active`，且 **无可达补救任务**：

- `remediation_task_id` 空；**或**
- id 有值但任务不在图上 / 软删 / 不可达  

→ 计为半截 → 所属 stage 热 → 项目可聚合进 `DELAY_NEEDS_REMEDIATE`。

### 3.2 项目级混态聚合（Normative）

多阶段并存时，**项目** `work_state` 优先级（高→低）：

1. `NEEDS_DEFINITION`（gaps 非空）  
2. 任一门控/阶段 ∈ 半截 **或** 日历逾期 → `DELAY_NEEDS_REMEDIATE`  
3. 否则任一对仍走报告链 → `DELAY_NEEDS_REPORT`  
4. 否则非终态 → `EXECUTING`  
5. 终态 → `TERMINAL`  

开票粒度仍 **一阶段一票**（`remediate_stage`）；项目态只服务 INV / 看板 / 健康，不合并多阶段票。

### 3.3 INV-3（修订 · Normative）

| Intent | 清票谓词 |
| ------ | -------- |
| **`remediate_stage`** | 仅当项目 `work_state ∉ {DELAY_NEEDS_REMEDIATE, DELAY_NEEDS_REPORT}` **且** 该 stage 已无「逾期 ∪ 半截」热项时，才可 cancel |
| **`remediate_envelope`** | **仍只认包络窗口**：窗口已不逾期 → cancel；**不**因门控半截而保留或拖杀 |

半截 ∈ `DELAY_NEEDS_REMEDIATE` → **禁止**对对应 stage 票 `reconcile_schedule_cleared`。  
对外日志 reason 名保持 `reconcile_schedule_cleared`（不新造 reason，避免审计分叉）。

---

## 4. 实现细则（已确认 · Normative）

### 4.1 GE / 投影

| ID | 决定 |
| -- | ---- |
| **D3** | **GE `is_overdue` 语义不动**；AA 办事态 **额外** 认半截 |
| **D1** | graph `needs_remediate_work`：**本切片不做** |
| **D2** | **不** 禁「只 open」；超时催 PM = follow-up |

### 4.2 粒度与开票

| ID | 决定 |
| -- | ---- |
| **G1** | 半截按 **门控所属 stage**；`remediate_stage` 一阶段一票 |
| **G3** | 日历逾期 ∪ 同 stage 半截 → **同一** concern，`items[]` 含相关 gate |
| **G2** | `open`/`active` 同等按 §3.1 |
| **C3** | concern_key **保持** `pra:remediate:stage:{phaseId}` |
| **C2** | Sense **不** 新 event_type；半截在 AA 内 **合成与 overdue 同形的 stage 热项** 再 merge（evidence 可带 `pending_activation`，**不**作分支条件） |
| **C1** | 误杀后 **新开** Action；同 concern 已 cancelled → **新 `stream_key`**（可注 `reopen_after_half_open_deviation`） |
| **O1** | Owner = **当前 `pm_user_id`** |

### 4.3 reconcile / 优先级 / 报告后

| ID | 决定 |
| -- | ---- |
| **B2** | **L1**：`NEEDS_DEFINITION` 时不开放 remediate（半截亦 suppress） |
| **B4** | scan：**先** `project_work_state` → **再** INV-1..4 → **再** Sense |
| **B3** | 报告 Action **已 done** 之后：若偏差仍 open/active **且** 又落入 §3.1 半截（无可达 rem-task）→ 回 `DELAY_NEEDS_REMEDIATE` 并按 C1 新开票。若 rem-task **仍可达**、仅 GE 未 close 偏差 → **`EXECUTING`**（AA **不**重复「去补救」）；关偏差属 GE，inform 催办 = follow-up |
| **C4** | `deviation_open` / `deviation_activate` 写挂载 **必须** `reconcile+scan`（并入 §4.6 `revalidate_project`） |

### 4.4 同源消费者（防维护分叉）

下列 **禁止** 再单独 `if assess_overdue` / `if is_overdue` 决定行为，一律经办事态或「半截∪逾期」派生：

| 消费者 | 要求 |
| ------ | ---- |
| INV-3 stage 清票 | §3.3 |
| Sense 开/并 stage 延迟票 | 合成热项 §4.2 C2 |
| 专项/子目标/公司看板延迟桶 | `work_state ∈ DELAY_*` **或** 已有开放 remediate 票；**禁止**只认 `ge_is_overdue` |
| `project_is_healthy` / 组合表扬分母 | `work_state == EXECUTING`（且非定义缺口）；半截 **不算** healthy |
| SDA CTA / 延迟角色句（「去补救」vs「写报告」） | **跟 `work_state`（+ live 补救可达）**；**禁止**仅因票上 `items=[]` 退回「去补救」 |

### 4.5 发布（WS1 历史）

| ID | 决定 |
| -- | ---- |
| **F1** | **只发 active_agent**（+ platform-docs） |
| **F2** | 先 audit dry-run；半截无票 **≥ 20** 则 `--limit` 分批 apply；首发禁止无上限一把清 |
| **F3** | DoD=半截项目有去补救票；催 PM activate 不挡发版 |
| **F4** | Panel 暴露 `work_state`：**WS1 不做** → **WS1.1 Follow-up** |
| **F5** | 审计：**扩展** `pra_invariant_audit`（不新开脚本名） |

### 4.6 写后重评 `revalidate_project`（Normative · WS1.1）

**问题（已确认）**：办事态已到 `DELAY_NEEDS_REPORT`，开放票仍显示「去补救」——因 `items[]` 被 rebuild 掏空，投影仍信空 items。根因是 **重评入口分叉 + CTA 不跟态机**。

| ID | 决定 |
| -- | ---- |
| **R1** | **单一入口** `revalidate_project(scope_id, *, source, reason)`：`load 新图` → `reconcile_project` → `scan_project` → `process_adopted_queue(scope)`；（可选）heal 开放 remediate 的 Owner/`items` |
| **R2** | **调用方**：GE `ingest_observation`、SDA **改票写路径**、cron `sense_scan` **只调 R1**；禁止再各写一套 reconcile/scan 语义 |
| **R3** | **图真源**：AA **现拉** `GET …/graph?view=sense`；outbox 内嵌 graph **不得**单独当真源（防异步旧图覆盖）。`occurred_at` 仅日志。**注**：GE 该 GET 构图前可对 active 项目幂等自愈阶段/结项漂移（《实现》§4.3.2 · §10.50）；Panel 治理者显式同步见《需求》§4.9.10 · 《实现》§10.51（**规划**）；AA reconcile 合约不变，但 sense 图可能已含修复后的 `phase.status` |
| **R4** | **SDA 写后**：默认 **同步** 调 R1（同请求）；可按 `project_id` **短窗合并**多次写为一次。纯导航 CTA（如只跳 Canvas）**不**触发 |
| **R5** | **必须触发的写**：定义/包络核销、报告提交、PM 通过/驳回、review 通过/驳回、cancel、escalate、reassign、以及任何改 Action `status`/`spec`/Decision 终态的 API |
| **R6** | **CTA / 角色句分工**：`DELAY_NEEDS_REMEDIATE` →「去补救」；`DELAY_NEEDS_REPORT` → 报告链文案；**禁止** `items=[]` ⇒「去补救」。`items[]` = 报告证据；空则从 live stage 热/偏差门控 **回填**，或 CTA 只跟态机（二者至少一） |
| **R7** | **Owner heal（O1）**：重评时开放 `remediate_*` 若 Owner≠当前 `pm_user_id` → **改到当前 PM** |
| **R8** | **读路径**：SDA GET 可保留轻量 `reconcile` 作安全网；**禁止**读路径跑满 Sense+Decide |
| **R9** | **GE outbox 合并**：同项目短窗 consolidate = **Follow-up**（与 R4 对称；不挡 WS1.1 AA 刀） |
| **R10** | **发版**：只发 `active_agent`（+ docs）；GE consolidate / Panel `work_state` 另开 |

**现场锚点**：慢病平台1.0 · Action **980** · stream `sda:58c6f0fb-…` · `work_state=DELAY_NEEDS_REPORT` 却 CTA「去补救」。

---

## 5. 现场（慢病平台1.0）

- WS1 发版后审计补开「去补救」（半截）。  
- **WS1.1**：补救任务已建后应进报告链；现网错 CTA 见 §4.6 锚点。  
- 业务：PM 对「团队共识」**确认补救时间 / activate** 后，界面不得再主推「去补救」。  

---

## 6. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-22 | **v0.3.0** | **§4.6 写后重评**：`revalidate_project` · 拉新图 · SDA 同步写后 · CTA/`items` 分工 · Owner heal；挂链 WS1.1 迭代/评价 |
| 2026-08-21 | **v0.2.2** | 生产现网（随 PRA-WS1 发版冒烟） |
| 2026-08-21 | **v0.2.1** | 清票分轨；混态聚合；Sense 合成热项；B3 收紧；看板/健康同源；apply≥20 限流；枚举钉死 |
| 2026-08-21 | **v0.2.0** | 开放项升格 §4 |
| 2026-08-21 | **v0.1.1** | §6 建议默认 |
| 2026-08-21 | **v0.1.0** | 初稿 |
