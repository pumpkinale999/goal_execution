# PRA 产品设计

- **文档类型**：产品共识（Business OS 实例 · 主动 Agent 填表）
- **版本**：**v0.2.91**（2026-08-27 · 看板 work_state 缓存）
- **状态**：**现网** — **M0–M6 现网**；主表面 **Project Panel**；**Panel 空态同步推进事项（§4.9.4 · 规划）**；**项目进展成果列**对齐证据层；**项目内办事优先级**：**定义 → 延迟 → 其它**（§3.3.0）；**SDA 角色门禁**；**专项/子目标看板**（§4.10/§4.11 · **现网** · **环左·图例右** · **延迟桶读 work_state 缓存**）；**公司目标看板**（§4.12 · **现网**：三环级联 · **环上·图例下** · 图例 `名称(n)` · 真表）；**公司目标排行榜**（§4.13 · **代码齐 / 待冒烟**）；协同 = produce/prereq；阶段完成 = notify；**M6 DoD** 落 [PRA-实现与测试](./PRA-实现与测试.md)；链 GE **v2.38.71** / 实现 **v1.39.83+**；缺省 Mute。**后置**集中见 **§5.5**。**性能优先级**：全组合扫描可慢；**单项目变化 → 判断/Panel 要快**（写路径 `pra_write_path` SLO：P50&lt;800ms / P95&lt;2s）；**看板读**须 O(1) DB、**禁止** per-project 拉 sense graph（[BOARD-CACHE](./PRA-目标看板work_state缓存迭代.md)）。**项目办事态机**：[共识](./PRA-项目办事态机共识.md) **v0.3.0** / [PRA-WS1 现网](./PRA-项目办事态机迭代.md) / [写后重评 PRA-WS1.1 现网](./PRA-项目办事态机写后重评迭代.md)。**SDA 步骤呈现**（槽位+模板 · 现网）：[共识](./PRA-SDA步骤呈现共识.md) **v0.1.2** / [STEP](./PRA-SDA步骤呈现迭代.md) / [分槽现网](./PRA-SDA步骤呈现分槽迭代.md)。
- **缩写**：**PRA**（PRoject Agent；**不用** PA）
- **读者**：产品、架构、GE / Hermes profile 设计与实现者
- **上位理论**：[主动agent.md](../../platform_docs/hermes-self/主动agent.md)（感知 · 决策 · 行动）
- **一致性**：开放票须跟 GE 真源收敛，见 [PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md)（废止「改期不自动关 remediate」；**INV-3** 以办事态为准，见下挂链）。
- **冲突处理**：项目 / 阶段 / 门控 / 任务域语义服从 [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md)；本文约束 PRA **如何感知、决策与行动闭环**，不改写 GE 状态机。行动运转态落在**主动 Agent 运行时**（见 §4.1），不以本服务替代 GE 真源。

**关联文档**

| 文档 | 关系 |
| ---- | ---- |
| [主动agent.md](../../platform_docs/hermes-self/主动agent.md) | 主动 Agent 理论；本文 = PRA 实例 |
| [business-os框架.md](../../platform_docs/business-os框架.md) | Business OS 角色目标（§6.2 PRA） |
| [business-os共识.md](../../platform_docs/business-os共识.md) | 现网细账与红线 |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | 项目 · 阶段 · 门控 · 任务真源 |
| [Governance-Assistant产品设计.md](./Governance-Assistant产品设计.md) | 三维偏差上卷对象 |
| [Personal-Assistant产品设计.md](../../platform_docs/hermes-self/Personal-Assistant产品设计.md) | 对人行动通道（Decide/Act 阶段再用） |
| [专业智能体规范.md](../../platform_docs/专业智能体规范.md) | Master→Expert（Decide/Act 阶段再用） |
| [组织PBC共识.md](../../pbc/docs/组织PBC共识.md) | PRA **不**改写 PBC、**不**自动打档 |
| [PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md) | **GE 真源 ↔ AA 票**一致性 INV；改期/空 gaps/终态收敛（现网切片） |
| [PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) | **项目办事总态 → 合法 SDA**；半截偏差 ∈ 去补救；INV-3 修订；**§4.6 写后重评** |
| [PRA-项目办事态机迭代.md](./PRA-项目办事态机迭代.md) | PRA-WS1 实现/测/DoD（现网） |
| [PRA-项目办事态机写后重评迭代.md](./PRA-项目办事态机写后重评迭代.md) | PRA-WS1.1：`revalidate_project` · CTA 跟态机 |
| [PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md) | **SDA 履历括号**：四层 · 槽位 · 步骤模板；**§4.0 人槽不变量** |
| [PRA-SDA步骤呈现迭代.md](./PRA-SDA步骤呈现迭代.md) | PRA-SDA-STEP 实现/测/DoD（现网） |
| [PRA-SDA步骤呈现评价.md](./PRA-SDA步骤呈现评价.md) | SDA-STEP 文档闸 + 实现闸 |
| [PRA-SDA步骤呈现分槽迭代.md](./PRA-SDA步骤呈现分槽迭代.md) | PRA-SDA-SLOT：mute/act/transition 分槽补丁 |
| [PRA-SDA步骤呈现分槽评价.md](./PRA-SDA步骤呈现分槽评价.md) | SLOT 开码前评价（文档闸 · 显著） |
| [PRA-目标看板work_state缓存迭代.md](./PRA-目标看板work_state缓存迭代.md) | **PRA-BOARD-CACHE**：看板读物化 `work_state`；scan 单点写 |

---

## 0. 一句话

**PRA** 让**项目**按时、保质、不超支地落地：先**感知**定义与执行问题（及目标树组合上的统计与周环比），再决策与行动；不替代人签偏差，不改 PBC 档位。

---

## 1. 产品目标与边界（摘要）

| 项 | 约定 |
| -- | ---- |
| **目标** | 成事：**按时 · 保质 · 不超支**；提高经 PA / Master→Expert 完成的比例 |
| **感知主语** | **单项目**；组合入口 = 专项 / 子目标 / 目标下子树的统计与态势 |
| **与 GA** | 三维等问题上卷；不替组织拍板 |
| **与 PBA** | 可提供弱关联交付线索；**不**改写个人 PBC、**不**自动打档 |
| **红线** | 不自动开偏差（含系统节点）；人可对**逾期**系统门控开偏差以创建补救任务；不改 PBC / 不自动打档 |

**建设顺序**：感知（§2）→ 决策（§3）→ 行动（§4）。

---

## 2. 感知子系统（Accepted）

### 2.1 定位

PRA 的主发动机首先是**感知**：看清问题，再谈决策与行动。

感知分两层，**共用同一套问题模型**；组合层**不**另立第三套问题类型。

派工、催办、核销、升级 GA、通道选择等属 **Decide / Act**，**不**在本章。

---

### 2.2 层 1：单项目

感知顺序：**定义 → 执行三维**。  
定义不过关时，优先暴露定义缺口，不优先吵执行三维。

#### 2.2.1 定义是否靠谱

按**项目属性**系统可判定；**缺少判定所需数据 = 定义问题**。

最低标准（保持简洁）：

1. **阶段数 ≥ 3**  
   「开始」「结束」为系统法定阶段；至少再有 **1 个执行阶段**，否则没有真正可推进的工作段。
2. **每一阶段**  
   - 至少 **1 个门控项**  
   - 至少 **1 个任务** 产出该门控项（门控不能悬空）
3. **截止日 / 包络**  
   - 门控项须有 `planned_due`；业务阶段须有持久化 `planned_end`。  
   - **项目截止日口径 = GE 包络**：开始/结束系统阶段均须有完整计划窗口（`planned_start`+`planned_end`）；以 `开始.planned_start`～`结束.planned_end` 为项目 envelope（见 GE §4.8）。**无**独立的 `project.planned_end` 字段。  
   - 包络未齐时：系统阶段与项目汇总均可报 `definition.missing_deadline`。
4. **任务负责人**  
   任务须有有效负责人（生命周期「启动项目 / 结项复盘」以 PM 为有效负责人）；缺则 `definition.missing_assignee`。

**评估真源（v0.2.17）**：定义完整性由 **GE** `GET /ge/projects/{id}/definition-gaps`（及 `GET …/graph` 内嵌 `definition_gaps`）判定；PRA / SDA / Define Canvas **只消费**该结果开票或打标，**不**各自镜像规则。**v1.39.83**：缺口含 **签收路由**（§3.4.4 · 无 `eligible_signers` / 无下游 prereq 消费 Task → 定义不过；「项目启动」orphan 例外仍保留）。

#### 2.2.2 执行是否顺利（定义过关之后）

| 维度 | 粒度 | 信号来源 |
| ---- | ---- | -------- |
| **超时** | 门控项 / 阶段 / 整个项目 | **系统可算**（相对截止日） |
| **质量** | 门控项 / 阶段 / 整个项目 | **PM 人工判断并输入**；PRA **不**自动判定，只消费已标明异常 |
| **成本** | 门控项 / 整个项目（暂不含「阶段成本」） | **PM 人工判断并输入**；同上 |

说明：质量、成本相关属性现网可能尚未齐备；**设计先假设有**，后续在 GE / 产品侧补齐录入。

---

### 2.3 层 2：组合（专项 / 子目标 / 目标）

对节点下**子树全量**、周期内**有效项目**，就层 1 的同一套信号做统计，并用同一套统计做态势。

#### 2.3.1 在册范围

| 计入 | 不计入 |
| ---- | ------ |
| 进行中、**已完成** | **取消**、**归档** |

「有效」= 取消 / 归档以外；组合统计看**周期内**这批有效项目。

#### 2.3.2 统计什么

对层 1 各类问题做**计数 / 占比**，并计算：

- **健康项目**：定义过关，且无超时、无质量标记、无成本标记  
- **健康占比** `healthy_ratio = n_healthy / n_有效`（`n_有效=0` 时不算环比、不触发组合决策）

一项目多病：**各类计数可重叠**（可同时计入超时与质量等）。

**不**另开与层 1 无关的问题类型；**不**另搞加权风险分等（本阶段不做）。

#### 2.3.3 态势是什么

态势 = **健康占比的周环比**（本周 vs 上周），**不**另开「结构态势 / 集中态势」等概念。  
各类问题 count 仍统计并进入 inform / 升级载荷，用于解释原因，**不**各自单独触发组合行动。

| 态势 | 判定（Normative） |
| ---- | ----------------- |
| **恶化** | 本周 `healthy_ratio` **低于**上周 |
| **好转** | 本周 `healthy_ratio` **高于**上周 |
| **持平** | 相等 → **不触发**组合行动 |
| **连续两周恶化** | 连续两个周切均满足「恶化」 |

周切规则：

- **每周六**切一周  
- **未满一周也算一周**  
- 周期**开始、结尾都计入**

（实现时再定切分时区；小样本抖动阈值可后置，不挡本共识。）

---

### 2.4 感知输出（概念）

| 层 | 输出要点 |
| -- | -------- |
| 单项目 | 定义是否过关及缺口要点；定义过关后的超时 / 质量 / 成本（各到约定粒度） |
| 组合 | 子树有效项目上：各类问题计数/占比、**健康占比**、相对上周的健康占比环比（恶化/好转/持平） |

具体 SenseEvent 字段、挂载点（写 / 读高信号 / 周期）与实现落点见 **§2.5**；**问题模型以 §2.1–§2.3 为准**。

---

### 2.5 感知实现共识（Accepted · **M1 现网**）

#### 2.5.1 运行时与依赖方向

| 项 | 约定 |
| -- | ---- |
| **运行时** | 独立卫星服务（如 `active_agent`）；**不**并入 GE |
| **GE** | 项目域真源；提供**观测挂载点与契约** |
| **PRA** | **注册**订阅挂载点；将域观测转为 `SenseEvent` |
| **依赖** | **单向**：PRA → GE 读（写）真源；GE → PRA **仅出站观测**。GE **不得**问询 PRA「是否已有在途票」 |

skstudio：BFF / AAP 深链 UI。PA/GA：inform 触达（决策/行动侧）。

#### 2.5.2 v1 感知范围

| 做 | 暂不做（字段/能力齐后再开） |
| -- | -------------------------- |
| 单项目：**定义缺口**、**超时**（门控/阶段/项目） | 质量 / 成本事件（健康公式中暂视「无标记」） |
| 组合：**健康占比**及周环比事件 | — |

#### 2.5.3 三通道触发（Normative）

| 通道 | 行为 |
| ---- | ---- |
| **写挂载** | 相关写成功后按契约投递域观测（截止日、阶段/门控/产出任务结构、项目生命周期等）；PRA 订阅后产 `SenseEvent`，并 **重建在途定义票 `gaps[]`**（可刷成空，**不**自动关票）。业务去重在 PRA（`concern_key` / 在途票） |
| **Cron** | **日扫**：定义 + 超时；**每周六周切**：写专项周快照、算健康占比环比并产恶化/好转/连两周恶化事件。扫完并投递后由 **同一 cron 任务**推进覆盖水位（见 §2.5.3.1） |
| **读** | 读路径可本地计算尖信号（如 `is_overdue`）。**不是**每次读都通知订阅方。**仅当**尖信号在 **`last_coverage_at` 之后才成立** 才投递；读投递**不得**改写水位。一期可先不启用读投递（仅写+cron），避免 GE 依赖水位副本；启用时见 §2.5.3.1 |

**禁止**：为读去重维护**永久指纹表**。  
**禁止**：每个 GET 都 HTTP 打 `active_agent` / PRA。  
**禁止**：GE 在读路径上 **RPC 问询** PRA「水位是多少 / 是否已有在途票」。

#### 2.5.3.1 覆盖水位 `last_coverage_at`（Normative）

| 项 | 约定 |
| -- | ---- |
| **语义** | 上次 **PRA 感知 cron** 已扫完并完成投递的覆盖时刻；与「另维护一套 cron 时钟再对齐」无关——**就是同一次 job 提交的时间戳** |
| **权威存储** | **`active_agent` 库**（按实例，如 `agent=pra`）；**不是** GE 权威字段，**不是** PA/GA |
| **谁写入** | 跑在 `active_agent` 进程内的 **PRA cron 任务自己**在扫完并投递成功后 `upsert`；无其它角色代写 |
| **写入步骤** | ① job 开始取 `coverage_as_of`（建议用开始时刻，整次扫描同一快照）→ ② 扫描 / 产事件 / 投递 → ③ **先投递成功，再** `last_coverage_at = coverage_as_of` |
| **仅谁可推进** | **仅**上述 cron（日扫 / 周切等全量感知扫）；写挂载、读投递、HITL **均不得**把水位改成 `now` |
| **与 GE** | GE **不负责**产生或维护权威水位。若日后读路径要在 GE 侧判「水位之后的尖」，由 **cron 写完权威水位后，单向把同一值推送到 GE 副本**；GE 只读本地副本，**读时不问** `active_agent` |

```text
# active_agent 内 PRA cron（示意）
coverage_as_of = now()
events = scan_and_build(as_of=coverage_as_of)
deliver(events)
db.upsert(pra_coverage, last_coverage_at=coverage_as_of)  # 仅此处写权威水位
# 可选：push_coverage_replica_to_ge(coverage_as_of)
```

---

#### 2.5.4 GE 挂载点（解耦）

- GE 定义挂载点（何时触发）与载荷契约（含 `idempotency_key` / 变更摘要等）；**不**嵌入 PRA 决策逻辑。  
- 订阅方（PRA，日后可有其它 Agent）注册 URL/密钥与订阅的挂载点。  
- 投递宜异步（如 outbox）、at-least-once；订阅方幂等处理。  
- 一期至少：`after_project_graph_write`（及生命周期类写）；读侧「水位之后尖信号」可复用同一出站管道，`source=read_high`。

GE 域模型对定义/超时**大体够用**（如门控 `planned_due`、阶段窗口、产出关系、派生 `is_overdue`）。**定义完整性只读接入（v0.2.17 现网）**：`GET /ge/projects/{id}/definition-gaps`（权威）+ graph 嵌 `definition_gaps`；鉴权同读 graph；项目截止日口径 = 开始/结束包络（§2.2.1）。

#### 2.5.5 SenseEvent 目录（v1）

**公共字段**：`id`、`agent=pra`、`type`、`scope_kind`（`project`\|`program`）、`scope_id`、`concern_key`、`observed_at`、`source`（`cron`\|`write`\|`read_high`）、`evidence`、`status`（`pending`\|`adopted`\|`suppressed`\|`decided`）。

| 场景 | `type`（例） | `concern_key`（例） |
| ---- | ------------ | ------------------- |
| 阶段数 &lt; 3 | `definition.stages_lt_3` | `pra:def:stages:{project_id}` |
| 阶段缺门控或缺产出任务 | `definition.stage_incomplete` | `pra:def:stage:{stage_id}`（门控级可含 `:gate:{id}`） |
| 无截止日 / 包络未齐 | `definition.missing_deadline` | `pra:def:due:{entity_kind}:{id}`（`entity_kind`∈ stage\|gate\|project） |
| 任务缺负责人 | `definition.missing_assignee` | `pra:def:assignee:task:{task_id}` |
| 门控/阶段/项目超时 | `execution.overdue.{gate\|stage\|project}` | `pra:overdue:{kind}:{id}` |
| 健康占比恶化/好转 | `portfolio.health.worsened` / `improved` | `pra:health:wow:{program_id}` |
| 连续两周恶化 | `portfolio.health.worsened_2w` | `pra:health:wow2:{program_id}` |

持平不产事件。周快照建议独立表（`program_id + week_end`），环比读快照；事件只表达「该过问」。

同一 `concern_key`：已有在途 Action / pending Decision 时，新观测宜 **suppressed 或刷新 evidence / 并入**，避免日扫风暴。

**示例**：

```json
{
  "type": "execution.overdue.gate",
  "scope_kind": "project",
  "scope_id": "proj_123",
  "concern_key": "pra:overdue:gate:gate_9",
  "source": "cron",
  "evidence": {
    "gate_id": "gate_9",
    "due_at": "2026-08-01",
    "days_overdue": 6
  }
}
```

#### 2.5.6 一句话

> GE 挂载 + PRA 注册；写推；PRA cron 自扫自投递并写入 `active_agent` 权威水位；读尖可选且不得改水位、不得问询 PRA；单向依赖；无永久指纹表。

---

## 3. 决策子系统（Accepted）

### 3.1 定位

针对已采纳的感知结果与真源快照，由 **Harness（规则）** 拟定**缺省处理安排**，经 **inform**（及**仅整改**时可能的开票前审批）后派遣；**不**负责盯执行进度（属行动子系统）。

决策结局对齐理论：`open_action`（含并入既有项）；**禁止**无主无期的开放 `defer`。规则为主；LLM 最多话术/摘要，不擅自改结局。

---

### 3.2 目标树上的主责与可见性

**事挂在树上的一个作用节点；主责（审批 Owner）唯一；祖先能看不能代办。**

| 行动 | 作用节点 | 审批 Owner（HITL） | 缺省执行侧 | 可见 |
| ---- | -------- | ------------------ | ---------- | ---- |
| 定义补齐 | **项目** | **项目 PM** | **PM 或改派代理人**（Mute 下 Owner `reassign-executor`）；**核销仍仅 PM**（不可由改派 Executor 代行） | 项目相关方 + **祖先只读** |
| 整改 | **项目** | **项目 PM** | **整改责任人**（= 补救任务负责人；现网已接线）；完成后仍要 **PM 核对与处置** | 同上 |
| 提醒 / 表扬 | **仅专项（Program）** | **专项 `owner_user_id`** | 专项 owner（知晓/表态） | 同上 |
| 升 GA | **仅专项** | **拍板人 = 父级子目标 `owner_user_id`**（无则上收到**公司目标** owner） | 经 **GA（管理助手）通道**落盘；**GA 不是拍板人** | 拍板人必见；专项 owner 可见；祖先只读 |

- 兄弟 / 旁支：**不可见**。  
- 父节点**不代办**子项目日常整改。  
- **单项目不升 GA**。  
- **子目标 / 公司目标**：v1 **可做感知统计**，**不开**提醒 / 表扬 / 升 GA 三类组合行动（避免与专项双刷）。

#### 3.2.1 公司目标为何不接「连续恶化」第一棒决策

连续两周恶化时，**决策要求**落到**父级子目标 owner**，**公司目标 owner 不接这张默认决策票**——合理，且为 Accepted：

1. **就近治理**：调优先级 / 取消项目 / 开整改，多发生在某一子目标下的专项与项目；子目标 owner 对子树有治理权，是第一拍板人。  
2. **一条 HITL**：若子目标与公司目标对同一恶化各审一次，超时默认批会冲突，也拖死主动环。  
3. **升级已上移一级**：专项恶化不是专项自己批自己，而是到子目标；对公司目标而言，下一级管域应先履职。  
4. **公司目标不没信息**：按可见性为**祖先只读**，能看见下属在途与升级项，只是**不是默认审批 Owner**，避免被专项噪声淹没。

**第二跳（后置，非 v1 必做）**：若子目标拍板后仍连续恶化、多专项反复升级、或需跨子目标挪优先级，再 inform **公司目标 owner** 审批。那是「升级的升级」，不与第一棒抢票。

---

### 3.3 单项目事件策略

| 项 | 约定 |
| -- | ---- |
| 优先级 | 见 **§3.3.0**（**定义 → 延迟 → 其它**） |
| 开票数量 | **定义**：项目内全部定义缺口 → **1** 张 `fix_definition`；**阶段延迟**：同阶段门控逾期 + 阶段窗口逾期 → **1** 张 `remediate_stage`（**跨阶段不合并**）；**项目包络**逾期 → **1** 张 `remediate_envelope` |
| 整改规格 | 见 **§3.3.1**（`remediate_stage`）；包络见 §4.8.6.2（`remediate_envelope`，仅改期核销） |
| 在途同类 | **定义**：新缺口并入既有定义票并刷新 `gaps[]`；**阶段延迟**：细事件并入 `pra:remediate:stage:{stage_id}` 的 `items[]` 并重建；**项目包络**：同一 `pra:overdue:project:{id}` 在途则刷新 |
| 聚合键 | 定义：`pra:def:project:{id}` + `gaps[]`；阶段延迟：`pra:remediate:stage:{id}` + `items[]`（细事件键仍为 `pra:overdue:gate|stage:…` 作证据）；项目包络：`pra:overdue:project:{id}`（**无** `pra:remediate:project:{id}`） |
| 定义挡执行 | 项目有未闭环 `fix_definition` 时，超时 / 交付 / 评审 / 阶段完成通知 Sense **suppress**，**不**开对应票，且**不**把逾期并进定义票的 `gaps[]`；已开非定义票 **cancel**（§3.3.0） |
| 定义就地标 | 执行力「定义」Canvas：阶段 / 门控项 / 任务 / 项目标题旁，**有问题才**出红「!」；hover 短句原因；点击打开 **Canvas 编辑**（项目级包络 → 开始/结束阶段；门控/任务 → 对应节点）；**不**进项目设置；无问题不加打勾 |
| 缺责任人等 | 开**补齐类**行动（有主人 + 时限）；禁止无主无期 defer |
| 红线 | PRA **不**自动开偏差；不改 PBC；**不**自动迁移/关闭存量细粒度 `pra:overdue:gate|stage` 票 |

#### 3.3.0 项目内办事优先级（Normative · v0.2.62）

对**同一项目**（`scope_kind=project` + `scope_id`），SDA / Sense / Decide 统一遵守：

| 级 | 条件 | 行为 |
| -- | ---- | ---- |
| **L1 定义** | 有开放 `fix_definition` | **硬门禁**：不新开 `remediate_*` / `deliver_*` / `review_*` / `notify_phase_complete`；已开上述票 **cancel**（timeline `reason=blocked_by_definition`） |
| **L2 延迟** | 无定义、有开放 `remediate_stage` / `remediate_envelope` | **次门禁**：不新开交付 / 评审 / 阶段完成通知；已开同类 **cancel**（`reason=blocked_by_delay`）。**不**挡定义 |
| **L3 其它** | 无定义、无开放延迟 | 现有意图规则照旧 |

**回收语义（锁定）**：

- 状态 = `cancelled` + timeline 写明 `blocked_by_definition` 或 `blocked_by_delay`
- 定义 / 延迟核销后 **不**自动 resume 旧票；靠下次 Sense 再开（与现网 `deliver` 因 `overdue_or_remediation` cancel 一致）
- Panel「我」/开放流：有定义时应首先看到「去补全定义」；`list_events` 排序 **定义 → 延迟 → 其它**；`cancelled` 不进开放流

**生产事故（发版竞态）**：若 AA 先于 GE 就绪，首扫 `definition-gaps` **404** → 跳过定义 Sense → 先开延迟票；GE 就绪后定义再开，但若只 suppress 不回收，则「定义 ×N + 去补救」并存。对策：首扫等 GE gaps 就绪；发版 **先 GE 后 AA**（或 AA 启动后待 GE ready 再扫）。

#### 3.3.1 门控延期补救（SDA · Normative · v0.2.48 · intent=`remediate_stage`）

适用范围：**门控项延期**（intent **`remediate_stage`**；concern `pra:remediate:stage:…`，含并入的门控逾期项）。**不**覆盖 **`remediate_envelope`**（项目包络 · §4.8.6.2；窗口清后 **系统 cancel**，见 [PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md)）。

| 项 | 约定 |
| -- | ---- |
| **同构** | 第 1 次与第 N 次补救 **同一过程**；**不**设「再补救 / 延期修订」为独立用户流程或独立 SDA CTA 轨 |
| **闭环** | **PM 去补救**（定合理时间 → **建补救任务**）→ **补救责任人写整改报告** → **提交报告** → **PM 通过或驳回** |
| **角色 / 投影** | SDA CTA 与写 API **同口径**：去补救 / PM 核销 → Owner；写/交报告 → Executor（建任务后 = rem-task assignee，现网 A+B 接线）；Owner==Executor 并集放行 |
| **PM 去补救** | 深链 `nav_delay` → Define/Canvas：**钟一点定时间**——一次点击确认 **补救截止日**，FE 编排 GE `open`+`activate` 或 `extend(due-only)`（见 GE 需求 §6.3）。叙事（原因/方案）进 **整改报告 Note**，**不**要求 Deviation 填 reason/plan/`extend_reason` |
| **报告前置（计划已就绪）** | 票内 `items[]` 对应门控：**补救任务已存在**（非空 `remediation_task_id`），且日历/补救截止不再逾期（与 Sense `assess_overdue` 同口径取反）。日历清后 **保留** `items[]` 身份（空 items ≠ 报告就绪）。**仅改日历、未建补救任务 → 仍只出「去补救」** |
| **报告** | 前置满足且无 Note → SDA primary `open_report_note`「写整改报告」（FE **懒建**）；有 Note → 提交。**禁止**单独强制「创建整改报告」主 CTA |
| **关票** | **仍超期需说明**：提交后 PM 通过 → `done`（并 rescan）；驳回 → 回写报告。**离开延迟办事态**（日历已清 **且** 无「open/active 无 rem-task」半截偏差，或已进入报告链等；见 [办事态机共识](./PRA-项目办事态机共识.md)）→ **系统 cancel**（`reconcile_schedule_cleared`）。**禁止**仅因 GE `is_overdue=false` 杀掉仍需「去补救」的票。废止「改期不关票」。**进入报告链后**主 CTA 须为报告路径，**禁止**因票上 `items=[]` 仍主推「去补救」（[写后重评 §4.6](./PRA-项目办事态机共识.md)） |
| **推进恢复** | 逾期/偏差激活 → **cancel 该门控（或该阶段）原** deliver/review；**计划就绪 + 补救任务已建**后，在补救任务上恢复 `deliver_gate`（可与延迟票并存）。**不**因项目内其它实体仍逾期而整项目禁开 deliver/review |
| **Canvas** | 「去补救」= **钟一点定时间建任务**；同一「确认补救时间」弹窗；**禁止**再弹「延期说明」窗。SDA 为主叙事与 CTA |
| **GE** | Deviation / 补救 Task 为域载体；对 SDA 暴露为「定时间→有补救任务」门槛，**不得**再以「延期修订 / 填原因方案」为第二套产品叙事 |

---

### 3.4 组合事件策略（行动仅挂专项）

输入：专项子树的**健康占比周环比**（判定见 §2.3.3）；载荷附带各类问题 count 作解释。

| 周环比 | PRA 缺省安排 | 性质 |
| ------ | ------------ | ---- |
| **恶化** | 提醒专项 owner | 组合提醒 |
| **连续两周恶化** | **升级**：升 GA，请拍板人三选一——**调整项目优先级** / **取消项目** / **开一个整改行动**；落盘后升级项才可核销 | **升级**（组织拍板，≠ Act 的 escalate） |
| **好转** | 表扬专项 owner | 激励 |
| **持平** | 不处理 | — |

升 GA 票上须**写明缺省拟选项**（供超时默认批使用）。**Normative**：超时默认批的缺省**不得为「取消项目」**；**实现默认固定为「开整改行动」**（亦可显式写「调优先级」）；取消须 Owner 在审批时限内**显式选择**。

**与 Act escalate 的区别**：连续两周恶化触发的是组合侧**升级（升 GA）**；单票久催不动触发的是行动侧 **escalate（改 Owner 再派遣）**。二者驱动不同、结果不同，**不是同一条链路**，可并存，文案上勿混称。

---

### 3.5 HITL 与 Mute（v0.2.8 修订）

#### 3.5.1 哪些意图要人类审批

| 意图 | 开票前 HITL（待确认） | 说明 |
| ---- | -------------------- | ---- |
| `praise_owner` | **否** | 发现问题 → 已通知 → 完成 |
| `notify_owner_worsening` | **否** | 发现问题 → 已通知 → 待执行（确认已知晓）→ 完成 |
| `fix_definition` | **否** | 发现问题 → 已通知 → 待执行（补全定义）→ GE 核销 |
| `escalate_owner`（卡住改 Owner） | **否** | 正常升一级负责人；可理解、不敏感；自动生效后再派遣 |
| **`remediate_stage`**（门控/阶段延期） | **是**（受项目 Mute 约束） | v1 开票前审批意图之一 |
| **`remediate_envelope`**（项目包络逾期） | **是**（受项目 Mute 约束） | v1 开票前审批意图之一；**闭环异于 stage**（无报告/PM 核） |
| `escalate_ga` | **是**（后置） | 不可 Mute 躲开；见 §3.4 |

#### 3.5.2 超时整改的审批路径

```text
PRA 拟定缺省安排（仅 remediate_stage / remediate_envelope）
  → 始终 inform（知情不断档）
  → 项目为 Mute（见 §3.5.3）：跳过「等待审批」；仍 inform；立即派遣
  → 项目明确要求审批（非 Mute）：
       · inform 审批 Owner（可批准 / 改派 / 改要求）
       · 等待时限：最多 T+1（Decision.approve_deadline_at）
       · 时限内批准 → 立即派遣；时限到未批 → 按缺省视为已批 → 立即派遣
```

| 规则 | 约定 |
| ---- | ---- |
| **改派 / 改要求** | **仅**在整改开票前的审批窗口（项目非 Mute 时） |
| **整改核对** | **仅 `remediate_stage`**：执行人交付报告后的 **PM 核对** ≠ 开票前审批；**不因 Mute 取消**。**`remediate_envelope` 无此步** |
| **升 GA 与 Mute** | **不可**靠 Mute 躲开升级（后置意图） |

#### 3.5.3 项目级 Mute（缺省即 Mute）

| 规则 | 约定 |
| ---- | ---- |
| **粒度** | **项目级**（每个项目独立设置；**不**做专项级整改 HITL 开关） |
| **缺省** | 库中**没有**该项目的「要审批」记录时，视为 **Mute = 开**（跳过等人批） |
| **Mute 含义（现网 · 开票前）** | **跳过等 Owner 开票前审批**，不是取消事项、不是沉默；**仍要 inform** |
| **Mute 含义（后置 · 代行 HITL）** | 规划模式曾述：Mute=真 → PRA **代替**可代行 HITL 并 inform。**现网**：Mute 仅跳过 **`remediate_*` 开票前**审批；**无**通用代行 review/其它槽位。**`deliver_*` / `notify_phase_complete` 无 HITL**。**硬 HITL 免疫 Mute**：`review_gate`、`review_project`（及升 GA 等 · 升 GA 后置） |
| **显式设置** | 仅当存在 **`require_approval`**（需要人类审批）时，可代行槽位才走等人批；无行=缺省 Mute |
| **存储** | `active_agent` 项目级 **`require_approval`** 记录（有 = 非 Mute；无 = Mute）。**废弃**「有 MuteRule 才跳过」语义。UI：执行力项目设置；权限同项目设置 |
| **v1 不做** | 「临时要审批、到期自动恢复 Mute」的 `until`（后置） |

---

### 3.6 决策意图（粗，行动子系统再细化）

| 意图 | 触发 |
| ---- | ---- |
| `fix_definition` | 单项目定义缺口 |
| **`remediate_stage`** | 同阶段门控逾期 + 阶段窗口逾期（门控延期补救 · §3.3.1） |
| **`remediate_envelope`** | 项目时间包络逾期（起止系统阶段窗口 · 仅改期核销） |
| `deliver_artifact` | **后置** · 一般任务交付（Sense **不** emit；常量/map 保留） |
| `deliver_gate` | **现网** · 绑 GI 任务交付（§4.9） |
| `review_gate` | **现网** · 门控评审（§4.9） |
| `notify_phase_complete` | **现网** · 阶段完成只通知 PM（§4.9；取代原 `review_phase` HITL） |
| `review_project` | **现网** · 结项评审（§4.9） |
| `notify_owner_worsening` | 专项健康占比周环比**恶化** |
| `escalate_ga` | 专项健康占比**连续两周恶化**（**后置** · Sense 可产 `worsened_2w`，Decide **不**映射开票） |
| `praise_owner` | 专项健康占比周环比**好转** |
| `amend_action` | 并入在途项并更新要求（**非**延期主意图） |

**废弃（产品名）**：笼统 intent **`remediate`**。闭环不同，**禁止**再当作单一插件/策略键。

**迁移（已完成 · v0.2.48）**：历史行曾按 concern 写回 `remediate_stage` / `remediate_envelope`。运行时 **无**旧 intent 常量、**无**读时归一、**无** backfill 脚本；库内若仍见 `"remediate"` 视为历史缺陷数据。新开票只写新名。

| 旧值 | concern | 写回为 |
| ---- | ------- | ------ |
| `remediate` | `pra:remediate:stage:…`（或细 `pra:overdue:gate\|stage:…` 并入阶段票） | **`remediate_stage`** |
| `remediate` | `pra:overdue:project:…` | **`remediate_envelope`** |

通道、催销、回执核销 → **§4**。

---

### 3.7 一句话

> v1 **仅 `remediate_stage` / `remediate_envelope`** 可能开票前 HITL；表扬/提醒/定义/卡住改 Owner **不批**。项目级 **缺省 Mute**（无显式设置即跳过等人批），非 Mute 时整改才 T+1 待确认；始终 inform。组合连续两周恶化升 GA 后置；公司目标 v1 不接第一棒。

---

### 3.8 决策实现共识（Accepted · **M2 现网**）

#### 3.8.1 v1 范围

| 进 v1 | 后置（v1.1+） |
| ----- | ------------- |
| 定义 / 超时类事件 → `fix_definition` / `remediate_stage` / `remediate_envelope` | 质量 / 成本事件（待感知字段） |
| 健康占比恶化 → 提醒；好转 → 表扬 | **升 GA**（`worsened_2w`）可同迭代后半段或 v1.1 |
| **仅 `remediate_stage` / `remediate_envelope` HITL**；项目级缺省 Mute；`escalate_owner` 自动升一级 | — |

与感知 v1（§2.5.2）对齐：无事件则无决策。

#### 3.8.2 实体与关系

| 实体 | 职责 |
| ---- | ---- |
| **Decision** | 消费 SenseEvent；记录缺省安排与（若需要）HITL 态 |
| **项目审批/Mute 设置** | 项目级 **`require_approval`**；**无行 = 缺省 Mute**；有行才对 `remediate_stage` / `remediate_envelope` 开待确认 |
| **Action** | 无 HITL 意图：建 Decision 后即可派遣；整改两意图在批准/Mute/T+1 后 open/amend |

关系：

- **1 Decision : 1..n SenseEvent**（同关注可合并）。  
- 同 `concern_key` 已有在途 Decision/Action → **并入/刷新**，不双开。  
- **HITL 态**（仅 `remediate_stage` / `remediate_envelope` 且项目非 Mute）：`pending_approval` → `approved` \| `auto_approved`；Mute/无 HITL 意图可用 `mute_skipped` 或直接进入行动。

#### 3.8.3 调度（主动性）

```text
SenseEvent status=adopted
  → 入决策队列（异步）
  → Harness 映射意图
       → praise / notify / fix_definition / escalate_owner：
            无开票前待确认 → inform → 立即 open/推进 Action
       → remediate_stage / remediate_envelope：
            查项目 Mute（缺省 Mute）→ inform
            Mute → 立即派遣；非 Mute → pending_approval（T+1）→ 批/超时后再派遣
  → worker 扫到期未批（仅非 Mute 的整改两意图）→ auto_approved → 派遣
```

- Decide **不**注册 GE 挂载；只消费 SenseEvent。  
- 对 GE 的写放在 **Action** 路径。  
- 映射见 §3.6（`execution.overdue.gate|stage`→`remediate_stage`；`execution.overdue.project`→`remediate_envelope`）。

#### 3.8.4 Harness

- v1：**代码内策略**（按 `SenseEvent.type` 映射意图）+ 单测。  
- 组合映射：`worsened`→提醒；`improved`→表扬；`worsened_2w`→升 GA（后置）。

#### 3.8.5 Mute

- **项目级缺省 Mute**（§3.5.3）：无显式「要审批」设置 = Mute。  
- 仅约束 **`remediate_stage` / `remediate_envelope` 开票前审批**；不影响表扬/提醒/定义/改 Owner。  
- 升 GA（后置）：**忽略 Mute**。

#### 3.8.6 一句话

> adopted 入队；v1 仅整改可能待确认；项目缺省 Mute；其它意图 inform 后即派遣/核销。

---

## 4. 行动子系统（Accepted）

### 4.1 定位与运行时

Act 从**安排派遣之后**开始：派发 → 报告/回执 → 检查 → 催促 / 改善 → 核销；**不**在催促里偷改使命。久催不动则 **自动升一级 Owner** 再派遣（**escalate**，≠ 组合侧「升级升 GA」；**无**开票前 HITL；见 §4.5 / §4.8）。

| 落点 | 约定 |
| ---- | ---- |
| **主动 Agent 运行时服务** | 承载事件采纳、决策记录、行动项、催促、报告提交、**项目 Mute/审批设置**等；**PRA 为第一个实例** |
| **GE** | 项目 / 阶段 / 门控 / 任务等**域真源**；本服务编排读写真源，**不**替代 GE |
| **Web UI** | 执行力目标树节点 **SDA tab（事件流）**；深链落到对应事件；项目级 Mute/审批设置 |
| **触达** | **复用 PA inform**；正文含深链进 SDA 事件 |

红线：不自动开偏差（含系统节点）；人可对逾期系统门控开偏差建补救任务；不改 PBC；inform **不**冒充系统偏差开单。

---

### 4.2 到位判据（按意图）

| 意图 | 到位 / 核销 |
| ---- | ----------- |
| **定义补齐** | GE 真源满足定义条件（阶段≥3、每阶段门控+产出任务、应有截止日等） |
| **整改** | 见 §4.3 |
| **表扬** | inform **投递成功**（提供方受理成功）即核销；v1 不依赖已读回执 |
| **提醒** | Owner **确认**后核销；未确认保持 open |
| **升 GA · 调优先级** | 拍板人已决策 → inform → **PM 确认** → 核销；优先级信息**暂不写入 GE**（未来 GE 有字段后再落真源） |
| **升 GA · 取消项目** | **GE 取消调用成功** + inform **专项 owner 与 PM** → 核销 |
| **升 GA · 整改** | 同 §4.3；**责任人 = PM**；**Owner = 专项负责人**；**子目标须被 inform（知情）** |

升 GA 票上须**写明缺省拟选项**。**Normative**：超时默认批**不得**缺省为「取消项目」（同 §3.4）。实现分期见 §3.8.1 / §4.8.1。

---

### 4.3 整改闭环（一张票）

```text
派遣整改责任人
  → 责任人在项目根 Note 下创建子 Note 作为报告
  → 在 Act Web（或项目 Web）提交该文档 URL
  → PRA 阅读报告并形成判断（= 给 PM 的辅证，不能代替通过）
  → inform PM 核对（结合线下互动 + 线上文档）
       ├─ 通过 → 核销，行动结束
       └─ 不通过 → inform 责任人；作废本次提交关联（文档痕迹宜保留审计）；票保持 open
```

- **一张票**覆盖「报告 → PM 核对」；实现上可区分 `awaiting_report` / `awaiting_pm_verify`。  
- PM 核对慢：按 §4.5 催当前责任侧；责任人可线下催 PM；**责任人自闭环、自负责**。

---

### 4.4 并入

行动项数据格式可关联**一类问题下的多个事件实例**。  
并入新事件 = 增加关联 + 更新要求 + 再告知执行侧；不另造冲突模型。

---

### 4.5 催促与久催 escalate

> **用词**：本节为行动侧 **escalate**（**自动**升一级 Owner 再派遣，**无 HITL**）。组合侧健康占比连续两周恶化触发的是 **升级（升 GA）**，见 §3.4；二者不是一回事。

1. 派遣时附带**时间要求**（`due_at`，见 §4.8）。  
2. 过点后开始催促：**每天 1 次**。  
3. **3 次仍无回执** → 久催不动：

```text
该行动标记 stalled
  → 按 escalation 阶梯，从「当前 Owner 所在档」再升一格，选定新 Owner
  → 同一 Action 更新 owner；催促计数清零；re-dispatch
  → 默认不改 executor（除非缺省安排/开票前改派已指定）
  → 不建待批 Decision；timeline 记「已升级负责人」+ inform 新/旧侧  
  → 升不动：仍记「已升级负责人」，括号 **`升不动，仍为` + `{owner}`（独立 who）**（见 §4.8.6 / 步骤呈现共识）
```

#### 4.5.1 Owner 升级阶梯（Normative）

```text
PM → 所归属专项 owner → 所归属子目标 owner → 所归属目标 owner → 评审员
```

| 规则 | 约定 |
| ---- | ---- |
| **爬法** | 从**当前 Owner 在链上的位置**再升 **一格**（不每次从 PM 重来） |
| **整改缺省** | 开票时 Owner 多为 **PM** → 第一次 escalate → **专项 owner** |
| **归属** | 「所归属」按 GE 树：项目 ⊂ 专项 ⊂ 子目标 ⊂ 目标 |
| **executor** | 默认**不换**；只换 Owner（追责/核对侧） |
| **评审员** | 末端：配置列表 / 平台评审员角色，取稳定一人（如列表首个）并 inform |
| **到顶** | 当前已是评审员仍 stalled → **不再**自动 escalate；保持卡住（停自动升；是否继续催另定，v1 可停催或低频） |
| **留痕** | timeline + inform；**禁止**再开 escalate HITL |

升 GA 拍板类（后置）不走本阶梯，见 §3.4 / §4.8.1。

---

### 4.6 与决策 HITL 的衔接

- **无 HITL 意图**（定义/提醒/表扬/改 Owner）：Decision 记录后即可派遣或核销。  
- **`remediate_stage` / `remediate_envelope`**：仅当项目**非 Mute** 时待确认（T+1）；Mute 或缺省 Mute → inform 后立即派遣。  
- **stalled escalate**：**不**再开审批；按 §4.5 自动升一级。

深链：执行力 **SDA 事件流**中的对应事件（见 §4.8.6）。

---

### 4.7 一句话

> 行动态在主动 Agent 运行时；inform + 深链进 SDA；按意图核销；过期催×3 → stalled → **自动**改 Owner 再派遣（≠ 升 GA）；开票前 HITL 仅非 Mute 的超时整改。

---

### 4.8 行动实现共识（Accepted · **M3 现网**）

#### 4.8.1 v1 范围

| 进 v1 | 后置 |
| ----- | ---- |
| `fix_definition` / `remediate_stage` / `remediate_envelope` / 提醒 / 表扬 | 升 GA 三类 Action（随决策 v1.1） |
| 催促、stalled→**自动** escalate_owner、报告/核对、确认 | 质量/成本专路径 |

与 §2.5.2 / §3.8.1 对齐。

#### 4.8.2 状态机（最小）

| 状态 | 含义 |
| ---- | ---- |
| `dispatched` | 已派，等待执行侧 |
| `awaiting_report` | 定义/整改：等报告或推进真源 |
| `awaiting_confirm` | 提醒：等 Owner 确认 |
| `awaiting_pm_verify` | 整改：报告已交，等 PM 核对 |
| `done` | 已核销 |
| `stalled` | 日催×3 无有效回执 |

表扬：`dispatched` → inform 投递成功 → `done`（可不经中间态）。

#### 4.8.3 due 与催促调度

- **`due_at`**：Action 派遣时写入（整改两意图若经审批窗可改；其它意图用模板默认）。  
- **催促 job**（与决策审批超时扫分离）：`now > due_at` 且非 `done` → 每日 inform 催一次；满 3 次 → `stalled` → §4.5 自动升一级。  
- 提醒未确认：同样计入日催与 stalled。

#### 4.8.4 整改报告与辅证

- 提交报告 URL 的 API 在 **`active_agent`**（Action 执行页）。  
- PRA 辅证：**异步 job**；失败/超时仍进入 `awaiting_pm_verify`，标注辅证不可用。  
- PM 驳回：**仅作废本次提交关联**；子 Note **保留**审计痕迹（Normative）。  
- 定义类核销前：**再读 GE** 校验定义条件（防快照过期假闭环）。

#### 4.8.5 表扬 / 提醒

- **表扬**：PA inform **受理成功**即 `done`；v1 不依赖已读。  
- **提醒**：执行页「确认」→ `done`；未确认走催促/stalled。

#### 4.8.6 深链与页面（SDA 事件流）

主表面：执行力 **Project Panel**（进化 SDA **单栏事件流**；废三 Tab）。  
挂载节点：**项目**与**专项**；目标 / 子目标 v1 **不做**完整事件流。  
深链：落到 `/execution/...?event={stream_key}`（**不**用 `/me/active-agent`）；旧 `?tab=sda` 由 FE replace。  
事件身份：**不可变 `stream_key`**（如 `sda:{ulid}`），在 Decision 创建（或首条 timeline）时生成；批准成 Action、升级 Owner **均不改键**。`decision_id` / `action_id` 仅为关联字段。  
可见性：与执行力「能打开该节点」同一 ACL；无权限则空列表（与详情进入方式一致）。项目级 Mute/审批设置见 §3.5.3。

##### 分层硬纪律（Normative）

> **SDA：UI 与深链属执行力表面；领域 API 与投影属 `active_agent`；skstudio 仅 BFF；GE 不承载 PRA 票务。**

| 层 | 归属 | 说明 |
| -- | ---- | ---- |
| **UI / 路由 / 深链** | 执行力（skstudio `/execution/...`） | Panel 事件流、筛选、卡片渲染；人感知为「项目树上的事」 |
| **领域 API / 投影 / 时间线日志 / 状态机** | **`active_agent`** | Decision / Action / Mute / SDA 读模型 / timeline append |
| **胶水** | skstudio BFF | 浏览器只经 `/api/v1/active-agent/*`；节点 ACL、补 scope 显示名 |
| **项目图真源** | GE | 树、可见性、核销读/约定写挂载；**不**实现 SDA JSON 或 PRA 票库 |

```text
用户 → /execution/...?event=…
         → BFF /api/v1/active-agent/sda/…
              → active_agent（投影 · 写 API · timeline）
         → 树 / 项目名 / 能否打开节点 → GE
```

实现契约（投影 JSON、徽章映射、timeline 字段、深链 id）见 [PRA-实现与测试.md](./PRA-实现与测试.md) **§ SDA**。

##### 筛选（按进程）

`待审批 | 待执行 | 已完成 | 全部`

| 筛选项 | 含义 |
| ------ | ---- |
| **待审批** | 开票前等人批（v1 **仅**非 Mute 的超时整改） |
| **待执行** | 已开票/已派遣，等人做（交报告、确认、补定义、PM 核对等） |
| **已完成** | 已核销 |
| **全部** | 不过滤进程 |

##### 事件卡片 · 标题行

同一行、行内小徽章（不单独成大块状态区）：

```text
[进程][类型]  项目或专项：具体问题
```

| 维度 | 取值 |
| ---- | ---- |
| **进程** | 待审批 / 待执行 / 已完成 |
| **类型** | 表扬 / 提醒 / 延迟 / 卡住 / 定义 / **交付** / **评审** |
| **标题** | `对象：具体问题`（可读事实；禁止泛称） |

| 类型徽章 | 典型意图 / 时机 |
| -------- | ---------------- |
| **表扬** | `praise_owner` |
| **提醒** | `notify_owner_worsening`（及阶段完成 `notify_phase_complete` 的展示归类） |
| **延迟** | `remediate_stage` / `remediate_envelope`（含 stage 票 PM 驳回后重交；类型**仍为延迟**） |
| **卡住** | 行动进入 **stalled 起**即标卡住（不必等升级完成）；其后可含自动 `escalate_owner` |
| **定义** | `fix_definition` |
| **交付** | `deliver_gate`（推进 · §4.9；`deliver_artifact` **后置**不新开票） |
| **评审** | `review_gate` / `review_project`（推进 · §4.9） |

治理类徽章见上表；**推进类**细则（CTA、核销、就绪集）见 **§4.9**。与 `sda.TYPE_LABELS` 对齐。

**Normative**：升 GA（组合侧升级，§3.4）与卡住改 Owner **不得**共用同一类型徽章。

##### 时间线纪律

- **竖排**时间线。  
- **每步恰好一行**（步骤内禁止多行说明）。  
- 句式：`通用步骤（具体人 / 时 / 事）`；**事**含事态（`what`）与因果（`why`）。实现用**槽位 + 步骤模板**，见 [PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md)（**§4.0：人只进 who，禁嵌 act/behalf**；补丁 [分槽迭代](./PRA-SDA步骤呈现分槽迭代.md)）。  
- 当前待办步可同行挂 **一个或多个** CTA（按意图与态，见 §4.8.6.2）。  
- 驳回、催促、升级等**留在同事件时间线**，不另开一条事件冒充履历。  
- **存储（Normative）**：写路径 **append** 轻量时间线日志（`active_agent`）；SDA `steps[]` **以日志为准**；当前 Action/Decision 态只驱动进程徽章与 CTA。禁止前端用现状字段「猜」完整履历（存量缺字段仅允许**命名清晰的 legacy 投影回退**）。  
- **卡头进度摘要**：与时间线**末步**同文（`label` + `detail`），不得只回显步骤名而丢掉括号。

##### 通用步骤名（展示用中文；可扩展）

| 通用步骤 | 何时出现 | 括号（Normative） |
| -------- | -------- | ----------------- |
| **发现问题** | PRA 生成安排 / 开票起点 | **问题说明**（单缺口具体问题；定义聚合 `定义缺口 ×N`）+ 时间；落 `discovered.payload.problem` |
| **待确认** | **仅** `remediate_stage` / `remediate_envelope` 且项目**非 Mute** | 待批人 + 时间 |
| **mute模式下跳过人类审批** | 项目 Mute（含缺省 Mute）跳过开票前审批 | **pra代替{本应审批的 Owner}** + 时间 |
| **已通知** | inform 投递成功 | **通知对象** + 时间 |
| **待执行** | 等人做事 | **做什么**（延迟可用角色短语）+ 谁（若需要）+ 时间 |
| **已改派执行人** | Owner 改派 Executor | **旧→新** Executor + 时间 |
| **催促** | 过点催促 | **第 N 次** + **被催人**（= inform 对象）+ 时间；payload 必含 `n` + `user_ids` |
| **驳回** | PM 核对驳回 | **原因** + 驳回人 + 时间；子 Note 审计保留（§4.8.4） |
| **已升级负责人** | stalled → **自动** escalate_owner | **升成**：旧→新 Owner；**升不动**（阶梯到顶）：保留本步骤名，括号 **`升不动，仍为` + owner（who）** + 时间；**不**另造 step_key |
| **完成** | 核销 | 核销人 + 时间（不可只留时间） |
| **已取消** | cancel 票 | **原因**（如 `blocked_by_definition`）+ 时间 |

原则：步骤名通用、稳定；人/时/事(因)只进括号。槽位表与写契约见步骤呈现共识。

##### 与 HITL / Mute 对齐（UI 必须反映）

| 规则 | UI 表现 |
| ---- | ------ |
| 开票前 HITL **仅**非 Mute 的 `remediate_stage` / `remediate_envelope` | 仅此类出现「待确认」+ 进程「待审批」 |
| 项目**缺省 Mute** | 写「mute模式下跳过人类审批」；**不出现**「待确认」 |
| Mute ≠ 沉默 | 仍有「已通知」 |
| PM 核对 ≠ 开票前审批 | 进程「待执行」；CTA 为通过/驳回，不是「批准开票」 |
| `escalate_owner` **无** Decision 待批 | 卡住链路**没有**「待确认」；直接「已升级负责人」 |
| 表扬 / 提醒 / 定义 | 无开票前「待确认」 |

##### 4.8.6.1 样例（验收）

紧凑时间线；实现验收以步骤序列与徽章为准。

**A. 非 Mute · 待批整改** — `[待审批][延迟]`  
发现问题 → **待确认**（+ 批准 / 改派 / 改要求）

**B. 缺省 Mute · `remediate_stage`（报告前置未满足）** — `[待执行][延迟]`（`pra:remediate:stage:…`）  
发现问题 → mute模式下跳过人类审批 → 已通知 → **待执行（待 PM 去补救）**（primary 仅 `nav_delay`；括号角色叙事）

**B′. 缺省 Mute · `remediate_stage`（写报告）** — `[待执行][延迟]`  
报告前置已满足（补救任务已建且日历不逾期）→（无 Note 则**懒建**）→ **待{executor}写报告 / 提交** → PM

**B″. 缺省 Mute · `remediate_envelope`** — `[待执行][延迟]`（`pra:overdue:project:…`）  
发现问题 → 已通知 → **待执行（去调整阶段窗口）**；窗口已不逾期后 → **已改期，请核销**（**不**走整改报告 / PM）

**C. 已交报告 · 待 PM 核** — `[待执行][延迟]`（`remediate_stage`）  
… → 待执行（已提交）→ 已通知(PM) → **待执行（待 PM 核对）** + 通过/驳回

**D. 被驳回 · 再补救（同构）** — `[待执行][延迟]`（阶段聚合票）  
… → **驳回（…）** → **待执行（PM 重计划 / 责任人改报告再提交）**（同 §3.3.1；类型仍为延迟；**无**「延期修订」旁路）

**E. 催×3 · 卡住升级** — `[待执行][卡住]`（自 stalled 起）  
… → 催促（第1次，{被催人}）→ … → 催促（第3次，{被催人}）→ **已升级负责人（旧→新）** → 已通知(新 Owner) → **待执行（继续整改）**（无「待确认」）。若升不动：末步为 **已升级负责人（升不动，仍为，{owner}）**，其后**无**已通知/再派遣。

**F. 表扬（对照）** — `[已完成][表扬]`  
发现问题 → 已通知 → 完成

**标题**：由 `active_agent` 投影生成（`对象：具体问题`；模板 + evidence；缺名时投影/UI 补 scope 显示名）；前端不用 intent 英文名拼标题。

##### 4.8.6.2 执行 CTA（按意图 · Normative）

执行环节必须给人**下手处**；**禁止**所有事件共用「提交报告」。

| 类型 / 意图 | 待办态 | CTA | 说明 |
| ----------- | ------ | --- | ---- |
| **定义** `fix_definition` | 待执行 · 仍有缺口 | **去补全定义**（primary · 深链 `?tab=define&issue=definition` + `phase` / `focus-gate`；Canvas 红 `!`） | **不**投影「已补齐，请核销」；**不**走整改报告；**不**打开项目设置；写挂载可刷新 gaps |
| **定义** | 待执行 · gaps 已空 | （系统应已 cancel；竞态窗口可短暂见）**去复查定义** | **空 gaps → `reconcile` cancel**（`reconcile_gaps_empty`）；**不**要求人点核销才清票；人核销仍可用于竞态/审计 |
| **`remediate_stage`** | 待审批（非 Mute） | **批准**（PM） | Mute 无此步 |
| **`remediate_stage`** `pra:remediate:stage:…` | 待执行 · 报告前置未满足 | **去补救**（primary · `nav_delay` · `?tab=define&issue=delay` + `phase` / `focus-gate`） | Canvas：**定合理时间 → 建补救任务**；仅改日历不够；**无**「已改期，请核销」 |
| **`remediate_stage`** | 待执行 · 报告前置已满足 · 写报告 | **写整改报告** / **提交整改报告**（primary）· **去复查计划**（`nav_delay` 辅） | 无 Note → **懒建**后打开；叙事在 Note；关票 = 报告提交 + PM；**离开延迟办事态 → 系统 cancel**（INV-3 · 办事态谓词；半截偏差不杀） |
| **`remediate_stage`** | 待执行 · PM 核对 | **通过** / **驳回** | 通过 → `done`；驳回 → 同构再补救（§3.3.1） |
| **`remediate_envelope`** `pra:overdue:project:…` | 待执行 · 窗口仍逾期 | **去调整阶段窗口**（primary · `nav_delay`） | **禁止**整改报告 / PM；改期后系统 cancel |
| **`remediate_envelope`** | （窗口已不逾期） | — | **自动 cancel**（`reconcile_schedule_cleared`）；废「已改期，请核销」为主关票路径 |
| **卡住** | 待执行 | **无新要求 UI**；自动升 Owner 后沿用整改 CTA | 不另开 escalate HITL |
| **提醒** | 待执行 | **确认已知晓**（现有） | 不新开大 UI |
| **表扬** | 已完成 | **无 CTA** | inform 即完成 |

投影字段：`ctas[]`（`kind` / `label` / `primary` / 可选 `href`）；`cta` 为 primary 兼容项。

**v1 刻意不做**：不以「我的 / 主动 Agent」列表替代 SDA 主表面；标题行不用大块状态区；步骤不拆成多行卡片文案；GE 内不实现 SDA/PRA API；目标层完整事件流。

#### 4.8.7 与 GE

- Act **可读** GE 做核销校验；**写** GE（如取消项目）仅相关 Action 执行路径。  
- Decide 不订挂载。  
- SDA **不**由 GE 提供列表/步骤 API（见 §4.8.6 分层纪律）。

#### 4.8.8 一句话

> SDA 在执行力表面展示、在 active_agent 投影与记履历；催促独立 job；整改辅证+PM 终核；stalled **自动**升 Owner；开票前 HITL 仅非 Mute 整改；v1 不做升 GA Action。

---

### 4.9 项目推进 Action（现网 · v0.2.51）

**状态**：**现网**（软缺口：GE 延迟转段 / E2E 全量 · 见 [PRA-实现与测试](./PRA-实现与测试.md)）。域侧对齐 [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) **§4.9（v2.38.65）**。  
**切换日已落地**（无双轨）：执行力右区 = Project Panel；旧 `?tab=` FE replace。

#### 4.9.1 定位

Sense–Decide–Act 上用推进意图端到端推动项目。**1 Task ↔ 1 `deliver_gate`（现网）**；`deliver_artifact` **后置**（Sense 不 emit）。多步 = 多 Action + **produce/prereq 就绪集**；临时交换在项目 Note。门控 / 结项有硬 `review_*`；**阶段完成 = 通知**（`notify_phase_complete`），不再二次通过/驳回。主表面 **Project Panel**（UI 见 §4.9.4 / GE §4.9.7）；阶段协同见 GE **§4.9.8**。

#### 4.9.2 意图 · 创建时机（现网）

| 意图 | HITL | Mute | 创建/激活 |
| ---- | ---- | ---- | -------- |
| `deliver_gate`（1:1 GI） | **无**；提交后 inform PM+项目团队 | — | 任务入 **就绪集**且 GI 非 schedule-overdue；偏差态须已有补救任务 |
| `deliver_artifact` | — | — | **后置**（不新开票） |
| `review_gate`（PM） | **硬**（Action `awaiting_review`，非开票前 Decision） | **免疫** | GI **首次提交后** |
| `notify_phase_complete`（PM） | **无**；只 inform | — | 本阶段全部 GI **已签**（GE 可已结段） |
| `review_project`（专项 owner / 阶梯上收 · **不含 PMBP · M41**） | **硬** | **免疫** | 结项条件就绪后 |

判据、主链、驳回=整改、逾期取消原票：GE §4.9.4–§4.9.6（**阶段完成通知**现网修订见同节）。Mute 见 §3.5.3。就绪集：GE §4.9.8。

**M41 · 拍板链（Normative · 现网）**：`review_project` 审批槽 **仍** 专项 `owner_user_id`（阶梯上收子目标/公司 owner）· **不含** effective PMBP · 细则 [M41](./目标与执行-项目管理BP迭代.md) **v0.2.0** · 测 **PRA-PMBP-01**。

**Cancel 作用域（Normative · v0.2.51）**：

| 触发 | cancel 范围 |
| ---- | ----------- |
| 逾期 / 偏差激活 | 按 **门控** 或 **阶段**（项目包络逾期才整项目） |
| `review_gate` **驳回** | **仅该 `gate_id`** 未终态 `deliver_*` / `review_*`（再 rescan 开补救侧 deliver） |
| `review_project` **驳回** | **整项目** 未终态推进票 |

#### 4.9.3 Sense / Decide / Act

| 环 | 例 |
| -- | -- |
| Sense | **就绪未交**、等前置文档（不刷存在感票）、已交待审、待 review、结项就绪、整改取消原票等 |
| Decide | 派给谁（人\|Agent）、是否 Mute（可代行档）、是否催、是否开整改 |
| Act | inform、代行可代行 HITL、催促、驳回→整改、通过后写 GE |

#### 4.9.4 UI：Project Panel + 定义侧矩阵（摘要 · v0.2.44 · **进展成果 v0.2.68**）

| 项 | 约定 |
| -- | ---- |
| **App 壳** | 执行力 **左目标树 + 右项目区**；点项目 → 右区即 Panel（**无** Panel 内回树） |
| **布局** | 右区 = **筛选条 → 可折「项目进展」表 → 单栏 SDA 事件流**；**无** Panel 内左右分栏办事面 |
| **流上优先** | 能流上完成的不强制弹窗；弹窗 **必须**有卡上明确 CTA 入口 |
| **弹窗 / 链出** | 仅装不下的表单/材料 → 弹窗；定义/去补救/改包络 → 链出 |
| **进展（知情）** | **团队知情**（非状态机）；卡上短状态；人 **不强制日报**；有日报写 **项目 Note**；卡上**可链**、**不摘摘要** |
| **项目进展表（v0.2.68）** | 见下表 **Normative** |
| **待我处理** | 待交 / 待审（硬 HITL Mute 仍计）/ 治理可点 CTA；详见 GE |
| **进入落点** | 待我处理→高亮（待审优先，**默认不**自动弹窗）；仅进行中→高亮；皆无→定义 |
| **定义往返** | 顶栏链出 Canvas；「回项目」→Panel 流并重算落点 |
| **阶段协同** | Canvas **任务卡片** + 拖线 produce/prereq；创建任务可选产出/依赖 GI；**无**依赖矩阵弹窗；空前置=起点；临时交换在项目 Note；真源 produce/prereq |
| **复用** | 现 SDA 卡 / `ctas[]` / 深链 / timeline；**无**独立 SDA Tab 名（Panel 吞流） |
| **废弃** | 三 Tab；Panel 内左右分栏；强制弹窗；旧 `remediate` 名；旧 `?tab=` replace；任务区依赖轮廓简图；**依赖矩阵三列表弹窗**；**N×N 方阵作主编辑**；成果列展示 `kb:uuid` |

**项目进展表 · 成果列（Normative · v0.2.68 · 对齐 GE 证据层）**

| 项 | 约定 |
| -- | ---- |
| **位置 / 显隐** | 筛选条与 SDA 之间；checkbox「项目进展」缺省勾选；改后 `localStorage`；define 不展示 |
| **列** | 阶段 / 任务 / 成果；数据主读 GE `graph`；多 produces **分行** |
| **材料何时显** | 仅 GI 已提交（`pending_sign` \| `signed` \| `rejected` \| `deviation`）**且**有 `content_ref`；未提交 **不**画材料行 |
| **三类 form** | **material**：材料一等（标题可点）；**status / metric**：判定文案主读，材料行附属 |
| **文案层次** | ① Note **标题**可点（打开本项材料同路径）② `summary` **永远次行**（防与材料混淆）③ **禁止**展示 `kb:uuid` |
| **标题解析** | 项目 Note 树批量 `id→title` **优先**；树缺失 → **`GET …/kbase/notes/by-id/{uuid}` 兜底**；同 noteId **去重**；403 不泄 title；仍失败 →「材料（标题暂不可用）」 |
| **线框** | `project-progress-outcome-material-wireframe.canvas.tsx`（成果材料）；表壳仍见 `project-progress-summary-wireframe.canvas.tsx` |

按意图 UI：GE §4.9.7。协同细则：GE §4.9.8。线框：App 壳 `project-panel-app-shell.canvas.tsx` · 按意图 `project-panel-wireframe.canvas.tsx` · **Panel 空态** `sda-sync-execution-state-wireframe.canvas.tsx`。

**Panel 空态 · 同步推进事项（Normative · v0.2.90 · 规划 · 链 GE §4.9.10）**

| 项 | 约定 |
| -- | ---- |
| **场景** | 进展表有内容 · SDA 列表为空（典型 stuck phase 未转段） |
| **位置** | 进展表 **正下方** · `execution-detail-meta` 位置感 · **非** 列表 footer |
| **治理者** | `暂无推进事项，让项目管理智能体` + **`主动同步推进事项`** |
| **参与者** | `暂无推进事项，项目经理可以让项目管理智能体主动同步推进事项` |
| **行为** | GE heal + BFF `sync-execution-state` + AA rescan；详见 GE §4.9.10 · 《实现》§10.51 · [迭代](./目标与执行-Panel空态同步推进事项迭代.md) |

#### 4.9.5 一句话

> produce/prereq 定就绪集；只对就绪集 deliver；review 放行；Panel 流上办事 → 项目由 PRA 推动跑完。

---

### 4.10 专项看板（Program Board · Normative · v0.2.66 · **现网**）

在**专项（Program）**详情增加 Tab **「看板」**：看子树项目**分布**，再**下钻**到列表并进 Project Panel。与项目内 SDA 办事流（§3.3.0 / §4.9.4）互补——看板**分类与跳转**，**不**在专项页代办定义/补救。

#### 4.10.1 表面结构

| 块 | 约定 |
| -- | ---- |
| **分布** | **圆环图**；四类占比 + 绝对数；图例单行 **`类名(n)`**（扁平行，与 §4.11/§4.12 同构）；**布局 = 环左 · 图例右**（与公司目标看板「环上 · 图例下」刻意不同） |
| **项目列表** | 点环上某一类 → 列表只显示该类；点行 → 进该项目 **Project Panel**（可带优票据深链） |
| **Tab** | 专项详情内 **「看板」**；能打开该专项的 ACL 不变；**环与列表只含当前 Actor 可见项目**（与 GE `GET /programs/{id}.projects[]` / `filter_projects_for_user` 同口径；**不是**专项 owner / 评审员全量视角，除非 Actor 本身是评审员或子树 governor） |

#### 4.10.2 四类互斥分类（进环集合）

**进环项目集合**：**当前 Actor 可见**的专项下项目，且 `lifecycle_status` **不是** `cancelled` / `archived`（及 GE 现网等价「取消/归档」）。**取消、归档不进环、不进列表。**

对进环集合，每项目恰好落入一类（优先级自上而下）：

| 类 | 判定 |
| -- | ---- |
| **定义** | 有开放 `fix_definition` |
| **延迟** | **无**开放定义，且（有开放 `remediate_stage` / `remediate_envelope` **或** 物化 `project_work_state ∈ DELAY_*`）；与 [办事态机共识 §4.4](./PRA-项目办事态机共识.md) 同源（含半截无票 · WS-T07） |
| **进行中** | **无**开放定义、**无**开放延迟（含无 `in_delay` 缓存），且未完成（`lifecycle_status` 为 active 等非 completed） |
| **已完成** | GE `lifecycle_status` = **completed**（或现网等价「完成」） |

**Normative**：

- 有定义 + 有延迟 → **只进定义**（与 §3.3.0 L1 一致）。  
- 「进行中」**不**因存在开放 deliver/review/notify 而改类。  
- 「已完成」看 **lifecycle**，不看「有没有票」。  
- 环上四段之和 = 进环项目数；可显示 0 段。

#### 4.10.3 交互与默认

| 项 | 约定 |
| -- | ---- |
| 点环段 | 列表过滤为该类；**无「全部」筛**（本 Tab 不做四类并集浏览） |
| 默认选中 | 有定义项目 → **定义**；否则有延迟 → **延迟**；否则有进行中 → **进行中**；否则 **已完成**（环上第一非空类） |
| 列表字段 | **项目名** · **类标签** · **PM**；点行 → 该项目 Project Panel |
| 进专项默认 Tab | **看板**（本 Tab） |
| 空态 | 进环为空：环与列表空文案；某类为 0：该段可展示为 0，选中则列表空 |
| 刷新 | 进页拉取；从项目 Panel 返回专项看板宜刷新分布 |

#### 4.10.4 数据与分层

| 层 | 职责 |
| -- | ---- |
| **GE** | 专项下**对当前 Actor 可见**的项目集合、`lifecycle_status`、显示名 / PM（`filter_projects_for_user`）；`GET /programs/{id}` **入口软过滤**（无 governor 硬 403 整板） |
| **`active_agent`** | 透传 Actor（含真实 `is_reviewer`，**禁止**抬权）；按可见项目聚合开放票意图 + 读 **`project_work_state_cache.in_delay`**（**scan 时写入**，见 [BOARD-CACHE](./PRA-目标看板work_state缓存迭代.md)）；四类标签与 count；**看板读错误透传**（v0.2.75：GE 4xx/5xx **禁止**折成 `not_found`；与 §4.11 同波 **已齐**）；**禁止**看板读路径 per-project `load_scan_bundle` |
| **skstudio** | 专项详情 Tab UI；BFF 拼装；**不**本地另算健康分 |

看板**不**改票、**不**代替 Sense/Decide；分类读开放票、lifecycle 与 **物化办事态**（非读时现算 graph）。

#### 4.10.5 刻意不做（本波）

- 质量 / 成本第五类；组合健康环比进环（仍走 §3.4 提醒/表扬）  
- 看板内改期、补定义、补救（深链出项目 Panel）  
- 公司目标级看板 → **见 §4.12（现网）**

---

### 4.11 子目标看板（Sub-Objective Board · Normative · v0.2.76 · **现网**；ACL/错误码 **已关**）

在**子目标**（`Objective.level=sub`）详情增加 Tab **「看板」**：同一排两个环——左看**专项分布**、右看**项目分布**（与 §4.10 四桶同构；对齐专项看板「分布」主语=项目），再下钻项目列表。子目标下**只挂专项**（无嵌套子目标）。看板**分类与跳转**，**不**代办定义/补救，**不**开组合 inform / 提醒 / 表扬（组合行动仍只挂专项 · §3.2）。

#### 4.11.1 范围与门禁

| 项 | 约定 |
| -- | ---- |
| **进** | 仅 `level=sub`；进子目标详情默认 Tab = **看板** |
| **company** | 公司目标看板见 **§4.12**（同一 `board` / `board-projects` 路径按 `level` 分支；**禁止**再把 company 当成「子目标 board 拒绝」） |
| **结构前提** | 子目标下直属仅为 Program；**无**下级子目标 |
| **入口 ACL（Normative · v0.2.73）** | 与专项 `GET /programs/{id}` **同构软过滤**：**不**因「非子树 governor」对整板硬 **403**。目标存在且 `level=sub` → **200**；`programs[]` 仍返直属全量（含空专项）；`projects[]` **仅** `filter_projects_for_user` 可见切片。无可见进环项目 → 走 §4.11.4「可见范围空」空态，**禁止**伪装成加载失败。 |
| **深链 / 真 stranger（Normative · v0.2.74）** | 任意持链 Actor（含树外、零参与）：目标存在且 sub → **仍 200**；切片为空 → **可见范围空**。**禁止**为 stranger 另加整板硬拒（否则重开「壳能开 / API 硬失败」裂缝）。树「所参与」仅为 UI 过滤，不改变本条。 |
| **与人员 Tab 边界（Normative · v0.2.74）** | 目标详情 **不再**挂人员 Tab。专项 / 项目 `people-summary` 仍 governor（或 project can_read）硬门；看板软过滤与人员硬门 **刻意不对称**（专项侧仍适用）。 |
| **错误码（Normative · v0.2.73–74）** | 目标不存在 → **404**；非 `sub`/`company` → **400**；传输/上游故障 → **5xx**。**禁止**把过滤空结果折叠成 `not_found`。AA/BFF 对**看板读**（objective board + 专项 board）**原样透传** GE 状态族；FE **禁止**对 4xx 自动重试；文案区分可见范围空 / 不存在 / 服务异常 / 人员无权限（403）。 |
| **刻意不做（ACL）** | **不**把详情页收成 governor-only；**不**用抬 `is_reviewer` 绕过过滤；**不**随看板软开 `people-summary`；**不**为 stranger 深链加整板 403。 |

#### 4.11.2 表面结构（同一排双环 + 列表）

| 块 | 约定 |
| -- | ---- |
| **布局** | 每个分布块 **环左 · 图例右**（与 §4.10 同；与公司目标 §4.12「环上 · 图例下」不同） |
| **左 · 专项分布** | **圆环 + 图例**（与右同构「分布图」）；每段 = 一个直属专项；**段长 = 该专项进环项目总数**（四桶之和）；**排序 = 定义数+延迟数降序**（同分跟结构序 / 名称） |
| **左 · 图例行** | 单行：`专项名(total)`（色块 · 名称(n)）；**无**「定义·延迟」次行 |
| **右 · 项目分布** | 与 §4.10 **同构**四桶环 + 图例；图例单行 `类名(n)`；scope = 左环当前选中专项，**未选中 = 全部直属专项上卷** |
| **项目列表** | 由右环当前桶过滤；**真表**列：**项目 · 类 · 所属专项 · PM**；点项目名 → 该项目所属 **专项看板**（`/execution/programs/{id}?tab=board`） |
| **可见性** | 环与列表只含**当前 Actor 可见**项目（与 GE `filter_projects_for_user` 同口径；**禁止** AA reviewer 抬权）。入口软过滤见 §4.11.1——能打开详情壳的 Actor 应能打开看板 Tab，看到的是**自己的切片**（可空），而非整板失败。 |

**段长 vs 排序（Normative）**：段长用四桶 `total`，保证「无定义/延迟但仍有进行中/已完成」的专项留在环上；排序用定义+延迟，保证救火入口沉顶。二者刻意不同；图例只标 `名称(n)`（n=段长），**不**用次行再拆定义/延迟。

#### 4.11.3 交互与 URL 状态机（Normative）

```
点左环段 / 图例某专项
  → 右环 = 该专项项目分布（四桶；标签可示专项名）
    → 点右环段
      → 列表 = 该专项 × 该桶
点左环中心数字
  → 清除专项选中 → 右环回上卷 → 桶按上卷 default 重算
```

| 项 | 约定 |
| -- | ---- |
| 右环选桶 | 与 §4.10 相同：**无「全部」筛**；默认第一非空桶（定义→延迟→进行中→已完成） |
| 切左环专项 | **必须重置**右环桶为该 scope 的 `default_bucket`（禁止沿用上一专项的桶，以免空列表误判为故障） |
| 回上卷入口 | **仅**点左环中心 |
| `total=0` 专项 | 进环项目为 0 → **不进左环弧、不进左图例**（结构 Tab 仍可见；看板只承接有进环项目的专项） |
| **URL 为真相** | `?tab=board&program=&bucket=`；点选/清选均写回；分享与刷新可恢复 |
| 非法 `program` | 不在当前 `programs[]`（已删或不可见）→ **视为未选**（上卷），不白屏 |
| 刷新 | 进页拉取；从专项看板 / 项目 Panel **返回必须 refetch**；若 refetch 后该 `program` 仍在则保持选中 |

#### 4.11.4 空态（三分，禁止共用一句「暂无数据」）

| 情况 | 文案方向（Normative 意图） | 动作 |
| ---- | -------------------------- | ---- |
| 直属专项数 = 0 | 本子目标下还没有专项 | 链到 **结构** Tab |
| **有专项但上卷进环项目 = 0**（含 Actor 可见切片为空、真 stranger 深链） | 当前可见范围内没有计入看板的项目（取消/归档不显示） | 可选链结构查看专项；**不**谎称「没有专项」；**不**报加载失败 |
| 已选专项或已选桶但列表空 | 该类暂无项目 | 与 §4.10 同类短句 |

#### 4.11.5 四桶、进环排除与合计不变量

- **打桶语义**：与 §4.10.2 **完全相同**（实现须**复用**同一套 `bucket_for_project` / `default_bucket`，禁止分叉）。  
- **职责切分（Normative）**：  
  - **GE**：只做 Actor **可见性**；`board-projects` **保留** `lifecycle_status`（含 cancelled/archived），**不**在 GE 预剔除进环排除集。  
  - **AA**：按 §4.10 排除 cancelled/archived，再打桶、聚合。  
- **合计不变量（Normative）**：AA 响应须满足  
  `sum(programs[].total) == sum(counts.*) == len(items)`  
  （`programs[]` 仅含 `total>0` 的专项。）

#### 4.11.6 数据与分层

| 层 | 职责 |
| -- | ---- |
| **GE** | `GET /ge/objectives/{id}/board-projects`：`level=sub` 分支；**入口软过滤**（§4.11.1）；直属 `programs[]`（含空专项）+ Actor 可见 `projects[]`（含 lifecycle / `program_id`）；**一次返回**（`level=company` 见 §4.12） |
| **`active_agent`** | `GET …/objectives/{id}/board`：透传 Actor（真实 `is_reviewer`，**禁止**抬权）；**看板读错误透传**（与 §4.10 专项 board **同波**）；排除进环；复用打桶 + **`project_work_state_cache`**（§4.10.4）；聚合左环 `programs[]` + `items[]` + 上卷 `counts`；守合计不变量 |
| **skstudio** | 子目标看板 Tab；BFF；共享 Ring + 单行图例 `名称(n)`；真表列表；URL 状态机；三分空态；4xx **不重试**；**不**本地另算健康分 |

看板**不**改票、**不**代替 Sense/Decide；**不**在子目标看板触发组合提醒/表扬/升 GA。

#### 4.11.7 刻意不做（本波）

- 看板内 inform / 提醒 / 表扬 / 升 GA  
- 健康环比进环；人维度排行；GE 阶段分布环  
- 列表行直跳 Project Panel（本波主跳专项看板；双链后置）  
- 左环段长改为「仅定义+延迟」；图例「按问题/体量」切换排序（P1，无投诉前不做）  
- `total=0` 专项进左图例（P1）  
- **随看板软开 `people-summary` / 人员 Tab**（问责面另开）  
- **stranger 深链整板 403**（与软过滤冲突）

#### 4.11.8 一句话

> 子目标看板：左环选专项、右环选项目情形、列表进专项看板；左右同构分布图（图例 `名称(n)`）；项目真表；入口与专项同软过滤（含 stranger=200+空）；GE 管可见切片、AA 看板读透传错误码；URL 扛状态；空态三分。

---

### 4.12 公司目标看板（Company Objective Board · Normative · v0.2.77 · **现网**）

在**公司目标**（`Objective.level=company`）详情增加 Tab **「看板」**：同一排三环——**子目标分布 → 专项分布 → 项目分布**，再下钻项目真表。与 §4.11 **同软过滤 / 同打桶 / 同错误透传**；**不**嵌套多层子目标（只吃直属 `sub`）。

#### 4.12.1 范围与门禁

| 项 | 约定 |
| -- | ---- |
| **进** | 仅 `level=company`；进公司目标详情默认 Tab = **看板** |
| **路径** | 扩展现有 `GET …/board-projects` 与 AA `GET …/objectives/{id}/board`（按 `level` 分支）；**不**另开路径 |
| **入口 ACL** | 与 §4.11.1 **同构软过滤**；无整板硬 403；切片可空 → 可见范围空 |
| **与人员 Tab** | 目标详情 **已无**人员 Tab；`people-summary` 仅专项 / 项目（问责硬门） |
| **错误码** | 不存在 → **404**；非 `sub`/`company` → **400**（如 `objective_level_unsupported`）；看板读 4xx/5xx **透传**；FE 4xx **不重试** |

#### 4.12.2 表面结构（三环 + 真表）

| 块 | 约定 |
| -- | ---- |
| **布局** | 每个分布块 **环上 · 图例下**（与 §4.10/§4.11「环左 · 图例右」刻意不同；三环并排时更省横宽） |
| **左 · 子目标分布** | 环 + 图例 `子目标名(n)`；段长 = 该子目标进环项目总数；排序 = 定义+延迟降序 |
| **中 · 专项分布** | 环 + 图例 `专项名(n)`；scope = 左环选中子目标（未选 = 全部直属子目标上卷）；专项须带 `sub_objective_id` |
| **右 · 项目分布** | §4.10 四桶同构；scope = 中环选中专项（未选则随子目标/上卷） |
| **项目列表** | 真表列：**项目 · 类 · 子目标 · 专项 · PM**；点项目名 → 所属 **专项看板** |
| **可见性** | 仅 Actor 可见项目；取消/归档不进环（AA 打桶） |

#### 4.12.3 交互与 URL（Normative）

```
点左环子目标 → 中环收窄专项 → 点中环专项 → 右环/列表收窄
点左环中心 → 清 sub（兼清 program+bucket）→ 回上卷
点中环中心 → 清 program（兼清 bucket）→ 专项回上卷
```

| 项 | 约定 |
| -- | ---- |
| URL | `?tab=board&sub=&program=&bucket=` 为真相 |
| 切 sub | **必须**清 program + bucket，并按新 scope 重算 default 桶 |
| 切 program | **必须**清 bucket |
| 非法 id | 不在当前数组 → 视为未选 |

#### 4.12.4 空态与合计

- 无直属子目标 / 可见进环为空 / 已选桶列表空：三分文案同 §4.11.4 精神（禁止共用「暂无数据」）。  
- 合计不变量：`sum(subs[].total) == sum(counts.*) == len(items)`（`subs[]`/`programs[]` 仅 `total>0`）。

#### 4.12.5 数据分层

| 层 | 职责 |
| -- | ---- |
| **GE** | `board-projects`：`level=company` → 直属 `subs[]` + 其下 `programs[]`（含 `sub_objective_id`）+ Actor 可见 `projects[]` |
| **AA** | 复用 `bucket_for_project`；读 **`project_work_state_cache`**（§4.10.4）；聚合 `subs` / `programs` / `counts` / `items`（item 含 sub+program 字段） |
| **skstudio** | `CompanyObjectiveBoardPanel`；三环 + 真表；URL 状态机；4xx 不重试 |

#### 4.12.6 刻意不做

- 嵌套多层子目标；人员软开；看板内 inform/提醒/表扬/升 GA；PM id 大清洗

#### 4.12.7 一句话

> 公司目标看板：三环级联（子目标→专项→项目）+ 真表；契约扩展同一 board 路径；软过滤与人员硬门边界同 §4.11。

### 4.13 公司目标排行榜（Company Objective Ranking · Normative · v0.2.78 · **代码齐 / 待冒烟**）

按子目标「顺利执行比率」排序成表，挂在公司目标详情 **排行榜** Tab（看板之后）。

#### 4.13.1 范围与门禁

| 项 | 约定 |
| -- | ---- |
| **进** | 仅 `level=company`；Tab 序：`看板 → 排行榜 → 概览 → 结构`；默认仍看板 |
| **不出** | 子目标页；专项级排行；目标「人员」Tab（已下线） |
| **路径** | 复用 AA `GET …/objectives/{id}/board` 的 `ranking[]`（company 分支）；**不**另开路径 |
| **入口 ACL** | 与 §4.12 同软过滤；无整板硬 403 |

#### 4.13.2 口径（Normative）

| 项 | 约定 |
| -- | ---- |
| **顺利** | 进环且桶为 `in_progress` 或 `completed`（无定义问题、无延迟问题） |
| **排除** | 取消 / 归档（同看板，不进环） |
| **比率** | `rate = (in_progress + completed) / total`；`total` = 该子目标进环四桶之和 |
| **进榜** | `total > 0`；`total = 0` 不进榜 |
| **排序** | 比率降序 → total 降序 → 子目标名升序 |
| **表列** | 名次 · 比率 · Owner · 子目标名（前三列随内容撑开；子目标吃剩余并截断） |

#### 4.13.3 数据分层

| 层 | 职责 |
| -- | ---- |
| **GE** | company `board-projects` 的 `subs[]` 含 `owner_user_id` |
| **AA** | 由子目标 counts 生成 `ranking[]`（`rank` / `owner_user_id` / `rate` / `sub_*` / `smooth` / `total`） |
| **skstudio** | `CompanyObjectiveRankingPanel`；复用 board 查询；4xx 不重试；三分空态 |

#### 4.13.4 刻意不做

- 子目标页排行；专项级排行；人员软开；新 GE/AA 路径

#### 4.13.5 一句话

> 公司目标排行榜：按子目标顺利执行比率排序；口径对齐四桶看板；挂在独立 Tab。

---

## 5. 落地：仓 · 挂载 · 里程碑（Accepted · **M0–M6 现网**）

### 5.1 仓库与边界

| 组件 | 职责 |
| ---- | ---- |
| **`active_agent`（独立仓）** | 主动 Agent **运行时**：SenseEvent / Decision / Action / Mute / 周快照 / coverage；**SDA 投影 + timeline 日志**；队列与 cron；PRA 为第一个实例包（如 `packs/pra`）；日后可增 PBA 等 |
| **goal_execution（GE）** | 项目域真源；**观测挂载点 + 契约 + 出站**；不嵌入 PRA 决策；**不**承载 SDA/PRA 票务 API |
| **skstudio** | BFF（`/api/v1/active-agent/*`）、鉴权；执行力 **Project Panel**（深链 `?event=`）；项目级 Mute/审批设置 UI |
| **Hermes PA / GA** | inform 触达通道（深链进 Panel 流）；不是票库 |

仓名用 **`active_agent`**（运行时），不用 `pra` 作仓名，以免第二实例名不正。仓 README：`~/projects/active_agent`；实现细账见 [PRA-实现与测试.md](./PRA-实现与测试.md)。

### 5.2 GE 挂载最小合同（一期）

| 项 | 约定 |
| -- | ---- |
| **一期必做** | `after_project_graph_write`（阶段/门控/任务/截止日等写成功后出站） |
| **一期宜做（现网）** | 项目生命周期：取消/归档/完成 → AA INV-1 清票；**软删** → `project_soft_delete`（无 graph） |
| **一期不做** | 读路径尖信号对外投递（仅写 + cron；避免 GE 依赖水位副本） |
| **注册** | PRA（`active_agent`）**启动自注册**为订阅方（`AA_PUBLIC_BASE_URL`）；GE 不写死 PRA URL 业务逻辑 |
| **投递** | **outbox 异步** + at-least-once（写后非阻塞 flush + 进程内周期 flush）；订阅方幂等（`idempotency_key` / `concern_key`） |
| **载荷最小** | `idempotency_key`、`occurred_at`、`project_id`、`change_kind`、实体 refs（阶段/门控/任务等） |
| **依赖** | GE → Agent **只推**；Agent → GE 读真源 / 可选推水位副本；**禁止**读时问询 |

细节见 [openapi/ge-observation-mount.md](../../platform_docs/openapi/ge-observation-mount.md)；**合同以本表为准**。

### 5.3 里程碑（竖切）

| MS | 内容 | 为何这样切 |
| -- | ---- | ---------- |
| **M0**（可并进 M1） | 建仓 `active_agent`：服务骨架、DB、健康检查、配置；调度器可跑空任务 | **现网** |
| **M1 感知保底** | PRA cron 日扫 + 周六周切；`SenseEvent` + 周快照；cron 自写 `last_coverage_at`；**不接** GE 挂载 | **现网** |
| **M2 决策 HITL** | adopted→决策队列；Harness；**仅整改两意图**可能待确认；`require_approval`；inform | **现网** |
| **M3 行动闭环** | 状态机、催促、报告/核对、提醒确认、表扬核销；stalled→**自动** escalate（§4.5.1） | **现网** |
| **M4 写挂载** | GE `after_project_graph_write`（+ 生命周期）+ 注册/outbox；Agent 消费；与 cron 去重 | **现网** |
| **M5 SDA** | `require_approval`；自动 escalate；`stream_key` + timeline；投影 API；执行力 SDA tab；深链 | **现网（M5.1–M5.5）** |
| **M6 项目推进 Action** | 推进意图 + Panel + **produce/prereq 就绪集** + 流上优先/进展可链不摘 + 整改两意图；**阶段完成 = notify** | **现网**（软缺口：GE 延迟转段 / E2E 全量）· §4.9 · **DoD** 见 [PRA-实现与测试](./PRA-实现与测试.md) · 链 GE v2.38.65 |

**约束：** M4 **不得**早于 M1；M0 可并入 M1；M4 可与 M3 尾部重叠开发，但验收上感知内环先于挂载。

**v1 意图范围**仍服从 §2.5.2 / §3.8.1 / §4.8.1（定义/超时/健康环比提醒表扬；升 GA 后置）。**项目推进**意图见 §4.9（**现网**；`deliver_artifact` 后置）。

### 5.4 一句话

> 仓用 `active_agent`；写挂载 outbox 与 **SDA 事件流**均已现网（执行力 UI + AA 投影/履历）。

### 5.5 后置项一览（非现网 · 勿当 DoD）

| 项 | 说明 | 现网边界 |
| -- | ---- | -------- |
| `escalate_ga` | 组合连续两周恶化升 GA | Sense 可产 `worsened_2w`；Decide **不**映射开票 |
| `deliver_artifact` | 一般任务交付开票 | Sense **不** emit；常量/map 保留 |
| Mute 代行 HITL | Mute=真时代行可代行 HITL | Mute **仅**跳过 `remediate_*` 开票前审批；**无**代行 review 等 |
| `until` 临时 Mute | 临时要审批、到期自动恢复 Mute | v1 不做 |
| 等文档卡载体 | `execution.deliver.waiting` 稳定投影为 Panel 卡 | **已裁定（v0.2.51）**：v1 **不**投影；waiting 保持 **suppressed**；DoD A4 已改 |
| 升 GA 拍板 UI / 公司目标第一棒 | §3.4 第二跳等 | 后置 |

代码偏差（非后置）见 [PRA-代码问题清单.md](./PRA-代码问题清单.md)（CODE-001～004 均已关；无待修 P1/P2）。

---

## 6. 修订记录

| 版本 | 日期 | 说明 |
| ---- | ---- | ---- |
| **v0.2.91** | **2026-08-27** | **BOARD-CACHE**：§4.10.2 延迟桶对齐办事态机（开放 remediate **或** `DELAY_*` 缓存）；§4.10.4/§4.11.6/§4.12.5 AA 读 `project_work_state_cache`、禁看板 per-project 扫图；[迭代](./PRA-目标看板work_state缓存迭代.md) **v1.0.0** |
| **v0.2.81** | **2026-08-18** | **M41 现网**：拍板链不含 PMBP · **PRA-PMBP-01** · 链 [M41](./目标与执行-项目管理BP迭代.md) **v0.2.0** |
| **v0.2.80** | **2026-08-18** | **M41**：§4.9.2 `review_project` 不含 PMBP · 拍板链 normative 段 · 链 [M41](./目标与执行-项目管理BP迭代.md) **v0.1.0** · **PRA-PMBP-01** |
| **v0.2.79** | **2026-08-15** | §4.10/§4.11 看板布局：**环左 · 图例右**；§4.12 公司目标保持 **环上 · 图例下**；§4.10 图例钉死 `类名(n)` 与子/公司同构 |
| **v0.2.78** | **2026-08-15** | **§4.13 公司目标排行榜**：顺利执行比率表；**目标详情去掉人员 Tab**（objective `people-summary` 下线；专项/项目保留）；待 Chrome 冒烟后标现网 |
| **v0.2.77** | **2026-08-15** | **§4.12 公司目标看板现网**：三环级联（子目标→专项→项目）+ 真表；扩展 `board-projects`/`board` 按 level；§5.5 去掉「公司目标看板后置」；Chrome 公众公司竖切过 |
| **v0.2.76** | **2026-08-15** | §4.11 UI：左右同构分布图；图例改 `名称(n)`（去定义/延迟次行）；项目列表真表；分布与列表留白 |
| **v0.2.75** | **2026-08-15** | §4.10/4.11：**ACL/错误码差口关闭**（GE 软过滤 · AA 透传 · FE 不重试）；Chrome anne→超声 + 人员负例 + 健康城市/专项回归；总评显著全路径 |
| **v0.2.74** | **2026-08-15** | §4.11：stranger 深链=200+空切片；人员 Tab **不同软**（people-summary 硬门）；§4.10/4.11 AA **看板读**错误透传同波；刻意不做写死 |
| **v0.2.73** | **2026-08-15** | §4.11.1：**入口 ACL = 专项 GET 同软过滤**（禁 governor 硬 403 整板失败）；错误码透传 + FE 4xx 不重试；实现差口见 PRA-实现 |
| **v0.2.89** | **2026-08-22** | **PRA-SDA-SLOT 现网**：mute/act/transition 分槽；[分槽迭代](./PRA-SDA步骤呈现分槽迭代.md) **v0.1.3** · [评价实现闸 · 显著](./PRA-SDA步骤呈现分槽评价.md) |
| **v0.2.88** | **2026-08-22** | **SDA 分槽补丁（规划）**：共识 §4.0 人槽不变量 · mute/act/transition；挂 [分槽迭代](./PRA-SDA步骤呈现分槽迭代.md) · [评价文档闸 · 显著](./PRA-SDA步骤呈现分槽评价.md) |
| **v0.2.87** | **2026-08-22** | **PRA-WS1.1 现网**：`revalidate_project` · 空 items 报告链 · Owner heal；[迭代](./PRA-项目办事态机写后重评迭代.md) **v0.1.1** · [评价实现闸 · 显著](./PRA-项目办事态机写后重评评价.md) |
| **v0.2.86** | **2026-08-22** | **办事态写后重评**：共识 §4.6 · [迭代 PRA-WS1.1](./PRA-项目办事态机写后重评迭代.md) · [评价（文档闸 · 显著）](./PRA-项目办事态机写后重评评价.md)；§3.3.1 报告链禁空 items⇒去补救 |
| **v0.2.85** | **2026-08-21** | **SDA 步骤呈现共识**：§4.8.6 槽位/模板 · 催促含被催人 · 升级升不动 why；挂链 [共识](./PRA-SDA步骤呈现共识.md) / [迭代 PRA-SDA-STEP](./PRA-SDA步骤呈现迭代.md)；实现待齐 |
| **v0.2.84** | **2026-08-21** | **PRA-WS1 现网**：办事态机生产发版；慢病半截有去补救；链 [迭代](./PRA-项目办事态机迭代.md) **v0.2.1** |
| **v0.2.83** | **2026-08-21** | **项目办事态机**：挂链 [共识](./PRA-项目办事态机共识.md) **v0.2.0** / [迭代 PRA-WS1](./PRA-项目办事态机迭代.md)；§3.3.1 关票改为办事态谓词（半截偏差 ≠ 可清 remediate）；INV-3 修订见一致性合约 |
| **v0.2.82** | **2026-08-20** | **一致性合约**：`reconcile_project` INV-1..4；改期/空 overdue → cancel `remediate_*`；空 gaps → cancel `fix_definition`；终态/软删零开放票；读路径 list_events 兜底。废止 v0.2.23「改期不关票」验收。见 [PRA-一致性合约迭代.md](./PRA-一致性合约迭代.md) |
| **v0.2.72** | **2026-08-15** | §4.11 子目标看板 **现网**：GE board-projects + AA board + FE 双环；Chrome 竖切通过（见实现文档） |
| **v0.2.71** | **2026-08-15** | §4.11 右环 UI 名：**办事分布 → 项目分布**（与专项看板「分布」主语=项目对齐） |
| **v0.2.70** | **2026-08-15** | §4.11 风险收口：GE 保留 lifecycle / AA 排除进环；合计不变量；左图例次行「定义·延迟」；URL 状态机与切 scope 重置桶；空态三分；P1 项写入刻意不做 |
| **v0.2.69** | **2026-08-15** | **§4.11 子目标看板（共识 / 待实现）**：同一排双环（左专项分布 · 右项目分布）；列表进专项看板；仅 `level=sub`；GE `board-projects` 一次拉取；AA 复用打桶；公司目标看板后置；§4.10.5 去掉「子目标同构后置」 |
| **v0.2.68** | **2026-08-14** | §4.9.4 **项目进展成果列（现网）**：已提交才显材料；Note 标题可点；summary 次行；status/metric 附属材料；树批量 + by-id 兜底；禁 `kb:uuid`；线框 outcome-material；链 GE **v2.38.71** · FE M1–M3 |
| **v0.2.67** | **2026-08-13** | SDA 角色门禁：定义核销仅 PM；延迟报告=Executor（补救任务负责人 · 现网接线）；改派 API；投影括号角色叙事；实现矩阵见 PRA-实现 |
| **v0.2.66** | **2026-08-13** | §4.10：看板环/列表按 **当前 Actor** 可见项目过滤（禁止 AA 以 reviewer 抬权拉全量） |
| **v0.2.65** | **2026-08-13** | §4.10 专项看板 **现网**：AA board API + FE 默认看板 Tab（环+列表）；无「全部」筛 |
| **v0.2.64** | **2026-08-13** | §4.10：看板无「全部」筛；列表字段名/类/PM；进专项默认落看板 |
| **v0.2.63** | **2026-08-13** | §4.10：专项看板（环分布 + 下钻列表）；四类：定义 / 延迟 / 进行中 / 已完成；取消归档不进环 |
| **v0.2.62** | **2026-08-13** | §3.3.0：项目内办事优先级 **定义 → 延迟 → 其它**；回收已开非优票（cancel 不 resume）；首扫/发版防 AA 先于 GE 竞态 |
| **v0.2.61** | **2026-08-12** | Panel：进展插在筛选条与 SDA 之间；筛选行 checkbox「项目进展」缺省勾选；用户选择后 localStorage 记忆 |
| **v0.2.60** | **2026-08-12** | Panel IA：上「项目进展」· 下 SDA 执行区（结项项目先看模型进展） |
| **v0.2.59** | **2026-08-11** | Panel：执行区下方「项目进展」三列表（阶段/任务/成果；GE graph 只读；等待≠未完成） |
| **v0.2.58** | **2026-08-11** | CODE-007：SDA 稳定与性能（签收路由竖切、写路径 `pra_write_path` SLO、notify 投影去重/collapse、Sense 降噪） |
| **v0.2.57** | **2026-08-11** | CODE-006：`notify_phase_complete` 终态幂等（Sense `already_notified` + Decide 双闸）；业务语义不变 |
| **v0.2.56** | **2026-08-11** | CODE-005：写挂载自愈（AA 启动注册失败退避重试；后续 M2–M4 GE 拒短 token / 周期重注册 / dead requeue）；业务语义不变 |
| **v0.2.55** | **2026-08-11** | 写路径 Sense：项目票/事件预取 + 延迟 flush；ingest 优先嵌入 `definition_gaps`；业务语义不变 |
| **v0.2.54** | **2026-08-11** | 性能优先级钉死：全扫可慢、单项目写后判断要快；写挂载 sense 轻量图 + Decide 按项目 scope；链 GE **v1.39.81**；业务语义不变 |
| **v0.2.53** | **2026-08-10** | CODE-004：写挂载/关键路径性能（M1–M4 收口 + M5 评价）；SenseEvent 增 `decided` 消费态；产品业务语义不变 |
| **v0.2.52** | **2026-08-10** | 清单 CODE-003：GI 提交关窗深链回弹（FE GE-T62b / v1.39.78）；产品语义不变 |
| **v0.2.51** | **2026-08-10** | §4.9：`review_gate` 驳回 **按 gate_id** cancel；`review_project` 整项目（CODE-001）；§5.5 / DoD A4：**等文档卡后置**、waiting=suppressed（CODE-002 文档关） |
| **v0.2.50** | **2026-08-10** | §4.8.6 类型徽章补 **交付/评审**；Panel/`?event=` 深链；新增 **§5.5 后置项一览** |
| **v0.2.49** | **2026-08-10** | 文首/§4.9/§3.6/§5：推进与 Panel 标 **现网（M0–M6）**；`deliver_artifact`/升 GA/Mute 代行标 **后置**；废「实现未齐 / 切换日前 Tab」 |
| **v0.2.48** | **2026-08-10** | §3.3.1：逾期 cancel 按门控/阶段；计划就绪后恢复补救任务 deliver；空 items ≠ 报告就绪；废名迁移完成（删 LEGACY/backfill） |
| **v0.2.47** | **2026-08-10** | §4.9：阶段完成改为 `notify_phase_complete`（只通知、无通过/驳回）；废 `review_phase` HITL |
| **v0.2.46** | **2026-08-10** | §4.9：**Retire 依赖矩阵 UI**；协同 = Canvas 拖线 + 创建任务可选 GI；链 GE v2.38.65 |
| **v0.2.45** | **2026-08-10** | §4.9.4：创建任务可选产出/依赖 GI；链 GE v2.38.64 |
| **v0.2.44** | **2026-08-10** | §4.9：矩阵只编排 Task↔门控项；临时交换在项目 Note；链 GE v2.38.63 |
| **v0.2.43** | **2026-08-10** | §4.9：**三列表**依赖矩阵（Task·前置文档·交付；空前置=起点）；链 GE v2.38.61 |
| **v0.2.42** | **2026-08-10** | §4.9：**依赖矩阵**（简图+弹窗·就绪集 Sense）；链 GE v2.38.60 |
| **v0.2.41** | **2026-08-10** | §5.3 M6 链 **DoD**（PRA-实现）；链 GE v2.38.59 |
| **v0.2.40** | **2026-08-10** | §4.9.4 钉 **App 壳**（左树+右 Panel）；线框链 app-shell；§4.9 文首版本对齐 v2.38.58 |
| **v0.2.39** | **2026-08-10** | 进展：卡上**可链**项目 Note；**不**摘摘要；链 GE v2.38.57 |
| **v0.2.38** | **2026-08-10** | 进展从简：日报若有只进项目 Note；链 GE v2.38.56 |
| **v0.2.37** | **2026-08-10** | 进展=团队知情（非状态机）；日报可选且入项目 Note；旧 `remediate` **一刀切废名**（禁长期双轨）；链 GE v2.38.55 |
| **v0.2.36** | **2026-08-10** | §4.9.4 **流上优先**；弹窗必有卡上入口；长跑进展槽；链 GE v2.38.54 |
| **v0.2.35** | **2026-08-10** | §4.9.4 Panel **改向**：继承 SDA 单栏流 + 按需弹窗/链出；废左右分栏与 Panel 回树；链 GE v2.38.53 |
| **v0.2.34** | **2026-08-10** | **整改意图拆分**：废弃笼统 `remediate` → **`remediate_stage`** / **`remediate_envelope`**；§3.3/§3.5/§3.6/§4.8.6.2；旧值按 concern 归一 |
| **v0.2.33** | **2026-08-10** | §4.9.4 补充：待我处理、定义返回重算、左栏吞 SDA；链 GE v2.38.51 |
| **v0.2.32** | **2026-08-10** | §4.9.4 Panel UI 首版；链 GE v2.38.50 |
| **v0.2.31** | **2026-08-10** | §4.9 推进契约补全（**UI 细则见 v0.2.32**）；链 GE v2.38.49 |
| **v0.2.30** | **2026-08-10** | §4.9 五意图骨架（**由 v0.2.31 补全**）；链 GE v2.38.48 |
| **v0.2.29** | **2026-08-09** | §4.9 任务执行 Action 首版（**由 v0.2.30 收束**）；链 GE v2.38.47 |
| **v0.2.28** | **2026-08-09** | §3.3.1 Canvas：**钟一点定时间**建任务；不弹延期说明；链 GE v2.38.46 |
| **v0.2.27** | **2026-08-09** | §3.3.1 修订：报告前置 = **定合理时间 → 建补救任务**（非纯日历）；SDA 未满足则仅「去补救」；Deviation 原因/方案非必填，叙事归整改 Note；链 GE §6 时间先行 |
| **v0.2.26** | **2026-08-09** | §3.3.1 门控延期补救：PM 重计划 →（懒建）报告 → 提交 → PM；第 N 次同构；日历门槛（非开偏差）；SDA 取消「创建报告 / 开偏差齐套」叙事；后由 **v0.2.27** 收紧前置 |
| **v0.2.25** | **2026-08-08** | 阶段延迟聚合：同阶段门控+窗口 → `pra:remediate:stage:{id}` + `items[]`；齐套处置后报告+PM；取消阶段票「已改期核销」；项目包络仍独立核销 |
| **v0.2.24** | **2026-08-08** | 延迟分径：门控仍报告+PM；阶段/项目日程仅改期后 `verify_stage_schedule` 核销；禁止对日程票走报告链 |
| **v0.2.23** | **2026-08-08** | 延迟票关票收口：Canvas 开偏差不消票；仅提交整改报告 + PM 通过 → done，驳回回待提交；撤回 overdue_cleared 自动关票；CTA 以报告为主 |
| **v0.2.22** | **2026-08-08** | Define 圆章：补救/偏差/延期；偏差 open/activate/extend/cancel/close 入 GE 写挂载；sense 认 GE `is_overdue`（不因此关票） |
| **v0.2.21** | **2026-08-08** | 逾期系统 GI/产出任务可人手开偏差 → Canvas「补救·…」；范围偏差仍禁；PRA 仍不自动开偏差；链 GE-24 修订 |
| **v0.2.20** | **2026-08-08** | Canvas `issue=definition\|delay`；延迟琥珀时钟 + SDA `nav_delay`；业务门控点钟开偏差，系统门控走整改报告 |
| **v0.2.19** | **2026-08-08** | 「发现问题」步骤写入/展示 `problem`；合并刷新；存量从 SenseEvent 回退 |

| **v0.2.18** | **2026-08-08** | 写挂载同步定义票 gaps：AA 自注册 + GE 自动 flush；空 gaps 保留票并以核销 CTA 为主；人确认关票 |
| **v0.2.17** | **2026-08-08** | 定义完整性评估真源收口 GE：`definition-gaps` + graph 嵌套；包络口径；`missing_assignee`；AA/FE 只消费 |
| **v0.2.16** | **2026-08-08** | §3.3 定义 Canvas 就地红「!」：标题旁标缺口；hover 原因；点击进编辑 |
| **v0.2.15** | **2026-08-08** | §3.3 纠正：仅定义项目合并 1 票；延迟按实体分票；定义挡执行不污染 `gaps[]` |
| **v0.2.14** | **2026-08-08** | §3.3 开票合并首版（后由 v0.2.15 纠正延迟合并） |
| **v0.2.13** | **2026-08-08** | §4.8.6.2 按意图分 CTA；定义深链/核销；整改 Note 创建·编辑·提交·PM 通过/驳回 |
| **v0.2.12** | **2026-08-08** | M5.1–M5.5 现网：`require_approval` · 自动 escalate · SDA 投影/UI/深链 |
| **v0.2.11** | **2026-08-08** | `require_approval`；§4.5.1 Owner 阶梯；不可变 `stream_key`；M5 契约收口 |
| **v0.2.10** | **2026-08-08** | SDA 分层纪律；timeline append；挂载节点/标题/深链；规划 M5；链实现文档 § SDA |
| **v0.2.9** | **2026-08-08** | §4.8.6 SDA UI 齐套：双徽章、筛选文案、通用步骤含催促/驳回、stalled 即卡住、样例 A–F |
| **v0.2.8** | **2026-08-08** | HITL 仅超时整改；项目缺省 Mute；escalate_owner 自动升一级；SDA 事件流 UI 约定 |
| **v0.2.7** | **2026-08-07** | M0–M4 现网：`active_agent` + GE outbox + 实现文档 |
| **v0.2.6** | **2026-08-07** | §5 落地：`active_agent` 仓、挂载最小合同、M0–M4 里程碑 |
| v0.2.5 | 2026-08-07 | §2.5.3.1 水位由 PRA cron 自写 |
| v0.2.4 | 2026-08-07 | §4.8 行动实现 |
| v0.2.3 | 2026-08-07 | §3.8 决策实现；HITL 等待 T+1 |
| v0.2.2 | 2026-08-07 | §2.5 感知实现 |
| v0.2.1 | 2026-08-07 | 健康占比态势；升 GA 缺省禁取消；升级 vs escalate；Mute Web UI |
| v0.2.0 | 2026-08-07 | §4 行动子系统 Accepted |
| v0.1.1 | 2026-08-07 | §3 决策子系统 Accepted |
| v0.1.0 | 2026-08-07 | 首版：§2 感知子系统共识 |
