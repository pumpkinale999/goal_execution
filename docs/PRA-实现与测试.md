# PRA — 实现与测试

产品真源：[PRA产品设计.md](./PRA产品设计.md) **v0.2.91**（含一致性合约 · 办事态机 · **看板 work_state 缓存** · **SDA 步骤呈现 / 分槽现网** · **写后重评 WS1.1 现网**）。运行时仓：[`active_agent`](../active_agent)。域侧：[目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) **§4.9（v2.38.71 · 进展成果；证据层 v2.38.67+）**。

**看板物化缓存（Accepted · PRA-BOARD-CACHE）**：[迭代](./PRA-目标看板work_state缓存迭代.md) — `scan_project` 唯一写 `project_work_state_cache`；看板批量读 `in_delay`；发版后须 `sense_scan` 预热。

一致性真源：[PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md)（`reconcile_project` · INV-1..4；废 v0.2.23「改期不关票」）。**INV-3 修订（现网）**：[PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) · [PRA-项目办事态机迭代.md](./PRA-项目办事态机迭代.md)（PRA-WS1 · 半截偏差不杀票）。

**写后重评（现网 · PRA-WS1.1）**：[共识 §4.6](./PRA-项目办事态机共识.md) · [迭代](./PRA-项目办事态机写后重评迭代.md) · [评价（实现闸 · 显著）](./PRA-项目办事态机写后重评评价.md) — 统一 `revalidate_project`；SDA 写后同步；CTA 跟办事态；observation 拉新图。

**SDA 步骤呈现（现网 · PRA-SDA-STEP）**：[共识](./PRA-SDA步骤呈现共识.md) · [迭代](./PRA-SDA步骤呈现迭代.md) · [评价（实现闸 · 显著）](./PRA-SDA步骤呈现评价.md)。**分槽补丁（现网 · PRA-SDA-SLOT）**：[分槽迭代](./PRA-SDA步骤呈现分槽迭代.md) · [分槽评价（实现闸 · 显著）](./PRA-SDA步骤呈现分槽评价.md) — 禁 id 嵌 act/behalf；mute/延迟 act/transition 分槽。

### HITL / Mute / escalate（现网）

- **仅 `remediate_stage` / `remediate_envelope`** 可能开票前待确认（产品名 · v0.2.34+）。表扬 / 提醒 / 定义 / 卡住改 Owner **不批**。  
- **缺省 Mute**：无 **`require_approval`** 记录 = 跳过等人批；仍 inform。  
- **stalled → escalate**：按 §4.5.1 阶梯**自动**升 Owner；不建待批 Decision；默认不换 executor。  
- UI：执行力右区 = **Project Panel**（筛选条 → 可折项目进展 → SDA；废三 Tab；深链 `?event=`）。

### 整改意图拆分（废名已完成 · v0.2.48）

| 新 intent | concern / 映射 | 闭环 |
| --------- | -------------- | ---- |
| **`remediate_stage`** | `pra:remediate:stage:…`；Sense `execution.overdue.gate\|stage` | 去补救 → 报告 → PM；计划就绪后恢复补救任务 deliver |
| **`remediate_envelope`** | `pra:overdue:project:…`；Sense `execution.overdue.project` | 改窗口 → 核销（后 rescan） |

- **废弃**笼统 `remediate`；运行时 **无**旧 intent 常量 / 读时归一 / backfill 脚本。  
- **M6.1 现网**：只认 `remediate_stage` / `remediate_envelope`；`is_remediate_intent("remediate")` 负例。  
- **交付恢复（v0.2.48）**：逾期 cancel **按门控/阶段**（包络才整项目）；日历清 + 有 rem task id 后开 rem `deliver_gate`；**不**因项目级 `has_overdue` 一刀切禁开；日历清后保留延迟票 `items[]`（空 items ≠ 报告就绪）。

### 项目推进 Action + Panel（现网 · M6 · v0.2.50）

- 契约见 PRA/GE §4.9：**现网**；推进意图分行；deliver 无 HITL；驳回=整改；逾期按实体取消原票。  
- 后置项见产品 **§5.5**；代码偏差见 [PRA-代码问题清单.md](./PRA-代码问题清单.md)。  
- **Panel IA**：**左树+右 Panel**（右区 = 筛选条 → 项目进展 → SDA）；弹窗必有卡上入口；进展可链不摘；按意图 UI 见 GE §4.9.7。  
- **项目进展（v0.2.61 壳 · v0.2.68 成果列 · 现网）**：只读表「阶段 / 任务 / 成果」插在筛选条与 SDA 列表之间；筛选行 checkbox「项目进展」控制显隐（与「我 / 已完成」同行）；**缺省勾选**；用户改过后写入 `localStorage`（`execution.projectProgress.collapsed.v1:<projectId>`）；数据主读 GE `graph`；define 视图不展示；任务行本波无深链。  
  - **成果列（现网）**：结构化 cell（`GateOutcomePart` / `outcomeParts`）；**仅已提交** GI + `content_ref` 显示材料；material 标题一等；status/metric 判定主读 + 材料附属；**summary 永远次行**；**禁止** `kb:uuid`；点击 = `openProjectNoteById`（同门控「打开本项材料」）。  
  - **标题解析**：`collectProgressNoteTitlesFromTree`（有界 BFS · `getTree` + `fetchProjectNotePath`）批量 map **优先** → 缺失 **`fetchNoteByStableId`（by-id）兜底**；同 noteId 去重；树失败整表退化为 by-id；403 不泄 title。  
  - **线框**：`project-progress-summary-wireframe.canvas.tsx`（表壳）· `project-progress-outcome-material-wireframe.canvas.tsx`（成果材料）。  
  - **测**：`projectProgressRows` · `progressNoteTreeTitles` · `ProjectProgressBlock`（by-id / seed / 树命中跳过 by-id / 403）· 既有 `projectProgressCollapseStorage`。  
  - **里程碑**：**M1–M3 已齐**（结构化 → by-id 可点 → 树批量优先 + 文档现网）。  
- **Panel 首屏（波次 A）**：筛选条（含「项目进展」）不卡 graph；表体等 graph；landing 与 SDA 流共用 `sdaEventsQueryKey`（单次 AA 拉取）。  
- **Panel 空态 · 同步推进事项（规划 · v0.2.90）**：SDA 空列表时在进展表下展示同步入口（治理者按钮 · 参与者纯文案）；GE `POST recompute-phases` + BFF `sync-execution-state` + AA rescan；见 GE **§4.9.10** · 《实现》**§10.51** · [迭代](./目标与执行-Panel空态同步推进事项迭代.md) **现网** · 线框 `sda-sync-execution-state-wireframe.canvas.tsx`。  
- **阶段协同**（GE §4.9.8）：真源 produce/prereq；**无**依赖矩阵弹窗；开边 = Canvas 拖线 + 创建任务可选 GI；Sense **按就绪集**开/推 `deliver_gate`（`deliver_artifact` **后置**）。  
- **软缺口**：GE 延迟转段（见下文 DoD）。Panel/CTA **E2E 冒烟**见 `test:e2e:pra`。  
- **CODE-003（已修 · GE v1.39.78）**：GI 提交/签收关窗与 `?gate-item=` 深链回弹 — dismiss 抑制 + `runWorkflowAction` 先 close 再 refresh（GE-T62b）。  
- **CODE-004（已修 · v0.2.53）**：写挂载 token 拒空；关键路径 FE 非阻塞 Sense；write 本地 gaps + cron 并行 GE 读；SenseEvent `decided`；评价见下文「CODE-004 性能评价」。  
- **写路径优先（v0.2.54）**：全组合 Sense 可慢；单项目 outbox 构图 = sense 轻量 + 嵌入 gaps；write/`_rescan` Decide 按 `scope_id`；链 GE **v1.39.81**。  
- **写路径 Sense（v0.2.55）**：`scan_project` 预取项目 open Action/Decision + adopted SenseEvent；延迟 flush；ingest 优先 graph 嵌入 `definition_gaps`。  
- **CODE-005（已齐 · v0.2.56）**：写挂载自愈 — 启动重试 / 拒短 token / 周期重注册 / dead requeue；评价见下文「CODE-005」。  
- **CODE-006（已齐 · v0.2.57）**：`notify_phase_complete` 终态幂等 — Sense `already_notified` + Decide 双闸；评价见下文「CODE-006」。  
- **CODE-007（已齐 · v0.2.58）**：SDA 稳定与性能 — 签收路由竖切、写路径时延日志、脏票治理、Sense 降噪；评价见下文「CODE-007」。  
- DoD 见「M6 完成定义」；线框主指针：`project-panel-app-shell.canvas.tsx`（`phase-dependency-matrix.canvas.tsx` = **历史线框**，不作现网验收）。

## 仓与端口

| 组件 | 说明 |
| ---- | ---- |
| `active_agent` `:8095` | Sense / Decide / Act / `require_approval` / SDA 投影 · timeline · stream_key |
| skstudio BFF | `/api/v1/active-agent/*` 透传 |
| skstudio UI | `/execution/...?tab=sda`；项目设置「要审批」 |
| GE | 只读 graph + **`definition-gaps`（定义评估真源）**；写挂载 outbox + 自动 flush（M4） |

### 分层硬纪律

> **SDA：UI 与深链属执行力表面；领域 API 与投影属 `active_agent`；skstudio 仅 BFF；GE 不承载 PRA 票务。**

---

## Mute：`require_approval`（M5.1 现网）

| 项 | 约定 |
| -- | ---- |
| 表 | `require_approvals`（project scope 唯一） |
| 判定 | **无行 → Mute**；**有行 → 非 Mute** |
| API | `GET/POST/DELETE /require-approvals` |
| UI | 项目设置勾选「超时整改需要人类审批」 |

---

## escalate Owner 阶梯（M5.2 现网）

```text
PM → 专项 owner → 子目标 owner → 目标 owner → 评审员（AA_REVIEWER_ESCALATION_USER_IDS 首个）
```

解析：`ProjectView` 字段 / GE graph；单测用 fixture。到顶停升；`escalation_count` 驱动类型徽章「卡住」。

---

## SDA（M5.3–M5.5 现网）

仓内：[`active_agent/docs/SDA.md`](../../active_agent/docs/SDA.md)。

| 能力 | 状态 |
| ---- | ---- |
| `stream_key`（Decision 创建，Action 继承） | 现网 |
| `timeline_events` 写路径打点 | 现网 |
| `GET /sda/events` · `/{stream_key}` | 现网 |
| 执行力 Project Panel + CTA | 现网（M6.5） |
| 双徽章语义色（进程 + 类型） | 现网 |
| 深链 `?event=`（旧 `?tab=sda` FE replace） | 现网 |
| **步骤模板 / chase·escalate 括号契约** | **现网**（[PRA-SDA-STEP](./PRA-SDA步骤呈现迭代.md)） |
| **分槽补丁（mute/act/transition）** | **现网**（[PRA-SDA-SLOT](./PRA-SDA步骤呈现分槽迭代.md) · [评价 · 显著](./PRA-SDA步骤呈现分槽评价.md)） |

### 步骤呈现（PRA-SDA-STEP · 现网 · SLOT 规划）

产品/契约真源：[PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md) **v0.1.2**。实现：`active_agent/app/services/sda_step_render.py`；FE `formatSdaProgress`。测 ID：STEP-T* 见 [STEP 迭代](./PRA-SDA步骤呈现迭代.md)；SLOT-T* 见 [分槽迭代](./PRA-SDA步骤呈现分槽迭代.md)（规划）。

| 项 | 约定 |
| -- | ---- |
| 模块 | `sda_step_render.py`（现网）；`_step_dict` → `render_step` |
| 人槽纪律（§4.0） | **禁止** id 嵌 `act`/`why`/`behalf`；mute=`pra代替`+who；延迟报告 act=`待写报告`+who |
| 新 `chased` | payload `n` + `user_ids`；detail 含第 N 次 + 被催人 |
| 新 `owner_escalated` | 升成 `from`/`to`；升不动 `stopped`+`owner` → why **`升不动，仍为`** + 独立 `who` |
| 存量 | **不**刷库；`legacy_*` 投影回退 |
| 进度行 | FE：`formatSdaProgress` = 末步 `label` + `detail` |
| 分槽补丁 | [PRA-SDA-SLOT](./PRA-SDA步骤呈现分槽迭代.md) · [评价文档闸 · 显著](./PRA-SDA步骤呈现分槽评价.md) |
| 测 | STEP-T01..T05 绿 |

### 投影 JSON

见仓内测试 `tests/test_m5_sda.py` / `tests/test_sda_title.py` / `tests/test_sda_ctas.py` / `tests/test_intent_merge.py`；字段：`process` / `type` / `title` / `cta` / `ctas[]` / `report_note` / `steps[]`。

**标题**：`对象：具体问题`（定义聚合写 `定义缺口 ×N`；空 gaps 写 `定义已齐，请核销`；延迟票写单实体具体问题，**不**写 `执行逾期 ×N`）。

**CTA（含 v0.2.27 · 角色门禁 v0.2.67 · 一致性合约 · 办事态 v0.2.83）**：按意图分下手处 — 定义有缺口时 `nav_define`「去补全定义」（**Owner ∨ Executor**）；**gaps 已空 → 系统 cancel**（竞态可短暂见复查）；**门控/阶段延迟**：报告前置未满足 → `nav_delay`（**去补救**，**仅 Owner**）；前置满足 → `open_report_note` / `submit_report`（**仅 Executor**；Owner==Executor 并集）→ `pm_approve`/`pm_reject`（**仅 Owner**）；**离开延迟办事态 → cancel remediate**（半截偏差保留；见 [PRA-WS1](./PRA-项目办事态机迭代.md)）。非 Mute `approve`；提醒 `confirm`；表扬无 CTA。整改 Note：`POST /ge/projects/{id}/pra-report-notes`（skstudio）+ `POST /actions/{id}/report-note`（AA）。未就绪 attach/submit → `409 delay_schedule_uncleared` 或 `delay_remediation_pending`。

### SDA 角色门禁矩阵（v0.2.67 · 行为真源）

投影 `_ctas` 与写 API **同口径**；身份一律 `user.matches_any(...)`（数字 id / username）。测：`tests/test_sda_role_gates.py`。

| 意图 / 阶段 | CTA / API | Actor |
| ----------- | --------- | ----- |
| `remediate_*` · 报告前置未满足 | `nav_delay` | **Owner**（+ reviewer） |
| `remediate_*` · 报告就绪 | `open_report_note` / `submit_report`；`POST …/report-note` · `…/report` | **Executor**（Owner==Executor 时并集） |
| `remediate_*` · `awaiting_pm_verify` | `pm_approve` / `pm_reject`；`POST …/pm-verify` | **Owner**（+ reviewer） |
| `remediate_envelope` · 改期核销 | `nav_delay` / `verify_stage_schedule` | **Owner** |
| `fix_definition` · 有 gap | `nav_define` | **Owner ∨ Executor** |
| `fix_definition` · gaps 空 | `verify_definition`；`POST …/verify-definition` | **仅 Owner**（+ reviewer）；纯 Executor **403** |
| `fix_definition` / 报告前 `remediate_*` | `POST …/reassign-executor` | **仅 Owner**；改派后新 Executor 见 `nav_define`、**不见**核销 |
| 路人 | 上表写路径 | CTA `[]` / **403** |

**Executor 真源（延迟 · M2）**：建补救任务（`deviation_activate`/`open` 观察）后 `Action.executor_user_id` = 图上 **first_undisposed** 补救任务 `assignee_user_id`；Sense 扫项目兜底（仍为 PM/空才改）。存量：`scripts/sync_remediate_executors.py`（dry-run 默认 / `--apply`；失败保留 PM）。测：`tests/test_observation_remediate_executor.py`。

**括号叙事（M3）**：延迟票最近一条 `awaiting_work` 投影为「待 PM 去补救」/「待{executor}写报告」/「待 PM 核对」；定义票 `role_hint`：「可补全定义；核销须项目 PM」。FE「我」= 有 CTA 的卡（`isActionableSdaCard`）。测：`tests/test_sda_role_phrases.py` · FE `projectPanelLanding.test.ts`。

**改派（M4）**：Mute 主路径开票前 `approve(executor=)` 用不上 → Owner `POST /actions/{id}/reassign-executor`；FE 定义票 CTA 旁「改派执行人」。测：`tests/test_reassign_executor.py` · FE `activeAgent.reassign.test.ts`。

**三角色冒烟清单（手工 · Chrome）**

| # | 场景 | 期望 |
| - | ---- | ---- |
| 1 | Mute 项目 · 延迟票 · 补救任务已建 · 补救人登录 | 「我」见写/交报告；括号「待{executor}写报告」 |
| 2 | 同票 · PM 登录 | 报告就绪前见「去补救/复查」；`awaiting_pm_verify` 见通过/驳回；**不见**写报告（Executor≠PM） |
| 3 | 路人 | 该延迟/定义票无 CTA；写报告/核销 403 |
| 4 | 定义票 · PM 改派执行人 | 新 Executor 见 `nav_define`；gaps 空后仅 PM 见核销 |
| 5 | 存量 `sync_remediate_executors.py` dry-run | would_update 数字合理；`--apply` 可再刷回需文档注明 |

**开票合并（v0.2.15）**：仅 `fix_definition` 项目合并（`MERGE_INTENTS`）；`gaps[]` 只挂定义缺口；延迟按 `pra:overdue:*` 分票；定义未闭环时 suppress 超时且不污染定义票；存量脚本 `scripts/merge_open_intent_tickets.py` **只**收口定义票。

**项目内办事优先级（v0.2.62 · 产品 §3.3.0）**：

| 级 | 实现落点 |
| -- | -------- |
| **L1 定义** | Sense `_should_suppress` / Decide §3.3：开放 `fix_definition` → suppress remediate/deliver/review/notify；**新建或 refresh** 定义票后 `reclaim_blocked_by_definition`（cancel + timeline `blocked_by_definition`） |
| **L2 延迟** | 无定义、有开放 `remediate_*` → Sense/Decide 挡 deliver/review/notify（`delay_blocks_*`）；开/刷延迟后 `reclaim_blocked_by_delay` |
| **L3** | 否则照旧 |
| **回收** | `cancelled`；**不** resume；核销后靠 Sense 重生 |
| **列表** | `list_events` 排序：定义 → 延迟 → 其它；`process=cancelled` 不进开放流（FE 同 `done` 剔除） |
| **首扫** | scheduler：GE `definition-gaps` 未就绪则延期首轮 `sense_scan`；发版 **先 GE 后 AA** |
| **存量** | 可选 `scripts/reclaim_blocked_by_definition.py`（授权后跑） |

测试：`tests/test_intent_merge.py`（L1 reclaim / L2 delay gate）；`tests/test_sda_priority_sort.py`（排序）；竞态见 scheduler/ge probe 测。

**定义 Canvas 就地标（v0.2.16）**：`DefinitionGapMark` 挂阶段/门控项/任务标题旁；项目级挂 `ExecutionDetailPageTitle`。

**定义评估真源（v0.2.17）**：GE `ge_assess_definition` → `GET …/definition-gaps` + `graph.definition_gaps`；AA `load_definition_gaps` / sense / verify 消费；FE `assessDefinition.ts` **只索引** graph 字段（不再本地规则）；项目级红「!」优先打开缺窗口的系统阶段。测试：GE `tests/ge/test_definition_gaps.py` · AA `tests/test_definition_gaps_client.py` · FE `assessDefinition.test.ts` / `ProjectCanvas.definitionGaps.test.tsx`。

**写挂载同步定义票（v0.2.18 → 一致性合约修订）**：AA 启动自注册 GE `after_project_graph_write`（`AA_PUBLIC_BASE_URL`）；定义相关图写入队 + 写后/周期非阻塞 flush；ingest → rebuild `actions.spec.gaps`；**空 gaps → `reconcile` cancel `fix_definition`**（废「空 gaps 保留票等人核销」）。运维可对手动积压 `POST …/observation/outbox/flush`。测试：GE `tests/ge/test_observation_mount.py` · AA `tests/test_ge_mount_register.py` / `test_reconcile_project.py` / `test_m4_observation.py`。

**发现问题履历（v0.2.19）**：开票写 `timeline.discovered.payload.problem`；合并缺口时刷新该字段；投影括号展示「事」+时间。存量无 `problem` 时从关联 `SenseEvent` 回退拼装（核销后 `gaps=[]` 仍可见）。测试：`tests/test_sda_discovered_problem.py`。

**Canvas 问题深链（v0.2.20）**：
- 定义：`define_href` → `tab=define&issue=definition` + `phase` / `focus-gate`（红 `!`；**不**带 `gate-item`）
- 延迟：`delay_href` / `nav_delay` → `tab=define&issue=delay` + `phase` / `focus-gate`（引导 PM **重计划**；SDA 主路径不要求开偏差）
- FE：`DelayIssueMark` · `delayIssue.ts` · `CANVAS_ISSUE_PARAM`；测试：`tests/test_define_deeplink.py` · `tests/test_sda_ctas.py` · `delayIssue.test.ts`

**逾期系统门控 / GE 偏差（v0.2.27 · Canvas 时间先行入口）**：GE open → 确认补救截止 → **再建**「补救·…」任务；SDA 写报告 **依赖**「补救任务已建」。PRA **仍不**自动开偏差。

**延迟票关票（v0.2.23 历史 → 一致性合约 → 办事态 v0.2.83 · PRA-WS1 代码齐）**：
- **废止**：重计划 / Canvas 写图「不」消 `remediate_*`（旧 v0.2.23 / 竖切勿再验收）。
- **现网（至 v0.2.82）**：live `assess_overdue` 为空 → cancel（曾导致半截偏差误杀）。
- **PRA-WS1（现网）**：**离开**延迟办事态 / stage 无「逾期∪半截」热项才 cancel stage；envelope 只认窗口；半截经 Sense 合成热项开票。见 [共识](./PRA-项目办事态机共识.md) / [迭代](./PRA-项目办事态机迭代.md)。
- **PRA-WS1.1（现网）**：统一 `revalidate_project`；写后同步重评；CTA 跟 `work_state`（禁空 `items`⇒去补救）；observation 拉新图。见 [写后重评迭代](./PRA-项目办事态机写后重评迭代.md) · [评价](./PRA-项目办事态机写后重评评价.md)。
- 关票（仍超期）：`submit_report` → `awaiting_pm_verify` → PM 通过 `done` / 驳回回 `awaiting_report`。
- 测试：`tests/test_overdue_cleared.py` · `tests/test_reconcile_project.py` · WS-T02/T03/T09 · `tests/test_pra_ws1_ms3.py` · `test_sda_ctas.py` · `test_m3_action.py`（report/pm）。

**延迟分径（v0.2.24 → v0.2.25 · 产品名 v0.2.34）**：
- **`remediate_stage`** `pra:remediate:stage:…`：Sense 仍产细事件；Decide/Sense 并入 `items[]`（**离开延迟办事态** → INV-3 cancel；半截偏差不杀）。**无**阶段票 `verify_stage_schedule` 关票主路径。
- **`remediate_envelope`** `pra:overdue:project:…`：窗口已不逾期 → **自动 cancel**（废「已改期请核销」为唯一关票）；**禁止**报告链。
- 存量细 `pra:overdue:gate|stage` **不**迁移；新扫描只开阶段聚合票。
- 测试：`test_intent_merge.py::test_stage_delay_merges_gate_and_window_same_stage` · `test_sda_ctas.py`。

**门控延期补救闭环（v0.2.26 · 已由 v0.2.27 修订）**：曾用纯日历门槛；见下。

**门控延期补救闭环（v0.2.27 · 已齐）**：
- `remediate_report_ready` = 日历不逾期 **且** 票内 items 对应 **补救任务已存在**；仅清 due → 仍「去补救」。
- GE：open 不建任务；activate 必填 `remediation_due` 后建任务；reason/plan 非必填。
- FE：确认补救时间弹窗（截止日 + 负责人）；无原因/方案字段。
- CTA：未就绪 → `nav_delay`「去补救」；就绪无 Note → `open_report_note`；有 Note → `submit_report`。
- 错误码：`delay_schedule_uncleared` · `delay_remediation_pending`。
- 测试：`active_agent/tests/test_sda_ctas.py` · GE `tests/ge/test_deviation.py` · FE `deviationMutations.test.ts`。

**Canvas 钟一点定时间（v0.2.28 · 已齐）**：
- GI 钟 / 队列 / 菜单 → **同一**「确认补救时间」弹窗；提交编排 `open`+`activate` | `activate` | `extend(due-only)`；**已删** `DeviationExtendModal`。
- GE：`extend` 仅 `remediation_due` 必填；空 `extend_reason` → 审计 `time_first`。
- FE：`confirmRemediationTime.ts` · tip「点击确认补救时间」；测试：`confirmRemediationTime.test.ts` · `test_extend_due_only_time_first`。

**Chrome 竖切验收（v0.2.26 · 历史）**：曾用「仅改日历→写报告」路径验收民营医疗机构项目 `37d52c27-…` / Action `546`；**负例已过时**——v0.2.27 要求该路径 **不得** 出现写报告 CTA。见文末 **v0.2.27 竖切**。

### Runtime 差口

| 项 | 状态 |
| -- | ---- |
| 缺省 Mute / require_approval | **已齐** |
| 自动 escalate 阶梯 | **已齐** |
| stream_key + timeline | **已齐** |
| SDA 投影 + 执行力 UI | **已齐** |
| 按意图分 CTA + 整改 Note | **已齐** |
| 定义合并 / 阶段延迟聚合（§3.3） | **已齐** |
| 项目内办事优先级 §3.3.0（定义→延迟→其它；回收 cancel；首扫等 GE） | **已齐（v0.2.62）** |
| **专项看板 §4.10**（环+列表；图例 `类名(n)` · **环左·图例右**；进专项默认看板；无「全部」；**按 Actor 可见过滤**；**延迟桶读 work_state 缓存**） | **现网（v0.2.66）**；layout/图例同构 **v0.2.79**；AA 看板读错误透传 **齐（v0.2.75）**；BOARD-CACHE **齐（v0.2.91）** |
| **子目标看板 §4.11**（双分布图 · 图例 `名称(n)` · **环左·图例右** · 真表；软过滤） | **现网（v0.2.76）**；layout **v0.2.79**；ACL/错误码 **已关（v0.2.75）** |
| **公司目标看板 §4.12**（三环级联 · 图例 `名称(n)` · **环上·图例下** · 真表；同软过滤/透传） | **现网（v0.2.77）**；layout 对比钉死 **v0.2.79** |
| **公司目标排行榜 §4.13**（顺利执行比率 · Tab） | **代码齐 / 待冒烟（v0.2.78）** |
| **SDA 角色门禁**（定义核销仅 PM；延迟报告 Executor；补救任务写 Executor；改派 API） | **已齐（v0.2.67）** |
| §3.3.1 门控延期补救（定时间→建任务→懒建报告→PM · v0.2.27） | **已齐** |
| §3.3.1 Canvas 钟一点定时间（v0.2.28） | **已齐** |
| 定义 Canvas 红「!」 | **已齐** |
| GE 定义评估 API（AA/FE 同源） | **已齐** |
| 写挂载注册 + 自动 flush + 空 gaps 保留核销 | **已齐** |
| 「发现问题」括号含问题说明 | **已齐** |

---

## 里程碑验收

| MS | 状态 | 要点 |
| -- | ---- | ---- |
| **M0–M1** | 现网 | 骨架；cron 感知 |
| **M2** | 现网 | HITL + `require_approval` |
| **M3** | 现网 | 催促 / 整改 / **自动** escalate |
| **M4** | 现网 | GE outbox ingest；AA 自注册；写后/周期 flush |
| **M5.1–M5.5** | **现网** | Mute · 阶梯 · timeline · 投影 · SDA UI |

## 测试

```bash
cd active_agent
.venv/bin/pytest tests/ -q
```

前端：`executionDetailTabs` 含 `sda`；联调经 BFF。

## 文档

- 仓内：`M1.md` · `M2-M3.md` · `M4-ge-mount.md` · **`SDA.md`**
- OpenAPI：[`openapi/sda-events.md`](../../platform_docs/openapi/sda-events.md)

---

## Chrome 竖切验收（v0.2.27）

| 步骤 | 期望 | 结果 |
| ---- | ---- | ---- |
| 1 | 阶段延迟票 SDA 仅「去补救」→ Canvas | **通过**（UI） |
| 2 | 开启偏差 → **只填合理截止日**（无原因/方案）→ 出现补救任务 | **通过**（API open 无 `remediation_task_id`；activate 仅 due → 建「补救·项目启动」；UI open 曾因库约束失败，见问题清单） |
| 3 | 回 SDA：「写整改报告」→ 懒建 Note → 提交 → PM | **通过**（UI 懒建 Note；API submit → `awaiting_pm_verify` → PM 通过 → `done`） |
| 4 **负例** | 只改日历、不建补救任务 → 仍「去补救」 | **通过**（due→`2026-08-19` 且无补救任务 → CTA 仍仅 `nav_delay`） |
| 5 | 包络票对照：无报告 CTA | **部分**：现网无开放包络票；阶段票路径与包络分径测见 `test_sda_ctas` |

**记录**：项目 `37d52c27-c021-4e90-b828-96af2b8c710d`（民营医疗机构项目）· Action **548** · stream `sda:b4479c46-cc47-48a4-8453-b878928827b8` · 2026-08-09。

**问题清单**

1. **GE 迁移 revision 过长**：`028_deviation_remediation_task_nullable` 超过 `alembic_version.version_num` varchar(32)，`alembic upgrade` 失败；现网曾仍 `NOT NULL`，导致 open 500 / UI「操作失败」。已改为短 id `028_dev_rem_task_null` 并落库 `DROP NOT NULL`。
2. **Canvas 逾期 tip 文案**：已改为「开启偏差，再确认补救截止日以创建补救任务」（**v0.2.28** 再改为「点击确认补救时间」）。
3. **懒建 Note 标题**：新建票标题为「门控×1」，Note 标题仍带历史「窗口 + 门控×1」字样（复用/命名残留，不影响门槛）。

---

## Chrome 竖切验收（v0.2.28 · 钟一点定时间）

**项目**：`59475a48-25a7-4b3a-a523-7b32198fcce5`（IPO审计筹备项目）· GI「项目启动」· Deviation `active` + 补救任务已存在 · 2026-08-09。

| 步骤 | 期望 | 结果 |
| ---- | ---- | ---- |
| 1 | `?tab=define&issue=delay` · GI 钟 tip「点击确认补救时间」 | **通过** |
| 2 | **一点**钟 → 仅「确认补救时间」弹窗（截止日+负责人；**无**延期说明） | **通过** |
| 3 | 填 `2026-08-18` → 确认 → toast「补救截止日已更新」· 截止变 8/18 · GI 钟灭 · 「补救·项目启动」仍在 | **通过**（验收前将「方案」段窗后移至 8/21 起，避免 `_sync` 撞 `phase_schedule_overlap`） |
| 4 | API 将 due 改回过期日 → 钟再现 → 再点仍是确认时间窗，**不是**延期说明 | **通过** |
| 5 | GE 迁移 `028_dev_rem_task_null` 已 stamp | **通过**（`alembic current` = head） |

**问题清单**

1. **段窗冲突**：开始段原窗 `7/1–7/7` 与下一段紧贴时，钟路径填「今天之后」due 会触发 `phase_schedule_overlap`；需先拉开段窗或接受 409。验收时已手动后移「方案」起点。
2. **阶段旁钟**：本项目开始段窗已盖住今天后未再验阶段钟灭；阶段钟仍只读提示。

---

## M6 完成定义（现网 · 切换日一刀切 · v0.2.44）

产品契约：PRA/GE **§4.9**（含 **§4.9.8 produce/prereq 就绪集**；**Retire 依赖矩阵 UI**）；壳层指针：[skstudio-壳层与导航UI迭代.md](../../skstudio/docs/skstudio-壳层与导航UI迭代.md) §4.2；仓内投影笔记：`active_agent/docs/SDA.md`（= Panel 主表面）。  
**已知软缺口**：GE `sign` 仍即时写阶段完成（与 AA `notify_phase_complete` 叠层，**已不再**要求人批阶段）。Panel E2E 冒烟已齐（M6.5-E2E-1～6）；仓库级 Playwright 全量仍非门禁。

### A · `active_agent`

| # | DoD |
| - | --- |
| A1 | 推进意图可开票 / 投影 / `ctas[]`（`deliver_*` · `review_gate` · `notify_phase_complete` · `review_project`；**无** `review_phase` HITL） · **现网** |
| A2 | deliver **无** HITL；阶段完成 **只通知**；`review_gate` 驳回 → **按 gate_id** cancel 推进票；`review_project` 驳回 → **整项目** cancel；逾期/整改 **按实体** 取消原推进票 · **现网（v0.2.51 · CODE-001）** |
| A3 | **仅** `remediate_stage` / `remediate_envelope`；**无** LEGACY/backfill；`map_intent` / SDA / Action **只认新名** · **现网（M6.1 · v0.2.48）** |
| A4 | Sense/Decide：**按就绪集**开/推 `deliver_gate`（前置具备或为空）；未就绪 **不**开 deliver 票；`execution.deliver.waiting` 记 **suppressed**、**不**默认 Panel 卡；「卡上表达等文档」**后置**（产品 §5.5） · **现网（M6.3 · 收口裁定）** |
| A5 | 单测覆盖 map_intent、SDA CTA、废旧名负例、就绪集负例 · **现网** |

### B · `goal_execution`

| # | DoD |
| - | --- |
| B1 | 推进相关生命周期/条件与取消原票契约可测（与 A2 对齐） · **部分**（observation + cancel；GE 延迟转段仍软） |
| B2 | 人日报**不强制**；有则落 **项目 Note**；卡上**可**挂链、**不**摘摘要正文 · **现网（链能力）** |
| B3 | 定义评估 / 延期 Canvas 仍可由顶栏链出（非 Panel 内第三 Tab） · **现网** |
| B4 | produce/prereq API 读写；创建任务可选开边；Canvas 拖线；**无**依赖矩阵弹窗；**无**第二套边表；可派生就绪信息供 AA · **现网** |

### C · skstudio FE

| # | DoD |
| - | --- |
| C1 | 执行力 **左目标树保留**；点项目 → 右区 = **Project Panel**（筛选 → 进展可折 → SDA） · **现网（M6.5 + v0.2.61）** |
| C2 | **废** `?tab=execute\|define\|sda` 三 Tab 主路径（切换日一刀切） · **现网（M6.5）** |
| C3 | **流上优先**；弹窗例外且卡上必有 CTA 入口；**无** Panel 内左右办事分栏、**无** Panel 内回树 · **现网** |
| C4 | 进展 = 短状态 update；可选 Note 链；**不**做同构摘要摘录 · **现网** |
| C5 | 进入落点：待我处理高亮（待审优先，默认不自动弹窗）→ 仅进行中 → 皆无进定义 · **现网（M6.5）** |
| C6 | 顶栏：项目名 / PM / **定义** / 设置；定义链出 Canvas，「回项目」重算落点 · **现网（M6.5）** |
| C7 | Canvas：任务区 = **任务卡片** + 拖线；创建任务可选 GI；**无**依赖矩阵弹窗 · **现网** |
| C8 | vitest / E2E：壳布局 + 废 Tab + 推进/治理 CTA + produce/prereq 开边 · **现网（冒烟）**（`npm run test:e2e:pra` · `project-execute-define` M6.5-E2E-1～6 + `deep-link`；全量 Playwright 仍可选） |

### D · 切换日

| # | DoD |
| - | --- |
| D1 | FE 废 Tab + 意图只认新名；**无**旧 intent 兼容层或 Tab feature flag · **现网** |
| D2 | 深链旧 `?tab=` **replace/忽略** 策略落地（见 GE §4.9.7）；inform 深链进 Panel 流 · **现网（M6.5）** |
| D3 | 线框对照验收：`project-panel-app-shell.canvas.tsx` + 按意图 `project-panel-wireframe.canvas.tsx` + `phase-dependency-matrix.canvas.tsx` · **Chrome 部分通过** |

**验收记录**：见下文「M6 竖切验收」；PRA §5.3 M6 标 **现网（软缺口见上）**。

### M6.4 竖切验收（review + 取消原票 · 2026-08-10 · 部分）

| 步骤 | 期望 | 结果 |
| ---- | ---- | ---- |
| A1 review_gate | `pending_sign` → review 票 + SDA CTAs | **通过**（`test_m6_review.py`） |
| A1 阶段完成 | 全 GI signed → `notify_phase_complete`（done · 无通过/驳回） | **通过**（同文件；现网修订） |
| A2 驳回 | reject → GE reject + cancel 推进票 | **通过** |
| A2 逾期 | overdue 扫描 cancel deliver/review | **通过** |
| B1 GE 观测 | submit/sign/reject → outbox `gate_item_*` | **通过**（`test_review_observation.py`） |
| 软门禁 | GE sign 仍即时转段；AA **只通知**不再人批阶段 | **现网**（SDA.md · 本节） |

---

## M6.1 竖切验收（整改废名 · 2026-08-10）

| 步骤 | 期望 | 结果 |
| ---- | ---- | ---- |
| 1 | `INTENT_BY_TYPE` / Decide 开票仅产出 `remediate_stage` / `remediate_envelope`；`map_intent` **不**产出旧名 `remediate`；`is_remediate_intent("remediate")` 为 False | **通过**（`test_m2_decide`） |
| 2 | SDA / Action 分支 `is_remediate_intent` **不**认旧名；库残留旧名 = 缺陷数据 | **通过**（负例 + CTA / report 路径） |
| 3 | 无 `LEGACY_REMEDIATE_INTENT` / `backfill_remediate_intents.py` | **通过**（v0.2.48 已删） |
| 4 | Chrome：阶段延迟票 / 包络票 CTA（去补救 · 核销）不回归 | **通过**（现网库已无旧 `remediate`；阶段票可投影；完成态卡无 CTA 属预期） |
| 5 | 日历清后 rescan：无 rem task 仍 `delay_remediation_pending`；有 rem task 可开 rem deliver；同项目其它逾期不挡 | **通过**（`test_m6_deliver` / `test_overdue_cleared` / `test_sda_ctas`） |

---

## CODE-004 性能评价（2026-08-10 · M5）

**基线（优化前实测）**：单项目 `sense_scan` ≈1.2s（GE graph+gaps 串行）；`decide_queue` ≈0.2s；FE 提交/签收 **await** syncPra ≈1.4s+；评审路径 FE 再扫一遍；写挂载 `observations` **401** → outbox dead。

| 项 | 优化前 | 优化后 | 达标？ |
| -- | ------ | ------ | ------ |
| 写挂载鉴权 | 订阅 token 漂移 → 401 | `AA_SERVICE_TOKEN` 非空才注册；curl observations **200**；token len=20 | **显著** |
| 提交/签收关键路径 | await sense+decide | `schedulePraReconcileAfterGraphWrite` 火后即忘；关窗不挡 | **显著**（vitest） |
| 评审双扫 | AA rescan + FE syncPra | FE 仅 invalidate graph；无第二次 FE `sense_scan` | **显著**（源码 + vitest） |
| Sense GE 读 | graph∥gaps 串行 sum | cron/`_rescan` 并行；write 用本地 `assess_definition` | **部分**：并行墙钟 ≈max（样例 graph 1.7s / gaps 1.1s → 并行 1.7s vs 串行 2.8s）；单扫仍受 **GE graph 下限** 约束（样例 sense_scan ≈2.4s，未达 &lt;0.8s 体感目标） |
| Decide 队列 | `DecisionSenseEvent.all()` 全表 | 处理后 `decided`；只扫 `adopted` | **显著**（单测二次 queue=0） |

**结论分级：部分。** 交互关键路径与挂载/队列已达计划；单次 Sense 绝对耗时曾绑 GE `build_project_graph`。后续已单开 **GE-PERF-GRAPH**（见 [实现与测试 · §GE-PERF-GRAPH](./目标与执行及其组织支撑(实现与测试).md) / v1.39.80），不与 CODE-004 缺陷混开。

**v0.2.54 续**：产品优先级改为「全扫可慢、单项目要快」。写挂载 outbox 已对齐 sense 轻量构图；Decide 写路径按项目 scope（见 GE **§10.44** / v1.39.81）。全组合 cron `sense_scan` **不再**作为 &lt;0.8s 目标。

**v0.2.55**：单项目 `scan_project` 由「每事件多 SQL + 每条 flush」改为项目级索引预取 + 末尾一次 flush；写 ingest 吃嵌入 gaps。目标是压低写挂载 → Panel 判断的 AA 侧墙钟（GE 构图仍在 outbox 侧）。

Chrome：样例项目已完成态，未再走完整提交→签收→评审 Network；以 API 探针 + FE 契约测替代。打开执行力页时资源计时无阻塞型 `sense_scan` 刷屏。

---

## CODE-005 写挂载自愈（2026-08-11 · 已齐 · v0.2.56）

**根因（IPO 竖切）**：GE 订阅 token 漂移 / AA 先于 GE 启动 → `observations` 401 → outbox dead → Panel 靠 FE syncPra 兜底。

| # | 里程碑 | 状态 |
| - | ------ | ---- |
| M1 | AA 启动注册失败退避重试（`ensure_observation_subscription`） | ☑ |
| M2 | GE 拒短 token + deliver 401 可观测（实现 **v1.39.82** §10.45） | ☑ |
| M3 | AA 周期重注册防漂移（`AA_MOUNT_REREGISTER_INTERVAL_SEC` 默认 300；0=关） | ☑ |
| M4 | dead outbox 401 requeue（`POST …/observation/outbox/requeue`） | ☑ |
| M5 | Chrome 竖切 + 评价收口 | ☑ |

**运维备忘**：修订阅 token 后 → GE `outbox/requeue`（默认匹配 `401`）→ `outbox/flush`；AA 周期重注册默认 300s（`AA_MOUNT_REREGISTER_INTERVAL_SEC`）。

测试：AA `tests/test_ge_mount_register.py` · `tests/test_scheduler.py`；GE `tests/ge/test_observation_mount.py`。

### CODE-005 评价（2026-08-11 · M5）

| 项 | 优化前 | 优化后 | 达标？ |
| -- | ------ | ------ | ------ |
| 启动 GE 晚到 | `ge_mount_register_failed 503`，订阅不更新 | daemon 退避重试至 `ge_mount_register_ok` | **显著**（单测 503→200） |
| 短/测试 token | 可写入 len=13 → 401 | 注册 400 `service_token_too_short`（curl 现网复现） | **显著** |
| 401 可观测 | 难辨 tok 漂移 | deliver warning 含 `tok_len` / `outbox_id` | **显著** |
| token 漂移自愈 | 需手重启 AA | 周期 `mount_reregister`（默认 300s） | **显著** |
| dead outbox | 积压不可回收 | `requeue` 190 条 401-dead → flush 全 delivered；现网 outbox 仅 delivered | **显著** |
| 写挂载主路径 | observations 连续 401 | enqueue+sense 图 → deliver **delivered** ~350ms；AA 日志 `observations` **200** | **显著** |
| Chrome Panel | — | IPO `59475a48-…` Panel 打开：标题/状态/定义票 CTA 可见（项目已完成，未再走提交链） | **通过**（只读 Panel）；提交链以 API 写挂载代替 |

**结论分级：显著。** 写挂载可靠性已自愈；FE syncPra 仍作兜底。IPO 完成态不强制 Chrome 再走提交/签收；活跃项目写路径用 GE outbox→AA observations 200 验收。

---

## CODE-006 · notify_phase_complete 终态幂等（2026-08-11 · 已齐 · v0.2.57）

**根因**：阶段全签后 `phase_needs_complete_notify` 持续为真；Sense `same_concern` 只认在飞票；`notify_phase_complete` 一旦 `done` 再 scan 会重复开票（路演项目同阶段多条 inform）。

| # | 里程碑 | 状态 |
| - | ------ | ---- |
| M1 | Sense `already_notified`（终态 Action concern）+ Decide 双闸 + 单测 | ☑ |
| M2 | `evidence.suppress_reason` + 日志（`sense_suppress` / `decide_skip_already_notified`）+ 文档 | ☑ |
| M3 | 活跃项目竖切：同阶段最多 1 张 notify + 评价收口 | ☑ |

**实现要点**（AA）：`intent_merge.has_terminal_action_for_concern`；`_ScanIndex.terminal_concern_keys`；`_should_suppress` reason=`already_notified`；Decide 在新建票前再拦一层。

测试：`tests/test_m6_review.py`（`test_phase_complete_notify_idempotent_after_done` 等）。

### CODE-006 评价（2026-08-11 · M3）

| 项 | 优化前 | 优化后 | 达标？ |
| -- | ------ | ------ | ------ |
| 同阶段二次 scan | 再开一张 `notify_phase_complete` | Action 仍为 1；新 SenseEvent `suppressed` + `suppress_reason=already_notified` | **显著**（单测） |
| Decide 漏网 adopted | 可再开票 | `decide_skip_already_notified` → event `decided`、不新建 Action | **显著**（单测） |
| 可观测 | 难辨重复开票 | 日志 + evidence `suppress_reason` | **显著** |
| 现网复扫（路演 `f8db1aba-…` / concern `…02c049fc40e1`） | 历史已积 9 张 done | 两次全组合 sense+decide 后 Action **仍为 9**；最新 SenseEvent `suppressed`/`already_notified`；decide `decisions: 0` | **显著** |
| Chrome 活跃项目 | — | `2f81b959-…` **MS-T06签收冒烟项目**（进行中）Panel：标题/状态/交付 CTA「去提交产出」可见 | **通过** |
| Chrome 路演结项盘 | 历史多 inform 残留 | Panel 打开正常（已完成）；复扫不新增 notify Action | **通过** |

**结论分级：显著。** 阶段完成通知终态幂等已闭合；历史重复票不自动清理（仅阻断增量）。不扩到 deliver/review（仍由 GE still_needed 驱动）。

---

## CODE-007 · SDA 稳定与性能（2026-08-11 · 已齐 · v0.2.58）

**范围**：签收路由定义防呆竖切 → 写路径时延可观测 → 脏票治理 → Sense 降噪 → 评价收口。  
**本波不做**：挂载健康告警弱化 syncPra、GE 即时结段改口径、Playwright 全量门禁、§5.5 后置。

| # | 里程碑 | 状态 |
| - | ------ | ---- |
| M1 | 签收路由定义防呆竖切（GE gaps + AA suppress deliver） | ☑ |
| M2 | 写路径 `pra_write_path` 埋点 + SLO（P50&lt;800ms / P95&lt;2s，非硬门禁） | ☑ |
| M3 | notify collapse 脚本 + SDA 投影去重 + 僵死定义票清单 | ☑ |
| M4 | completed 跳过 overdue；终态 notify 不 emit；suppress 少落库 | ☑ |
| M5 | 评价收口 + 产品 **v0.2.58** | ☑ |

### M1 竖切

- GE 规则已在 v1.39.83（`missing=signer_route` / `pra:def:signer:gate:…`）；本波不改规则本体。  
- AA 单测：`tests/test_code007_signer_route.py` — gaps 含 `signer_route` → 开 `fix_definition`、**不开** `deliver_gate`、deliver SenseEvent `suppressed`。  
- 现网：`2f81b959-…`（MS-T06）新建业务门控「CODE007签收缺口门控」`eligible_signers=[]` → `definition-gaps` 含 `signer_route`；sense+decide 合并进项目级 `fix_definition`（`awaiting_report`）；**无**对该门控新开 `deliver_gate`。

### M2 写路径埋点

- 字段：`event=pra_write_path` · `project_id` · `phase`=`ingest|sense|decide|total` · `elapsed_ms` · `ok`。  
- 入口：`observation.ingest_observation`、`action._rescan_project`（`app/services/write_path_metrics.py`）。  
- SLO（文档钉、非硬门禁）：单项目写后 AA 链路 **P50 &lt; 800ms、P95 &lt; 2s**。  
- 样例（2026-08-11 · 本地）：对 `2f81b959-…` observations 写入 → 客户端往返 **~138ms**（空 phases 轻量图；达 SLO）。

### M3 脏票治理

- 脚本：`active_agent/scripts/collapse_notify_phase_tickets.py`（**默认 dry-run**；`--apply` 写库）。同 `concern_key` 保留最早 `done`，其余 → `cancelled` + timeline `collapse_duplicate_notify`。僵死 `fix_definition`：GE 项目 `cancelled|archived` 或 gaps 空 → 可自动 cancel；否则只打印清单。  
- SDA 投影：`list_events` 对 `notify_phase_complete` **同 concern 只出 1 张**（优先 open，否则最新）。  
- 现网 dry-run（2026-08-11）：notify **9** 组 / **153** 张可折叠候选；僵死定义票 open **53**（自动 cancel **0**，需人工核销清单）。**真实 `--apply` 待运维确认后执行。**

### M4 Sense 降噪

- `assess_overdue`：`lifecycle_status ∈ {completed,cancelled,archived}` → 空。  
- `execution.phase.completed`：已有终态 notify Action → **跳过 emit**。  
- `adopt_or_suppress`：同 concern 已有 suppressed → **刷新 observed_at**，不新建行。  
- 现网对照（56 项目）：优化前全扫 DB insert **~320–329**；优化后同次 sense_scan `events` 计数仍 ~320（含 refresh），**DB `sense_events` delta = 0**。全组合墙钟仍可 &gt;0.8s（**仍非目标**）。

### CODE-007 评价（2026-08-11 · M5）

| 项 | 优化前 | 优化后 | 达标？ |
| -- | ------ | ------ | ---- |
| 签收路由防呆 | 假开 deliver 可撞 `no_eligible_signers` | gaps 竖切 + AA 挡 deliver | **显著** |
| 写路径可观测 | 无端到端数字 | `pra_write_path` 分相日志；样例 ~138ms | **显著**（样例达 SLO） |
| Panel notify 噪声 | 同 concern 多 done | 投影唯一 + collapse 脚本（dry-run 153） | **显著**（投影）；存量 apply 待运维 |
| SenseEvent 膨胀 | 全扫每次 +~327 行 | 全扫 DB **+0** | **显著** |
| 全组合 &lt;0.8s | ~8–12s | 仍慢 | **非目标**（明确不做） |

**结论分级：显著。** 稳定与写路径可观测已闭合；脏票存量需一次运维 `--apply`；全扫墙钟非本波目标。

---

## §3.3.0 办事优先级验收（v0.2.62）

| # | 场景 | 期望 | 测 |
| - | ---- | ---- | -- |
| L1a | 先开 delay，再开/刷 `fix_definition` | delay → `cancelled` + `blocked_by_definition`；新 overdue suppressed | `test_reclaim_delay_when_definition_opens` |
| L1b | 定义开放时不新开 remediate/deliver/review/notify | Sense suppress / Decide 不建票 | 既有 merge + Decide §3.3 |
| L2a | 无定义 + 开放 delay | deliver Sense `delay_blocks_deliver` | `test_delay_blocks_deliver_sense` |
| L2b | 延迟核销后 | deliver 可再开 | 回归既有 deliver 测 |
| L3 | 无定义无延迟 | 照旧 | 既有 |
| Sort | `list_events` | 定义 → 延迟 → 其它 | `test_sda_priority_sort` |
| Cancel | cancelled 票 | `process=cancelled`；开放流剔除 | `test_cancelled_process_label` + FE filter |
| Race | GE gaps 未就绪 | 首扫 deferred / scheduler 等待 | `test_ge_sense_ready` |
| Stock | 生产清场 | dry-run 脚本；**`--apply` 须授权** | `scripts/reclaim_blocked_by_definition.py` |

**生产清理**：未授权本波不跑 `--apply`。

---

## §4.10 专项看板（v0.2.66 · **现网**）

产品真源：[PRA产品设计.md](./PRA产品设计.md) **§4.10**。

### API 契约（M1）

`GET /api/v1/active-agent/programs/{program_id}/board`（用户态 Actor；经 skstudio BFF 同源路径）

```json
{
  "program_id": "…",
  "counts": {
    "definition": 0,
    "delay": 0,
    "in_progress": 0,
    "completed": 0
  },
  "default_bucket": "definition",
  "items": [
    {
      "id": "project-id",
      "name": "…",
      "pm_user_id": "…",
      "status": "active",
      "bucket": "definition"
    }
  ]
}
```

| 项 | 约定 |
| -- | ---- |
| 项目集合 | GE `GET /ge/programs/{id}.projects[]`；**可见性 = 当前 Actor**（透传 `X-Actor-User-Id` + **真实** `X-Actor-Is-Reviewer`；**禁止** Sense 扫仓那套 `reviewer=True` 抬权） |
| 排除 | `status ∈ {cancelled, archived}` 不进 `items` / counts |
| 已完成 | `status=completed`（不论开放票） |
| 定义/延迟 | AA 开放 Action：`fix_definition` / `remediate_*`；**延迟第二来源**：`project_work_state_cache.in_delay`（`scan_project` 写入 · [BOARD-CACHE](./PRA-目标看板work_state缓存迭代.md)） |
| `default_bucket` | 定义 → 延迟 → 进行中 → 已完成，取第一非空；全空则为 `null` |
| 实现 | `app/services/program_board.py` · `app/services/work_state_cache.py` · `GeClient.fetch_program_projects(..., actor_is_reviewer=)` · 单测 `tests/test_program_board.py`（B1–B5 · B9）· `tests/test_work_state_cache.py`（BC-T01/T02） |
| 迁移 | `scripts/migrate_m5_schema.py` → 表 `project_work_state_cache` |
| 预热 | 发版后跑 `sense_scan`（或等 cron）；冷启动无缓存行不算 `in_delay` |

### FE 落点（M2）

| 项 | 约定 |
| -- | ---- |
| Tab | `programDetailTabs()` = `["board","overview","projects","people"]`；`allowed[0]=board` 为默认；非法 / 旧 `?tab=sda` 回落 board |
| 组件 | `ProgramBoardPanel` · testid `execution-program-board` |
| 环/列表 | 无「全部」；选中 = `default_bucket` 或用户点的段；列表字段名·类标签·PM |
| 深链 | 行 → `/execution/projects/{id}{treeQuery}` |
| API | `fetchProgramBoard` → `/api/v1/active-agent/programs/{id}/board` |
| 刷新 | `refetchOnMount: "always"` + `refetchOnWindowFocus`（从 Panel 返回可感知桶变化） |
| 测 | `executionDetailTabs.test.ts` · `ProgramBoardPanel.test.ts` · `GoalProgramDetail.test.tsx`（默认看板） |

### 验收表

| # | 场景 | 期望 | 状态 |
| - | ---- | ---- | ---- |
| B1 | 同项目开放定义+延迟 | 只进 **定义** count | **单测齐** |
| B2 | 仅开放延迟 | 进 **延迟** | **单测齐** |
| B3 | active 且无定义无延迟 | 进 **进行中**（有 deliver 票仍算进行中） | **单测齐** |
| B4 | `status=completed` | 进 **已完成** | **单测齐** |
| B5 | cancelled / archived | **不**出现在环与列表 | **单测齐** |
| B6 | 点环「定义」 | 列表条数 = counts.definition | **FE 单测齐** |
| B7 | 点项目行 | 进入该项目 Panel | **FE 齐**（href → `/execution/projects/:id`） |
| B8 | 项目内 L1 reclaim 后刷新看板 | 该项目从延迟桶消失（若仍有定义则在定义桶） | **代码齐**（返回 refetch）；现网 reclaim 后肉眼复核 |
| B9 | 非评审员 / 非全量子树 governor 打开看板 | 环与列表 = GE 对该 Actor 过滤后的 `projects[]`；**不得**因 AA 抬权看到 owner 全量 | **单测齐**（`actor_is_reviewer` 透传；默认 `Is-Reviewer=0`） |
| B10 | 半截偏差、无开放 remediate 票；已 `scan_project` | 进 **延迟** 桶（WS-T07 / `in_delay` 缓存） | **单测齐** |
| B11 | 看板读路径 | **不**调用 `load_scan_bundle`；延迟来自缓存批量查询 | **代码齐**（`program_board._ids_in_delay_work`） |

**竖切记录（v0.2.65）**：AA 单测 B1–B5；FE vitest 默认 Tab=看板、bucket 过滤；环段 0 仍可点选；空专项空态文案。  
**竖切记录（v0.2.91 · BOARD-CACHE）**：消除 N×sense graph；公司目标看板 503 根因修复；见 [迭代](./PRA-目标看板work_state缓存迭代.md) · [release-v29.00.44](../../platform_docs/migration/release-v29.00.44.md)。

---

## §4.11 子目标看板（v0.2.72 · **现网**；v0.2.75 · ACL 齐；v0.2.76 · **分布图/真表 UI**）

产品真源：[PRA产品设计.md](./PRA产品设计.md) **§4.11（v0.2.76）**。

### 实现顺序

1. **GE** `GET /api/v1/ge/objectives/{id}/board-projects` — **M1 齐**  
2. **AA** `GET /api/v1/active-agent/objectives/{id}/board` — **M2 齐**  
3. **skstudio BFF** 透传 — **M3 齐**  
4. **FE** `SubObjectiveBoardPanel` — **M3 齐**  
5. 验收 S1–S12 + Chrome 竖切 — **M4 齐（2026-08-15）**  
6. **v0.2.73–75 ACL/错误码**：入口软过滤；stranger=200+空；人员 Tab **不同软**；AA **看板读**（objective+program）错误透传；FE 4xx 不重试 — **S13–S19 齐（2026-08-15）**  

### 已知差口与边界共识（v0.2.73–75 · **已关**）

| 现象 / 议题 | 根因或张力 | 共识修法 / 边界 | 状态 |
| ---- | ---- | -------- | ---- |
| anne→超声：久转后「看板加载失败」 | GE 硬 `can_read_objective_scope` 403；AA `>=400→None→404`；FE 默认重试 | **软过滤 200**；AA 透传；FE 4xx 不重试；空切片→可见范围空 | **已关** |
| 真 stranger 深链 | 树「所参与」≠ API 门禁；若再硬 403 重开壳/API 裂缝 | **200 + 可见范围空**；**禁止** stranger 整板 403 | **已关** |
| 看板软 vs 人员硬 | 目标人员 Tab 已下线；专项/项目 `people-summary` 仍硬门 | **本波不同软** | **已关（负例·专项）** |
| 专项 board 同类折叠 | `fetch_program_projects` 同 `>=400→None` | **与子目标 board 同波**透传 4xx/5xx（Sense/cron 其它路径不动） | **已关** |

**身份 follow-up（不阻塞）**：`pm_user_id` username vs owner 数字 id → 软过滤后防空环误判。

### GE 契约

`GET /api/v1/ge/objectives/{objective_id}/board-projects`

| 项 | 约定 |
| -- | ---- |
| 门禁 | `level` ∈ {`sub`,`company`} → **200**；其它 level → **400**；目标不存在 → **404** |
| **入口 ACL** | **禁止** governor 整板硬 403；**软过滤** `projects[]`（与 `GET /programs/{id}` 同构） |
| stranger / 零可见 | **200**；`projects[]` 可空 → FE 可见范围空 |
| Actor | `filter_projects_for_user` |
| 返回（sub） | `programs[]` 直属全量（含空专项）；`projects[]` Actor 可见（含 cancelled/archived lifecycle） |
| 返回（company） | `subs[]` 直属 sub；`programs[]`（含 `sub_objective_id`）；`projects[]` Actor 可见 |
| **不改** | 专项/项目 `people-summary` 仍硬门（目标侧人员 API 已下线） |
| **状态** | **现网（M1 · v0.2.77 含 company）** |

### AA API 契约

（响应 JSON 形状同前 · 略）

| 项 | 约定 |
| -- | ---- |
| 项目集合 / 排除 / 打桶 / 不变量 | 同 v0.2.72；company 另聚 `subs[]`（段长=进环项目数） |
| company | **200**（v0.2.77）；非 sub/company → **400** |
| **错误透传（看板读）** | `fetch_objective_board_projects` **与** `fetch_program_projects`：GE 4xx/5xx → AA **同族**；**禁止**折 `not_found` |
| **状态** | **现网（M2 · v0.2.77）** |

### FE 落点

| 项 | 约定 |
| -- | ---- |
| Tab / 双分布图 / URL / 空态三分 | 同 v0.2.76：左右同构环+图例 `名称(n)`；**环左·图例右**（v0.2.79）；项目真表（项目/类/专项/PM）；分布与列表留白 |
| **错误 UX** | 4xx **不重试**（`shouldRetryBoardQuery`）；可见范围空 ≠ 加载失败；人员 Tab 硬门失败用摘要失败文案（**不**当成看板失败） |
| **状态** | **现网（M3 · v0.2.76）** |

### 验收表

| # | 场景 | 期望 | 状态 |
| - | ---- | ---- | ---- |
| S1–S12 | 双环/打桶/URL/空态等（v0.2.72；**历史**含「company 无 Tab」已由 §4.12 取代） | 单测 + Chrome victor→健康城市 | **齐** |
| S13 | 非 owner 兄弟子目标（anne→超声） | **200**；切片可空 | **齐**（GE 单测 + Chrome） |
| S14 | AA 遇 GE 4xx（看板读） | 对外同族状态，绝非折叠 404 | **齐**（AA 单测） |
| S15 | FE 收到 4xx | **不重试**；秒级文案 | **齐**（FE 单测） |
| S16 | 同 Actor：专项 vs 子目标 board | 可见口径一致（软过滤） | **齐**（Chrome 抽检） |
| S17 | 真 stranger / 零可见深链 | **200** + 可见范围空；非整板失败 | **齐**（GE 单测） |
| S18 | 非 governor 开人员 Tab | `people-summary` **仍硬门**（证明未误软） | **齐**（Chrome / curl：anne→超声 403） |
| S19 | 专项 board 读路径错误透传 | 与 S14 同族；不回归 Sense 抬权 | **齐**（AA 单测 + Chrome 专项） |

### Chrome 竖切验收（v0.2.72 · 2026-08-15 · 健康城市 · Actor victor）

| 步骤 | 结果 |
| ---- | ---- |
| 1–8（默认看板→选专项→延迟→中心清选→切专项重置桶→进专项返回→桶空；**当时** company 无看板 Tab） | **全部通过**；不变量 30=30=30 |

### Chrome ACL 竖切（v0.2.75 · 2026-08-15）

| 步骤 | 结果 |
| ---- | ---- |
| 1. anne → 超声 `82831999-…` 默认看板 | **通过**：非「加载失败」；**可见范围空**（空切片） |
| 2. 同页人员 Tab | **通过（负例）**：仍失败（「无法加载人员摘要」）；未误软 people-summary |
| 3. 健康城市回归 | **通过**：双环 30 / 定义29+延迟1；非失败 |
| 4. 专项看板抽检 | **通过**：四桶正常（定义27…） |

### 评价（v0.2.72 冒烟）

| 维度 | 结果 |
| ---- | ---- |
| 功能 / 口径 / 回归 / 文档现网 | **通过**（victor→健康城市） |

### 评价与评级（v0.2.75 · ACL/错误码全路径齐）

| 维度 | 评级 | 说明 |
| ---- | ---- | ---- |
| 双环功能（owner 路径） | **显著** | S1–S12 / Chrome 1–8 已过 |
| Actor 切片 / stranger | **显著** | 软过滤 + 200 空切片；anne 超声冒烟过 |
| 人员 vs 看板边界 | **显著** | 不同软；S18 负例 Chrome 过 |
| 错误可观测性 | **显著** | AA 透传 + FE 不重试；S14/S15/S19 齐 |
| 文档完备度 | **显著** | v0.2.75 差口关闭；S13–S19 勾齐 |
| **总评** | **显著（全路径）** | GE→AA→FE + anne/victor 冒烟齐 |

---

## §4.12 公司目标看板（v0.2.77 · **现网**）

产品真源：[PRA产品设计.md](./PRA产品设计.md) **§4.12（v0.2.77）**。

### 实现顺序

1. **GE** `board-projects` 支持 `level=company` — **齐**  
2. **AA** company 三环聚合 + 错误透传 — **齐**  
3. **FE** tabs 默认 board + `CompanyObjectiveBoardPanel` + URL `sub/program/bucket` — **齐**  
4. Chrome 竖切 + 文档现网 — **齐（2026-08-15）**

### GE / AA / FE 契约要点

| 层 | 要点 | 状态 |
| -- | ---- | ---- |
| GE | company → `subs[]` + `programs[]`（`sub_objective_id`）+ 软过滤 `projects[]`；其它 level → 400 | **现网** |
| AA | 复用打桶；`subs`/`programs`/`items`（含 sub 字段）；合计不变量；403/502 透传 | **现网** |
| FE | 三环 + `名称(n)` + 真表（项目/类/子目标/专项/PM）；切 sub 清 program+bucket；环中心清选；4xx 不重试 | **现网** |

### Chrome 竖切（v0.2.77 · 2026-08-15 · 公众公司 `312400de-…` · Actor victor）

| 步骤 | 结果 |
| ---- | ---- |
| 1. 公众公司默认看板 | **通过**：Tab=看板；三环非失败（子目标 6 / 专项多 / 定义44…） |
| 2. 点健康城市 → 专项收窄 → 点公改 | **通过**：专项仅公改+强基；项目定义 29→27；URL `?sub=&program=` |
| 3. 子目标环中心清选 | **通过**：回上卷；URL 清参 |
| 4. 健康城市子目标双环回归 | **通过**：专项分布 + 项目分布仍绿 |
| 5. 人员硬门负例 | **通过**：`people-summary` anne→超声仍 **403**（未误软） |

### 评价（v0.2.77）

| 维度 | 结果 |
| ---- | ---- |
| 三环级联 / 子目标回归 / 人员边界 / 文档 | **通过** |

---

## §4.13 公司目标排行榜（v0.2.78 · **代码齐 / 待冒烟**）

产品真源：[PRA产品设计.md](./PRA产品设计.md) **§4.13（v0.2.78）**。

### 实现顺序

1. **GE** company `subs[]` 补 `owner_user_id` — **齐**  
2. **AA** company board 出 `ranking[]`（比率口径 + 排序）— **齐**  
3. **FE** 公司 Tab 插入「排行榜」+ `CompanyObjectiveRankingPanel` — **齐**  
4. Chrome 竖切标现网 — **待**

### 契约要点

| 层 | 要点 | 状态 |
| -- | ---- | ---- |
| GE | `subs[].owner_user_id` | **齐** |
| AA | `rate=(in_progress+completed)/total`；`total=0` 不进榜；排序 rate↓ total↓ name | **齐** |
| FE | Tab 仅 company；表列名次/比率/Owner/子目标（前三随内容、子目标截断）；三分空态；复用 board query | **齐** |

---

## M6 竖切验收（Chrome · 2026-08-10 · IPO审计筹备项目）

| 步骤 | 期望 | 结果 |
| ---- | ---- | ---- |
| 1 | 左树点项目 → 右区 Panel（无三 Tab） | **通过**（`execution-project-panel`；tabs=[]） |
| 2 | 待我处理 / 流上办事；定义链出 | **通过**（交付卡 CTA：去提交产出 / 核销；顶栏「定义」） |
| 3 | 定义任务卡片 + 拖线 / 创建任务声明 GI | **通过**（任务列卡片；无矩阵弹窗） |
| 4 | 就绪 deliver → review →（可选）整改 | **部分**（现网见 deliver 卡；review 主链单测齐；Chrome 未完整走签收驳回） |
| 5 | 旧 `?tab=sda` 深链落到 Panel | **通过**（URL replace 去 tab） |
