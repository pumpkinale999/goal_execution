# Governance Assistant · project-create（共商建项 / 补空壳）

- **文档类型**：产品需求 + 实现规格 + 测试/验收（本迭代真源）
- **版本**：**v0.1.48**（2026-08-23 · **C65 Agent 文档齐** + GA/Web 建项同路径规划）
- **里程碑**：**BO-M-PC**（**M0–M7 + C57～C65**）
- **状态**：**C62 现网**；C63/C64 ✅；**C65 BFF M1 ✅** · **Agent 文档 ✅** · **发版 M2–M3 待签收**
- **适用对象**：产品、GA / Hermes / skstudio 研发、QA

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [Governance-Assistant产品设计.md](./Governance-Assistant产品设计.md) | 管域 Copilot · G29 · mutate · `open_ge_embed`（**v0.8.108** 指针） |
| [Governance-Assistant-project-duplicate迭代.md](./Governance-Assistant-project-duplicate迭代.md) | **对照**：复制项目（**v0.1.8**；与本 create 分流） |
| [Hermes与组织及目标执行的集成.md](../../platform_docs/integration/hermes-goal_execution/Hermes与组织及目标执行的集成.md) §13.14 / §13.15 | governance toolset；**§13.15**（**v1.9.71** · C62 现网） |
| [business-os共识.md](../../platform_docs/business-os共识.md) §9 | 演进入口（**v1.3.98**） |
| [hermes-profiles/governance-assistant/SOUL.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/SOUL.md) | 瘦路由（含 validate/commit · C62 纯文本深链 + wecom 样例） |
| [hermes-profiles/governance-assistant/skills/governance/project-create/SKILL.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/skills/governance/project-create/SKILL.md) | **Agent 规程真源 · 0.5.7**（C65 专节 + 话术表） |
| [hermes-profiles/governance-assistant/PC-T01-signoff.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-T01-signoff.md) | 建图竖切签收（含 **M5** 边界边） |
| [hermes-profiles/governance-assistant/PC-NOTIFY-signoff.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-NOTIFY-signoff.md) | **M4** 成员欢迎 inform 签收 |
| [openapi/ga-bo-m-pc-plan.openapi.yaml](./openapi/ga-bo-m-pc-plan.openapi.yaml) | **M7 + C57–C60** validate + commit（**0.2.5**） |
| [openapi/ga-bo-m-pq.openapi.yaml](./openapi/ga-bo-m-pq.openapi.yaml) | `project_mutate` + notify；Plan 三 action **已删**（**0.1.11**） |
| [openapi/ga-bo-m-structure-mutate.openapi.yaml](./openapi/ga-bo-m-structure-mutate.openapi.yaml) | `goal_mutate` 建壳（+`shell` 回执；PC 仅执行器内） |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) §3.4.3 / §3.4.4 | 系统起止 seed · 签收路由 · orphan 例外 |

### 0.1 DOC-SYNC（跨文档对齐表 · v0.1.48）

| 工件 | 版本 / 状态 | 与本迭代 |
| ---- | ----------- | -------- |
| 本迭代 | **v0.1.48** | C62 现网 + **C65 GA/Web 建项同路径（v29.00.07）** + **Agent 文档齐** |
| SKILL | **0.5.7** | C65 专节 · 话术表 · tags `c65` |
| SOUL | **≥0.5.7** · C65 三句 + 身份半句 | ✅ |
| profile README | PC **≥0.5.7** · C65 验证行 | ✅ |
| project-duplicate SKILL | **0.1.1** · 红线 C65 | ✅ |
| eval_governance_assistant | C65-AGENT 静态断言 | ✅ |
| Hermes §13.15 | **v1.9.71** | △ C65 指针待刷（非挡实现） |
| OpenAPI pc-plan | **0.2.6** | ✅ C64 sender 短名别名 |
| OpenAPI pq | **0.1.11** | ✅ |
| GA 产品设计 | **v0.8.108** | ✅ C62 |
| business-os §9 | **v1.3.98** | ✅ |
| PC-PLAN-signoff | C65-A 待实跑 | △ GA-PC-K27-AGENT-T01 |
| BFF / plugin | **C65-M1** | ✅ `ga_structure_mutate` + GE-T47 pytest |

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| C1 | 能力形态 = **Hermes skill**（非 mega create tool）；名 **`project-create`** |
| C2 | 范围 = **A+B**：A 从零立项；B 补全 **完全系统预生成** 空壳。**暂不做** C（`project-evolve`） |
| C3 | B 准入：仅 **完全系统预生成** 空壳（§3.3）；**不用** `status=draft`（GE create 多为 `active`） |
| C4 | 「方案」= 无业务含义 sample；enrich 时 **改名复用** 为第一业务阶段（不优先删除、不长期保留） |
| C5 | 整图 **确认一次** → 连续落库；每原子写 `user_confirmed=true` 且 **一次一项**（M6：确认对象 = **Plan 表格确认单**，整单同意） |
| C6 | 落库编排 = commit 执行器内 `goal_mutate` create（仅 A）+ 原子补图；**Agent 不逐步 invent**（M6）。**M7**：Agent 只调 validate/commit 两 tool，执行器细节对模型不可见 |
| C7 | **OUT**：activate、提交/签收、lifecycle、改 membership API、整图单次 HTTP、evolve、新「读全图」独立 tool、**GA 启用 `inform` toolset** |
| C8 | 打开 GA `skills` toolset；仅白名单同步本 skill |
| C9 | SOUL **瘦路由**；细则在 skill |
| C10 | 写权对齐现网 mutate（能评 ≠ 能改） |
| C11 | 中途失败：停 + 已成功项 + 深链 + **结构化 detail**；不整图回滚；可 **同 Plan 续跑**（勿 A 重复 create）；**禁止** 换无关 action 盲重试 |
| C12 | DQ 建议立项 → 一句引导本 skill |
| C13 | **A 建壳回执**须带 `shell.placeholder_phase_id`（及 name=方案），供下一步 `patch_phase` |
| C14 | **`add_task` 支持 `assignee_username`**（BFF 解析，对齐 `owner_username`）；对话禁止向用户索数字 user id |
| C15 | **`patch_phase` 可按名解析**：`fields.phase_name`（或 target 仅 name）在 `project_id` 下唯一匹配非系统阶段；B 路径依赖此能力或 C13 等价信息 |
| C16 | **PC-NOTIFY（M4）**：共商图落库成功后，向项目组成员发 **同一欢迎文案** + **项目深链**；**建壳不发** |
| C17 | 收件人 = **S1**：PM ∪ 业务任务负责人（去重）；**跳过**本轮同意落库的调用方 |
| C18 | 通道 = **域侧钩子**（BFF 内经 PA inform 投递）；**禁止** GA 挂 `inform_*` tool |
| C19 | 发送者 = **本轮同意落库的调用方**（mutate `sender`） |
| C20 | A/B **同一文案模板**（不按角色分叉）；不区分「新建」与「补空壳」口吻 |
| C21 | inform **失败不回滚**建图；可对调用方轻量提示「通知未全部送达」 |
| C22 | 确认单可列「将通知：…」；整图同意即含通知同意；独立里程碑 **M4**（不挡 M0–M3） |
| C23 | **M5 · 启动签收路由**：落库后 `项目启动` **必须**有 ≥1 条业务侧 Prerequisite；签收人 = **项目经理**（`eligible_signers` ⊂ {PM}） |
| C24 | 启动边挂法：优先复用第一业务阶段且 **owner=PM** 的任务；若无 → **新增**签收路由任务「确认启动」（不 produce）→ `add_prerequisite` → `项目启动`；**N=1 无产出任务时亦强制注入「确认启动」**（M6） |
| C25 | **M5 · 结项前置（E1）**：末业务阶段**退出门控** → `add_prerequisite` → 系统任务 **`结项复盘`**（解锁边）；**不**改 `确认结项` 签收路由 |
| C26 | 「禁动系统开始/结束」= 禁改名/删阶段/删改系统 Task·GI/断系统 produce；**允许** C23–C25 的 `add_prerequisite`（及 C24 新增业务侧「确认启动」） |
| C27 | **M5 范围**：**仅** PC skill / Plan / 签收；**不**改 GE seed（§3.4.3 启动仍可不 seed）；**不**改 PQ「系统不进衔接边」 |
| C28 | 独立里程碑 **M5**（不挡 M0–M4 现网）；无新 OpenAPI / BFF action（M5 切片） |
| C29 | **M6 · Plan 真源**：共商真源 = 结构化 **`ProjectCreatePlan`（JSON）**；Markdown **表格**仅为确认单投影；**禁止** 以自由文 Intent 作为唯一落库依据 |
| C30 | **validate → confirm → commit（M7 改口 · 废 M6 propose 话术）**：结构共商齐后 **必须** `governance_project_plan_validate`；**禁止** 未 ok / 未整单同意即写图；改字段 → 改 Plan JSON → 再 validate；同意绑 fingerprint → `governance_project_plan_commit` |
| C31 | **B 编译硬约束**：`enrich_shell` 时 `phases[0].op` **必须** `patch_shell`；**禁止** 用 `add_phase` 顶替改名复用「方案」（左伟单根因） |
| C32 | **N≥2 handoff 必填**：`len(phases)≥2` ⇒ `handoffs.length≥1`；N=1 ⇒ `handoffs` 必须空 |
| C33 | **默认与假设**：门控 `form` 默认 **材料型**；未给 due ⇒ `planned_due=phase.planned_end` 写入 `assumptions`（不追问）；助手推断须进 `assumptions`，禁止静默 |
| C34 | **`boundary.deferred` v1 不允许**：边界边必须进 Plan 且在同一次 commit 内做完；不得声称图齐却缺 M5 边 |
| C35 | **无写权**：仍出**只读**确认单 + 顶栏标明不能落库；`status=blocked`；commit 硬拒绝 |
| C36 | **PQ /「帮我创建」+ enrichable** → 直接 **Plan-B**，开场固定句「按补空壳确认单」再出表 |
| C37 | **Plan 持久化**：skstudio 短生命周期存 `plan_id`（绑 sender+会话，TTL≈7 天或 commit 后归档）；续跑依赖 Plan+Run，不靠模型上下文 |
| C38 | 独立里程碑 **M6**（不挡 M0–M5 现网）；新增 propose/commit（及可选 Plan 存储）API/工具 |
| C39 | **M6 工程默认**（2026-07-28 钉死 · 详 §4.9）：同意=Agent「同意」+ fingerprint；服务端出表；mutate 新 action；Plan+Run 同表；进程内执行器+幂等；A/B 共商必须经 commit；入口一次授权整链；CI 合成夹具；M6-1b=CI DoD；签收文档放 M6-2；revise=整单替换；切片 **M6-0 / M6-1a / M6-1b / M6-2** |
| C40 | **M6-create（2026-07-29）**：Mode A **必须**实现 `commit_plan`（去掉 `create_commit_not_in_m61b` / 501）；微序 = `goal_mutate` create + 与 B 同 §3.5（`phases[0]` **必须** `patch_shell`） |
| C41 | **整单含系统起止占位**：确认单须展示派生的 **开始 / 结束** 有效窗（及专项 `period_*`）；业务阶段共商窗须夹在其间；**不**把开始/结束当用户可改业务阶段 |
| C42 | **排期预检（A/B 同一套 · 归入 validate）**：超专项窗、与起止重叠、段间交叉 → `ok=false` + issues；**不得**出可同意确认单；**禁止**「先同意再撞 GE 排期」；**禁止**自动延专项（C43） |
| C43 | **超专项周期**：只允许 **改日期后才能同意**；**禁止** create/enrich 路径自动延长专项；另议延专项不在本切片 |
| C44 | **失败续跑**：同 `plan_id`+fingerprint 可从 Run 失败步继续（C11）；create 已成功则续跑 **禁止**二次 create |
| C45 | **写权**：A 建项鉴权 **对齐现网**「专项下新建项目」/ `goal_mutate` create（含子树 steward · 评审员 BFF 等现网规则） |
| C46 | **SKILL/SOUL 与代码同发**：禁止再出现「create commit 暂未开放」类绕路建壳话术；门禁与竖切同切片 DoD |
| C47 | **Harness · 门控须有生产者**：每个业务 `GateSpec` 须被本阶段恰好 1 个非 `start_sign` 任务的 `produces_gate_key` 引用；否则 validate **`ok=false`**（`gate_without_producer` / `gate_multiple_producers`） |
| C48 | **Skill · 结构共商门闩**：出审查前须对话收齐阶段 / 每阶段门控 / 每门控产出任务 /（N≥2）衔接；仅名·PM·日期·描述 **不够**；未齐 **禁止** validate/commit 与臆造硬调；`gate_without_producer` **禁止**盲改字段名或改走 enrich 绕路（曾 SKILL **0.3.2**；M7 改口见 C49） |
| C49 | **M7 · 双独立 tool（2026-07-29 钉死）**：Hermes 仅 **`governance_project_plan_validate`** + **`governance_project_plan_commit`**；**作废** `propose_plan` / `revise_plan` / `commit_plan`（及 mutate 上同名 action）。A/B 共用。全新发版，**无旧路径迁移** |
| C50 | **Validate 契约**：统一回执 `{ok, issues[], plan_id?, fingerprint?, confirmation_markdown?, status?}`；**一次尽量返回全部 issues**；**落库** Plan。**对外主路径禁止**「第一个 schema 400 截断、排期另袋」——一律进 `issues[]`（内部可分段收集）。`ok=false` → 问题清单（+可选草稿表）；`ok=true` → 可同意确认单 + fingerprint |
| C51 | **迭代节奏**：结构共商齐 → validate →（不过则与用户改正 Plan → 再 validate）×N → **仅** `ok=true` 确认单需整单「同意」→ commit。改正后可立即再 validate；同意绑 fingerprint |
| C52 | **Commit-once**：入参 **只** `plan_id` + `fingerprint`（+ `user_confirmed`）；**禁止** 未审/未绑 fingerprint 的裸 JSON 落库。半截失败 → **同 plan 续跑**（C11/C44），**禁止**二次 create。执行器仍含 **boundary + notify**（整单结果一次交付） |
| C53 | **强禁逃逸 · 方案 A（2026-07-29）**：GA Hermes **工具面只暴露** `governance_project_plan_validate` + `governance_project_plan_commit`（PC 共商建/补完整执行图）。**不对 GA 注册/启用**用于替代该路径的 `goal_mutate` create 与逐步 invent 写图；**PQ** 在跑单次修复仍用原子 `project_mutate`（分流）。skill 文案同步，但 **以 tool 表面裁剪为机制真源** |
| C54 | **审查全面覆盖 · 本切片必检清单（2026-07-29）**：见 §4.11.7。必检 = schema/mode/op、produce、boundary/handoff、open_questions、排期三件套、due∈阶段、写权/blocked、username 可解析（PM/任务负责人）、enrichable 再检（B）。**后置 OUT**：跨项目重名策略细化、通讯录缺失话术产品化、仅 GE 运行时可知且不可预检的约束。新增 Plan 约束须同步进必检表 |
| C55 | **禁止结构自决**：validate/commit 路径上 Agent **不得**擅自取消用户阶段、压缩进系统「开始/结束」、或把业务交付塞进系统结项槽；超窗等只通过 `issues` 交用户改期/改结构后再 validate |
| C56 | **M7 与代码同发**：SKILL/SOUL/OpenAPI/plugin 与 BFF 双 tool **同切片上线**；文档与实现不得再出现旧 propose 三 action 主路径 |
| C57 | **`program_ref` 对外只谈 name（2026-08-01 · Chrome 实测钉死）**：产品假设 **专项（program）名全局唯一**。Agent/Plan/Skill/确认单 **只使用 `program_ref.name`**；**禁止** 向模型或用户索要、展示、共商 `program_ref.id`。**validate 与 commit** 由 **服务端内部** 将 name 解析为 id 并固化（写权/可见性仍按现网 C45）；fingerprint 用固化后的 Plan。**禁止**「validate 过、commit 再要 id」假通过。0 命中 → `ok=false`，对用户话术 **「没有找到专项：{name}」**（不必附候选列表/id）。Skill：**嵌入最小合法 Plan 样例**（`program_ref: { name }` + schema 必填）；**不**把 `governance_scope` 当作 validate 前置。动机：实测假通过与 schema 空转。 |
| C58 | **validate 失败分流 + 结项门 A1 + 行为契约（2026-08-01 · Chrome WEAK 竖切钉死 · v0.1.28 工程默认）**：`issues[]` 须标 **`owner`（agent\|user）** 与回执级 **`next_action`**。**仅** schema/形状（`owner=agent`）允许 Agent 静默改 Plan 再 validate；**凡 `owner=user` / `next_action=ask_user` 必须停问用户**，**禁止**为过校验擅自新增用户未确认的阶段/门控/任务。**结项（A1）**：`boundary.end_entry_gate_key` **必须等于**末业务阶段某一**用户指定**的业务退出门控（该门控仍须有业务 produce · C47）；**禁止**另造「结项前置」门再自补任务；commit E1 将该门 → 系统「结项复盘」。系统开始签收任务 owner=**PM**（C23）；**不**强制其它业务任务默认 PM。**不做**依赖 plugin 轮次的 validate 硬限流——靠 `next_action` + Skill/tool 纪律；整体同发。failed_partial：**必须**贴 deep_link + 残留说明。细则 §0.3。 |
| C62 | **冒烟 hard=session deep_link + 纯文本深链 + wecom 样例（2026-08-01）**：Chrome hard 以 session/GE `deep_link` 为真源（UI 无 `/execution/` 仅 WARN `deep_link_ui_missing`）；c57 否定句「不用/无需…uuid」**不**计 solicitation；Skill **0.5.6** committed/failed_partial **必须**贴一行纯文本 `/execution/projects/<uuid>?tab=define`；样例 `pm_username`/`owner_username` 用完整登录名（如 `wecom:example`）。细则 §0.7。 |
| C64 | **发送者短名别名（仅自己）**：Plan `pm_username`/`owner_username` 无法解析 **且** 等于 `sender` 去前缀短名时，归一为 `sender.username`；**禁止**全局模糊匹配他人。OpenAPI pc-plan **0.2.6**。 |

<a id="c57-program-ref-name"></a>

### 0.2 C57 展开（normative · **C57-M1 已实现** · M2 运行面同发）

| 项 | 决议 |
| -- | ---- |
| 唯一性 | **专项名全局唯一**（解析：全局 program 名 → 至多一个内部 id） |
| 对外（模型/用户） | **只谈 name**；Skill/样例/确认单 **不出现 id**；不教模型填 id |
| 对内（BFF） | validate/commit **内部** name→id 并固化；执行器挂父子用 id |
| validate 失败（用户） | 「没有找到专项：{name}」 |
| validate 失败（机器） | `program_not_found`（不存在/名不对）；写权不足另码 `program_create_forbidden`（对用户仍可同一句或「无权在该专项下新建」——实现任选，**码必须可测**） |
| 确认单 | **只展示专项 name** |
| commit | 不再要求客户端传 id；入口 **统一再 resolve**（与 validate 同规则）；缺 name 才拒 |
| fingerprint | **含**固化后的内部 id；同意须绑 **最后一次** `ok=true` 的 fingerprint |
| 存量 Plan | 仅有 name、无 id 的旧行：commit 再 resolve，允许续跑；不强迫用户重开共商 |
| HTTP 回执 | Plan JSON **可**含内部 id（日志/排障）；Skill/确认单/对用户话术 **永不提** |
| scope | **非** validate 前置 |
| Skill | **一份能过 validate 的最小完整 create 样例**（N=2 + handoffs + boundary + 双门控 produce + `program_ref.name`） |

### 0.2.1 C57 工程默认与测试 DoD（2026-08-01 钉死）

| # | 默认 |
| - | ---- |
| E1 | fingerprint 在 name→id 固化**之后**计算 |
| E2 | commit 不依赖客户端 id；依赖 fingerprint + 服务端 resolve |
| E3 | 对用户不附专项候选列表、不展示 uuid |
| E4 | 本切片 **pytest 必绿**；Playwright/Chrome 竖切 **可选**（不挡合入） |

| ID | 意图 | 期望 |
| -- | ---- | ---- |
| PC-REF-01 | 仅 `program_ref.name`（无 id）合格 Plan | ✅ validate `ok=true`；确认单含专项 **name** |
| PC-REF-02 | 同上 → commit | ✅ 存盘 Plan 含固化 id；deep_link |
| PC-REF-03 | 错误专项名 | ✅ `program_not_found` +「没有找到专项：…」 |
| PC-REF-04 | 无写权专项 | ✅ `program_create_forbidden`；commit 拒 |
| PC-REF-05 | 旧 fingerprint | ✅ `plan_fingerprint_mismatch` |
| PC-REF-06 | 仅 name 的已存 Plan 再 commit | ✅ commit 入口 re-resolve |

<a id="c58-validate-ownership"></a>

### 0.3 C58 展开（normative · **规格+工程默认冻结 · 未实现**）

> **Chrome 实测锚（2026-08-01）**：`PC-PW-202608010303` · Playwright → Chrome · 脚本 **WEAK 12/15**。C57 name 解析已过；Agent 对 `ok=false` **连打 validate×9 自补**（含为 `gate_without_producer` 发明「结项复盘」）→ 用户未介入 → 首次 commit `failed_partial` / `produce_prerequisite_loop`。根因：**「改正再 validate」歧义** + **结项门与 C47 交叉**。  
> **v0.1.28 工程默认**：结项 **A1 且须用户指定**；**不做** plugin 轮次硬闸；**整体同发**；pytest 挡合入、Playwright 签收。

#### 0.3.1 产品 / 工程决议（已拍板）

| 项 | 决议 |
| -- | ---- |
| Issue 分流 | **Schema/形状 → Agent 自修**；**业务缺口 → 必须用户共商**（`next_action=ask_user`） |
| 结项门 | **A1**：`end_entry_gate_key` = 末阶段某一**用户指定**的业务退出门控（有 produce）；**禁止**另造结项前置门 + 自补任务 |
| 系统起止负责人 | **仅**系统开始签收 / 结项边界相关任务要求 **PM**（C23–C25）；**不**强制其它业务任务默认 PM |
| 连打抑制 | **不做**依赖「用户消息轮次」的 BFF/plugin 硬限流；靠 `owner`/`next_action` + Skill/tool 文案；Agent 与用户合理互动后轮次不是主问题 |
| 发版 | **整体同发**（BFF + OpenAPI + Skill/SOUL/plugin + 测试） |
| 测试 | **pytest 必绿挡合入**；Playwright/Chrome **签收用**，不挡合入 |

#### 0.3.2 Issue 归属白名单（实现真源）

| `owner` | 典型 `code`（非穷尽；新增码须归类） | Agent 行为 |
| ------- | ----------------------------------- | ---------- |
| **agent** | `invalid_plan_schema`；可归因「未贴 Skill 样例」的形状错（缺 `key`/`op`/`planned_*`、误用 `stages`/`pm`、单数 `gate` vs `gates` 等） | 对照 Skill 最小样例改 JSON；**可**再 validate（建议同轮自修收敛，勿刷屏） |
| **user** | `gate_without_producer`（业务门控）；`gate_multiple_producers`；`program_not_found`；`program_create_forbidden`；排期类；`end_entry_*` 若因**用户未指定**结项门；缺阶段/门控/衔接；写权/blocked | **停**；展示 `issues[]`（用人话）；**禁止**再 validate；**禁止**发明任务/门控/阶段 |
| **禁止** | — | 为过 `ok=true` 新增用户未确认的业务节点；另造「结项前置」并自补 produce；与系统「结项复盘」同名冲突 |

回执扩展（C50 兼容超集）：

```text
{
  ok, issues[], plan_id?, fingerprint?, confirmation_markdown?, status?,
  next_action: "fix_schema" | "ask_user" | "show_sheet",
  issues[].owner: "agent" | "user",
  issues[].needs_user: boolean
}
```

**C51 改口（C58）**：「改正再 validate」=  
- `next_action=fix_schema` → Agent 自修后再 validate；  
- `next_action=ask_user` → **必须先问用户**；用户补充前 **禁止**再 validate。

#### 0.3.3 结项 A1 · 系统起止（与 C25/C47 对齐）

| 规则 | 说明 |
| ---- | ---- |
| A1 | `boundary.end_entry_gate_key` **必须**指向末业务阶段内、用户共商指定的**业务退出门控**；该门控适用 C47（须有同阶段非 `start_sign` 任务 produce） |
| A2 | **禁止** Plan 内再增加仅服务结项、无业务语义的「结项前置」门，再为其自补 produce 任务 |
| A3 | commit **E1**（C25）：将该 `end_entry_gate_key` → `add_prerequisite` → 系统任务「结项复盘」；**不**在 Plan 里发明同名业务任务 |
| A4 | 共商清单须收齐：「哪扇末阶段门控作为结项入口（end_entry）」——**用户指定**；未指定 → `ok=false` + `needs_user`（码如 `end_entry_unspecified` 或复用 `end_entry_gate_unknown`） |
| A5 | `start_sign_task`：执行器按 C23–C24 注入；owner=**PM**；**不对用户开「请造启动任务」业务题**（可确认 PM 签收即可） |
| A6 | 业务任务负责人：共商有则用用户值；**不**服务端一律默认 PM |

#### 0.3.4 行为契约（替代轮次硬闸）

| # | 契约 |
| - | ---- |
| B1 | Skill/tool：**`ask_user` 时禁止连续调用 validate**；只展示 issues 并提问 |
| B2 | schema 自修：允许 Agent 在展示给用户前收敛；**禁止**把业务缺口当成 schema 自修 |
| B3 | **OUT（本切片不做）**：plugin 注入 turn_id、BFF 按「无用户消息」拒第 3 次 validate |
| B4 | 若日后连打复现，再议轻量闸（须不强迫改会话协议） |

#### 0.3.5 failed_partial / 孤儿项目（体验）

| # | 要求 |
| - | ---- |
| F1 | commit `ok=false` 且已有 `project_id`/`deep_link` → Agent **必须**对用户展示深链 +「已落库步骤 / 失败步」；**禁止**只报错不给链 |
| F2 | 话术引导：同 plan 续跑或打开 GE 查看残图（C11/C44）；**禁止**二次 create |
| F3 | 冒烟/竖切：工具层有 deep_link 即算可观测；UI 文案亦须含 `/execution/` |

#### 0.3.6 交付切片（整体同发）

| 包 | 交付 | DoD（摘要） | 状态 |
| -- | ---- | ----------- | ---- |
| **契约** | `owner`/`needs_user`/`next_action`；白名单；OpenAPI **0.2.2** | PC-OWN-01～04 | ✅ C58-M1 |
| **结项 A1** | harness/validate/commit 对齐；消自补结项环；Skill 共商句待 M3 | PC-SYS-01～04 | ✅ C58-M2 |
| **行为面** | Skill/SOUL/tool **0.5.2** 文案；禁 ask_user 后连打 | 文案 + profile 测 | ✅ C58-M3 |
| **残留** | F1–F3；Playwright ask-user（签收） | PC-PART-01；PC-PW-ASK | ✅ C58-M4 |

**同发纪律**：BFF + OpenAPI + Skill/SOUL/plugin **同一发版**；禁止只装 0.5.2。

#### 0.3.7 测试 ID（规划）

| ID | 意图 | 期望 | 挡合入 |
| -- | ---- | ---- | ------ |
| PC-OWN-01 | 纯 `invalid_plan_schema` | `next_action=fix_schema`；`owner=agent` | ✅ |
| PC-OWN-02 | 业务 `gate_without_producer` | `next_action=ask_user`；`needs_user=true` | ✅ |
| PC-OWN-03 | 混合 issues | `next_action=ask_user`（user 优先） | ✅ |
| PC-OWN-04 | ok=true | `next_action=show_sheet` | ✅ |
| PC-SYS-01 | 用户指定末阶段业务门为 end_entry 且有 produce | validate 可 `ok=true`（其它合格时） | ✅ |
| PC-SYS-02 | 另造结项前置 + 自补「结项复盘」类任务 | validate **拒**；不得假通过 | ✅ |
| PC-SYS-03 | commit 后 E1 | 用户指定的 end_entry 门控 → 系统结项任务 prerequisite | ✅ |
| PC-SYS-04 | 未指定 end_entry | `ask_user` / 相应 issue | ✅ |
| PC-PART-01 | failed_partial 回执 | 含 deep_link + failed step | ✅ |
| PC-PW-ASK | Playwright | 业务 issue 后 bot 提问；不连打 validate | 签收 |

### 0.4 C59 展开（normative · A/B/C 行为 + 形状诊断）

> **动机（2026-08-01 · C58 后 Chrome WEAK）**：Agent 用单数 `gate` / `produces_gate` 布尔导致门控静默丢失，issues 误报 `*_gate_unknown`（user），ask_user 无法收敛。  
> **决议**：A 机械形状自修（说明一句 + validate≤1，无硬闸）；B 有判断须带推荐并确认；C/未知交给用户；M1 先落地机器真相，M2 同发 `proposal`+Skill **0.5.3**，M3 签收。

#### 0.4.1 行为分档

| 档 | `next_action` | Agent |
| -- | ------------- | ----- |
| **A 机械形状** | `fix_schema` | 改 JSON → **对用户一句话说明** → validate ≤1；仍失败升 B/C |
| **B 有判断** | `ask_user` | **推荐方案**（M2：`issues[].proposal`）→ 停等确认 → 确认前禁止 validate |
| **C 真缺口 / 未知码** | `ask_user` | 只问缺项；禁止编造节点 |

#### 0.4.2 交付切片

| 包 | 交付 | DoD | 状态 |
| -- | ---- | --- | ---- |
| **诊断归属** | 窄形状检测；空 gates→`invalid_plan_schema`；归属表 A/B/C；OpenAPI **0.2.3** | PC-SHAPE-01/02；PC-OWN-05 | ✅ C59-M1 |
| **提案+行为面** | `proposal`；Skill/SOUL/plugin **0.5.3** install | PC-PROP；profile 测 | ✅ C59-M2 |
| **竖切** | smoke assisted 确认；Chrome | PC-PW-C59 | ✅ C59-M3（脚本；Chrome 签收不挡） |

**同发纪律**：0.5.3 已与 M1 BFF 同发；禁止只装 Skill（本切片已关闭）。

#### 0.4.3 测试 ID（C59）

| ID | 意图 | 期望 | 挡合入 |
| -- | ---- | ---- | ------ |
| PC-SHAPE-01 | 单数 `gate` / 无 `gates` | `invalid_plan_schema`；`fix_schema`；非仅 `*_unknown` | ✅ |
| PC-SHAPE-02 | 合法 gates + 错 handoff key | `handoff_gate_unknown`；`ask_user` | ✅ |
| PC-OWN-05 | `name_required` | `owner=agent`；`fix_schema` | ✅ |
| PC-PROP-01 | `handoff_gate_unknown` + proposal | `ask_user`；proposal 含候选 key | ✅ |
| PC-PROP-02 | `end_entry_unspecified` + proposal | `ask_user`；proposal 提示末阶段门 | ✅ |
| PC-PW-C59 | Chrome assisted | 脚本就绪；实跑签收 | 不挡 |

### 0.5 C60 展开（normative · 低垂果 · Mode A only · **规划冻结**）

> **共识（2026-08-01）**：空壳/Mode B **OUT**。样例策略 **A+C**（SOUL 极短骨架 + `fix_schema.proposal` 可粘贴补丁）。签收：**硬** = `/new` 后会话不回跳 + commit + deep_link；**软** = validate≤2 / 无 assisted（加分不挡）。gateway `/new` 竞态已在 `v26.11.39` 修好。  
> **切片纪律**：逐 MS 合入；M1/M2 pytest·静态挡合入；M3 Chrome 硬门槛签收。

#### 0.5.1 交付切片

| 包 | 交付 | DoD | 状态 |
| -- | ---- | --- | ---- |
| **C60-M1 · 对话入口（A）** | SOUL 挂极短最小 Plan 骨架（自 Skill 0.5.3 裁短）；install | PC-SOUL-01；profile 测 | ✅ C60-M1 |
| **C60-M2 · 回执侧（C+确认单）** | `invalid_plan_schema` 等 A 码 `proposal` 含可粘贴片段；确认单/展示强调 commit 工具名 | PC-PROP-A01+；确认单文案测 | ✅ C60-M2 |
| **C60-M3 · 签收面** | smoke 等终态 + 假阴性收敛；signoff 勾 C59/C60；Chrome 硬门槛 | PC-PW-C60 | ✅ C60-M3 |

#### 0.5.2 C60-M1 · 对话入口（A）

**实现**

| # | 仓库 / 路径 | 动作 |
| - | ----------- | ---- |
| 1 | `platform-docs/.../SOUL.md` | 在「新建项目」主闭环段后增加 **「Plan 形状骨架（必遵）」**：从 Skill **0.5.3** 最小合法 JSON **裁短**（约 10～20 行）：保留 `mode/name/pm_username/program_ref.name/phases[].{key,name,op,planned_*,gates[],tasks[]}/handoffs/boundary.end_entry_gate_key`；占位值可简；注明「整段复制再改值；禁单数 gate / produces_gate 布尔 / project_name」 |
| 2 | `platform-docs/.../README.md`（可选一行） | PC 行注明 SOUL 含短样例 · `/new` 后生效 |
| 3 | skstudio `install_governance_assistant_profile.py` | **无逻辑改**（已 sync SOUL）；合入后本地/现网 reinstall |
| 4 | **不做** | 不改 Skill 大样例真源；不升 OpenAPI；不改 BFF；不碰 Mode B |

**测试**

| ID | 类型 | 期望 | 挡合入 |
| -- | ---- | ---- | ------ |
| PC-SOUL-01 | profile 静态 | SOUL 含 `produces_gate_key` + `gates` + `end_entry_gate_key` + `program_ref` 短骨架 | ✅ |
| PC-SOUL-02 | profile 静态 | 骨架段明示禁止 `project_name` / 单数 `gate` / 布尔 `produces_gate` | ✅ |
| — | Chrome | **本 MS 不要求** | — |

**迭代文档（本 MS 合入时）**

- 本文件 → **v0.1.37**：文首/DOC-SYNC · §0.5.1 M1 ✅ · 修订表一行  
- `PC-PLAN-signoff` 层 B：勾「SOUL 短骨架」  
- Hermes §13.15 / GA 产品设计：**可延到 M3** 一并指针（避免三次改）

#### 0.5.3 C60-M2 · 回执侧（C + 确认单）

**实现**

| # | 仓库 / 路径 | 动作 |
| - | ----------- | ---- |
| 1 | `skstudio/.../ga_project_create_plan_proposal.py` | 为 **A 档**码（至少 `invalid_plan_schema`；可含与形状相关的 `name_required` 加强）生成 **`proposal`**：中文一句 + **fenced JSON 片段**（正确键名示例，如 `gates:[{key,name,planned_due}]`、`produces_gate_key`、顶层 `name`）；可粘贴 |
| 2 | `ga_project_create_plan_validate.py` | 确认 `attach_proposals` 在 `fix_schema` 路径也会挂上（已调用则只扩 proposal 表） |
| 3 | `render_confirmation_markdown` | 脚注已点名 commit；若不足则加粗/独立一行：「回复『同意』后调用 **`governance_project_plan_commit`**」 |
| 4 | Skill / plugin（可选薄改） | `fix_schema` 时 **必须展示 `issues[].proposal`**（含代码块）；不升版也可只靠 BFF |
| 5 | **不做** | 新 issue 码；新 `next_action`；轮次硬闸 |

**测试**

| ID | 类型 | 期望 | 挡合入 |
| -- | ---- | ---- | ------ |
| PC-PROP-A01 | pytest | 单数 `gate` / 空 gates → `fix_schema` + `proposal` 含 `gates` 与可粘贴片段（` ``` ` 或明确 JSON） | ✅ |
| PC-PROP-A02 | pytest | `produces_gate` 布尔类形状 → proposal 指向 `produces_gate_key` | ✅ |
| PC-CONF-01 | pytest | `render_confirmation_markdown` 含字面量 `governance_project_plan_commit` | ✅ |
| — | Chrome | **本 MS 不要求** | — |

**迭代文档（本 MS 合入时）**

- 本文件 → **v0.1.38**：§0.5.1 M2 ✅ · 修订表 · 若 OpenAPI 描述 `proposal` 举例则 **0.2.5**（仅描述增强时）  
- `PC-PLAN-signoff`：PC-PROP-A / PC-CONF  
- Skill 若改文案 → **0.5.4** 同发；否则注明「行为靠 BFF proposal」

#### 0.5.4 C60-M3 · 签收面

**实现**

| # | 仓库 / 路径 | 动作 |
| - | ----------- | ---- |
| 1 | `ga_pc_chrome_smoke.mjs` | `send` 前/后确保 **bot 终态**（无 awaiting/streaming；非 interrupt 瞬态）再发下一句；`/new` 步骤保留为硬前置 |
| 2 | 同脚本 `scoreSkill` | 收敛假阴性：`elicitation_before_validate`（允许结构复述含「确认单」字样但不含 tool 调用）；`mentions_commit_tool_name`（确认单正文或 bot 回复任一即可）；`c57_no_program_id_ask`（收紧误伤「专项周期」等） |
| 3 | 可选 | 报告字段：`session_rotated`（对比 `/new` 前后 `sessions.json` session_id）；`validate_count` 软门槛标注 |
| 4 | **不做** | 为刷 17/17 改 Agent 业务逻辑 |

**测试**

| ID | 类型 | 期望 | 挡合入 |
| -- | ---- | ---- | ------ |
| 静态 | vitest/node | smoke 启发式单测（若已有 `ga_pc_chrome_smoke_c59_static.test.mjs` 则扩） | ✅ 有则 |
| PC-PW-C60 | Chrome | **硬**：`/new` → Session reset → 全程 session_id≠旧 → commit + `/execution/` deep_link | 签收（不挡 CI） |
| 软指标 | Chrome 报告 | validate≤2；无 `assisted_*` → 加分记录 | 不挡 |

**迭代文档（本 MS 合入时）**

- 本文件 → **v0.1.39**：**C60 现网** · DOC-SYNC 全绿 · §0.5.1 三包 ✅  
- `PC-PLAN-signoff`：C59/C60 Chrome 实跑 ☑（记 tag/项目名/deep_link）  
- Hermes §13.15 / GA 产品设计 / README：C60 一行指针  
- 修订表 + 简短评价（硬门槛 / 软指标实测值）

#### 0.5.5 非目标（C60）

- Mode B / enrich / 空壳  
- validate 轮次硬闸、新 tool、新 `next_action`  
- 生产机大切（另开窗口；本切片以本地 Mac + tag 为准）

### 0.6 C61 展开（normative · 软效率 · Mode A only · **规划冻结**）

> **共识（2026-08-01）**：首轮 validate 常因 `handoffs.to_phase_key` 触发 `fix_schema` → validate≥3 + assisted。C61 = SOUL 双阶段合法 handoff + Skill **0.5.5** 红线 + smoke `self_heal` 再 assisted。**BFF 不动**；无硬闸；软未过不挡合入。  
> **切片纪律**：逐 MS 合入；M1/M2 静态测挡合入；M3 Chrome 硬门槛签收、软指标记数。

#### 0.6.1 交付切片

| 包 | 交付 | DoD | 状态 |
| -- | ---- | --- | ---- |
| **C61-M1 · SOUL handoff** | 双阶段短骨架 + `to_task_key`；禁 `to_phase_key` | PC-SOUL-01/02 扩 | ✅ C61-M1 |
| **C61-M2 · Skill 0.5.5** | 红线禁 `to_phase_key`；fix_schema 后再 validate≤1 | profile 0.5.5 | ✅ C61-M2 |
| **C61-M3 · smoke/Chrome** | `self_heal` nudge → assisted；`soft_ok`；PC-PW-C61 | 硬 PASS；软记数 | ✅ C61-M3 |

#### 0.6.2 非目标（C61）

- BFF 新 issue 码 / 新 `next_action` / validate 硬闸  
- Mode B / enrich  
- 软指标挡 CI 或挡硬签收  

### 0.7 C62 展开（normative · 硬真源冒烟 + 纯文本深链 + wecom 样例 · Mode A only）

> **共识（2026-08-01）**：生产 c62b 已落库且 soft_ok，但脚本 hard FAIL（UI 无 `/execution/`）+「不用 uuid」假阴性；Skill/SOUL 样例仍裸 `victor`。C62 = 冒烟 hard 认 session `deep_link` + c57 否定句白名单 + Skill **0.5.6** 纯文本深链 / `wecom:` 样例 + 生产签收。**BFF 不动**（短名别名属 C64）。

#### 0.7.1 交付切片

| 包 | 交付 | DoD | 状态 |
| -- | ---- | --- | ---- |
| **C62-M1 · smoke harness** | session deep_link hard；否定句不 solicitation；`deep_link_ui_missing` WARN | 静态测 | ✅ C62-M1 |
| **C62-M2 · Skill/SOUL 0.5.6** | 纯文本深链红线；样例 `wecom:example` | profile 测 | ✅ C62-M2 |
| **C62-M3 · 生产签收** | install + PC-PW-C62 Chrome hard_ok | 硬 PASS；软记数 | ✅ C62-M3 |

#### 0.7.2 非目标（C62）

- BFF 用户名别名（→ C64）  
- 运维清僵尸 / session 权限正规化（→ C63）  
- scope/DQ 短冒烟（→ **SHIP 已签收** · 见 §0.10；**非**产品编号 C65）
- validate 轮次硬闸  

### 0.8 C63 展开（运维卫生 · **不升 Skill**）

| 项 | 状态 |
| -- | ---- |
| 清 Jun10 headless Chrome / Jun14 kanban 僵尸 | ✅ |
| systemd 去掉 `RestartMaxDelaySec` / `RestartSteps`（CLI + 现网 unit） | ✅ |
| devops 只读 ACL → `governance-assistant/sessions/`；冒烟直 rsync（`/tmp/ga_sessions_pub` 仅 fallback） | ✅ |
| 运维文档 | [运维-Hermes-skstudio-集成.md](../../platform_docs/运维-Hermes-skstudio-集成.md) **§9.6** |

### 0.9 C64 展开（BFF · sender 短名别名）

| 项 | 决议 |
| -- | ---- |
| 触发 | 用户名 **无法**直接解析 |
| 匹配 | 仅当 Plan 值 = sender 去前缀短名（如 `victor` ↔ `wecom:victor`） |
| 动作 | 归一为 `sender.username` 后再过校验 / 入 Plan |
| 禁止 | 全局短名猜人、匹配他人 |
| OpenAPI | pc-plan **0.2.6** |
| Skill | **不**改主流程（样例已是 `wecom:`） |

### 0.10 scope/DQ 短冒烟（SHIP · 已签收 · **不升 PC Skill**）

> **编号说明**：v0.1.46 修订表曾将本包误标为「C65」；**产品编号 C65 自 v0.1.47 起专指 GA/Web 建项同路径（§4.6.1）**。

| 项 | 状态 |
| -- | ---- |
| 脚本 | `skstudio/frontend/scripts/ga_scope_dq_smoke.mjs` |
| Hard | scope 无 `execution_footprint`；DQ 有 `overall`/`logic_status`；Chrome 时 tool 含 `governance_scope`/`governance_goal_dq` |
| 签收表 | [SHIP-三件套](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/SHIP-三件套.md) 冒烟行 · [PC-PLAN-signoff](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-PLAN-signoff.md) scope/DQ 行 |

### 0.11 C65 Agent 展开（v0.1.48 · **与 v29.00.07 同发**）

| ID | 内容 | 状态 |
| -- | ---- | ---- |
| **C65-A1** | Skill **0.5.7**：§C65 专节 + §对用户话术 + 红线重编号 | ✅ 文档 |
| **C65-A2** | SOUL：身份半句 + 主闭环 C65 三句 + **≥0.5.7** | ✅ 文档 |
| **C65-A3** | `project-duplicate` 红线 C65 + 完成话术 | ✅ 文档 |
| **C65-A4** | README 验证行 · `eval_governance_assistant.py` C65-AGENT | ✅ 文档 |
| **C65-M1** | BFF `_create_project` → `create_project_with_note` | ✅ pytest T01–T03 |
| **C65-M2** | install Skill 0.5.7 + gateway restart | ✅ 本地 · 生产待 deploy |
| **C65-M3** | **GA-PC-K27-AGENT-T01** 对话探针 + Chrome 知识库无二次确认 | ☐ 发版签收 |

---
## 1. 问题与动机

监管者与 GA 共商后要落地执行图（阶段为何、门控验什么、谁产出、跨阶段衔接）。现网仅「方案」空壳 + Web Canvas；SOUL 堆规程会臃肿；mega-tool 破坏 G29/一次一项。

**解法**：skill = 共商 playbook；mutate = 原子写；结果面 = `open_ge_embed`；成员感知 = **M4 域侧欢迎 inform**（非 GA 直调 inform tool）。

**M5 动机（2026-07-28）**：GE 创建时已 seed「开始/`项目启动`」「结束/`结项复盘`」，但 **启动签收路由故意不 seed**（留给 Canvas）；PC 旧规程只建业务↔业务 handoff，又把「禁动系统起止」理解成碰不得系统 GI。结果：共商图业务内通、**开始出口 / 结束入口断**——`项目启动` 无签收人则无法提交，首业务阶段永不 `active`；结束侧缺少「末业务交付物 → 结项任务」的任务级边（阶段级开门仍在）。M5 用 **PC 必补边界边** 闭合，不改 GE。

**M6 动机（2026-07-28 · 生产案例）**：用户「数据基座筹备」补空壳时，助手已判 enrichable，但未钉死 Plan：同意后仍追问、`patch_phase` 参数 400 不澄清、改打 **`add_phase` 顶替改名复用**（日程冲突连败）、最终甩手动。根因：**规程在 skill 文案里 = 建议而非约束**。M6 将共商升为 **可 assert 的 Plan + 表格确认单 + commit 执行器**，让错误路径「没机会飘」。

**M6-create 动机（2026-07-29 · 生产案例「慢病平台1.0」）**：用户与 GA 共商四阶段（设计/开发/测试/打磨）并整单同意后，`mode=create` 的 `commit_plan` 返回 **501**（文档曾写后置、skill 仍写可 commit）→ Agent 绕路建壳 → 二次 enrich 再确认 → 再撞 **系统开始/结束占位** 与 **专项季度窗**（打磨超 9/30）。根因：**create commit 半上线** + **propose 未预检排期/起止**。本切片补齐 A 路径，并让确认单成为「含系统起止的合格整单」。

**M7 动机（2026-07-29 · 生产案例「空中影像科」）**：用户共商四阶段（设计/实现/测试/打磨一月）后，Agent **未**用合格 Plan 走服务端全量审查，却在 mutate schema 碰壁后 **绕路** `goal_mutate` 建壳 + 逐步 invent 建图；打磨超专项窗（至 10/26 vs 专项 9/30）事后才发现，再 **自作主张** 放弃打磨阶段、把「优化打磨并上线」塞进系统 **结束**。根因：**审查与落库耦在同一 mutate 叙事里、模型可逃逸**；skill 红线挡不住。M7 将审查升为 **独立 validate tool（全量 issues）**，落库升为 **独立 commit-once（仅 fingerprint）**，并 **强禁逃逸**。

**C57 动机（2026-08-01 · Mac Chrome / Playwright 全新建竖切）**：结构共商与 create-only 门闩合格，但 Plan 多轮 schema 空转；且 **validate 接受 `program_ref.name` 即 `ok=true`，commit 却硬要 `program_ref.id`** → 假通过后再查 scope 重审。根因：**对外契约与落库门槛不一致** + Skill 缺最小合法样例、仍暗示先 scope/填 id。C57 规定对外只谈 name、服务端解析固化、Skill 嵌入可过审样例。

**C58 动机（2026-08-01 · 同日 Chrome 复测 WEAK）**：C57 name→id 已通，但 Agent 把「据 issues 改正再 validate」做成 **连打自补**（schema 试错 + 为系统结项门发明「结项复盘」），用户未介入；validate 假通过后 commit `failed_partial`（`produce_prerequisite_loop`）。根因：**失败归属未机器化** + **系统结项与 C47 交叉** + **无硬闸**。C58 规定 issue `owner`/`next_action`、系统结项方案 A、硬限连打、failed_partial 必出深链，并强制用户介入业务缺口。

---

## 2. 目标与非目标

| 编号 | 成功标准 |
| ---- | -------- |
| G1 | A：共商 → validate ok → 同意 → commit（建壳+补图）→ Host 进 GE |
| G2 | B：系统空壳 → 不二次 create → 改名「方案」+ 补图 → 深链 |
| G3 | 非 enrichable / 未同意 → 不 mutate |
| G4 | SOUL 保持瘦；skill + install 可同步 |
| G5 | `patch_phase` / `shell` / `assignee_username` 契约可测；PC-T01 可签收 |
| G6 | Agent **无需**新读图 tool 即可完成 id 链（C13/C15 + 各步 `entity.id`） |
| G7 | **M4**：图就绪后 S1 成员在「我的助手」收到统一欢迎信 + 可点深链；建壳无信；GA overlay 仍禁用 `inform` |
| G8 | **M5**：落库后 `项目启动.eligible_signers` 含 PM；末业务退出门控 ∈ `结项复盘` 任务的 prerequisites；PC-T01 边界步可签 |
| G9 | **M7**：共商建图 **只**经 validate（全量 issues）迭代至 ok → 整单同意 → commit-once；**无**绕路建壳/逐步 invent/塞系统结束（逃逸=A · C53） |
| G9a | **M6（历史成功标准 · 仍适用执行器行为）**：N=1 enrich（方案→改名+窗+一门控）表格确认 → commit 成功贴 deep_link；错误参数停失败步；B 路径无法用 add 顶替 patch_shell |
| G10 | **M6-create（历史 · 能力仍在执行器）**：Mode A 一次合格 Plan→同意→commit 落库成功；确认单含开始/结束占位；不合格日期不可同意；A/B 同一套排期预检（现经 validate） |
| G11 | **C58**：业务 `needs_user` 后 Agent **停问用户**再 validate；结项门 **用户指定**（A1）；不另造结项前置自补；failed_partial 必出 deep_link；**无**轮次硬闸 |

非目标：C7（含 GA 不启用 inform toolset）；**改 GE seed / PQ 系统边评分**（C27）；**改 GE 开始/结束派生算法本身**（只用其结果做占位与预检 · C41）；**自动延长专项周期**（C43）；通用意图框架；M6 v1 不做逐行勾选 UI 卡片（对话表格即可）。

---

## 3. 需求规范（Normative）

### 3.1 角色与触发

| 项 | 规则 |
| ---- | ---- |
| **用户** | `governance_active`；写库另判 mutate 写权 |
| **触发** | 「给专项 X 建项目」「立项」「补齐空壳阶段门控」「共商项目执行图」 |
| **不触发** | 仅评价、改在跑图、activate、个人待办、组织编制 |
| **加载** | SOUL → skill `project-create` |

### 3.2 Mode A / B

| Mode | 条件 | 行为 |
| ---- | ---- | ---- |
| **A · create** | 尚无目标项目实体 | **validate** Plan-A（**含系统起止占位 + 排期预检** · C41–C42）→ `ok` 后表格确认 → **commit**：执行器内 `goal_mutate` create → `shell` → §3.5 补图（C40；细节对模型不可见 · C6） |
| **B · enrich_shell** | 已有项目且 enrichable（§3.3） | **validate** Plan-B（**同一套排期预检** · C42）→ `ok` 后表格确认 → **commit**：跳过 create；`phases[0].op=patch_shell` → §3.5 其余 |

> **M7 主路径 tool**：`governance_project_plan_validate` → 整单同意 → `governance_project_plan_commit`（C49）。旧 `propose_plan` / `revise_plan` / `commit_plan` **作废**。

### 3.3 enrichable（完全系统预生成）

> GE `create_project` 现网 `Project.status=active`。enrichable **只看结构**，不看 draft。

**同时满足** 方可 B：

1. 调用方具备图编辑权（同 `project_mutate` / GE `_require_graph_editable`）  
2. 非系统业务阶段 **恰好一个**，名 **「方案」**  
3. 该阶段无业务 `gate_items` / `tasks`  
4. 无额外业务阶段；「方案」上无业务 produce / prerequisite  
5. 无业务门控提交 / 签收 / 偏差痕迹  

否则拒绝 B（话术见 skill）。v0.1：**skill 纪律为主**；服务端 `enrichable` 为增强项。

### 3.4 ProjectCreatePlan（Normative · M6；升格原 Intent）

> **真源**：结构化 JSON（可 schema + harness assert）。  
> **确认单**：同一 Plan 的 **人读 Markdown 表格**投影（**非** YAML）。  
> **运行态 Run**：`plan_id` + 已完成步 + 失败码（续跑用）。  
> 旧称 Intent：语义并入 Plan；文档示例若写 Intent 均视为 Plan 投影。

#### 3.4.0 生命周期

```text
探测（pq/scope）→ 结构共商齐（C48）
  → governance_project_plan_validate(plan) → {ok, issues[], plan_id?, fingerprint?, confirmation_markdown?}
  → ok=false：与用户改正 Plan → 再 validate
  → ok=true：出表格确认单 → 用户整单「同意」
  → governance_project_plan_commit(plan_id, fingerprint, user_confirmed)
  → 执行器按 §3.5 微序落库 → notify → deep_link
失败半截 → status=failed_partial；同 plan 续跑（禁二次 create）
```

| 规则 | 说明 |
| ---- | ---- |
| 结构共商齐后 | **必须** validate；**禁止** 未 ok / 未整单同意即写图（C30） |
| `open_questions` 非空 | validate **`ok=false`**；不得出可同意确认单 / 不得 commit |
| 整单同意 | v1 不逐行勾选；改字段 → 改 Plan JSON → **再 validate** → 新 fingerprint → 再出表（C30/C51） |
| 无写权 | 仍出只读表 + 标明不能落库；`blocked`；commit 拒绝（C35） |
| PQ 空壳 / 「帮我创建」且 enrichable | 直接 Plan-B；先说「按补空壳确认单」（C36） |
| 对外回执 | **统一** `issues[]`（C50）；禁止「首个 schema 400 截断 / 排期另袋」作为主路径体验 |

> **历史（M6）**：曾用 mutate action `propose_plan` / `revise_plan` / `commit_plan`；**M7 作废**，语义并入独立 validate/commit（C49）。

#### 3.4.1 Plan 顶层

```text
ProjectCreatePlan
  plan_id: uuid
  plan_version: int
  fingerprint: str                 # 规范化 JSON 哈希；同意绑定

  mode: create | enrich_shell
  status: drafting | blocked | committed | failed_partial
  # 对外以 validate 回执 ok 为准；ok=true ≡ 可同意（废止对外主依赖 status=ready）
  # drafting/blocked 等可作内部/兼容字段

  program_ref: { name, id? }       # A 必填 · **C57**：对外以 name 为准；id 由服务端解析固化（可选回显）
  project_ref: { id, name }        # B 必填（id 必填）
  shell?: {                        # B 必填
    placeholder_phase_id
    placeholder_phase_name         # 通常「方案」
  }

  name?: string                    # A 必填
  pm_username: string              # A/B 必填

  phases: PhaseSpec[]              # ≥1
  handoffs: HandoffSpec[]          # C32
  boundary: BoundarySpec           # M5；C34 不可 deferred
  notify: { enabled: true }

  assumptions: Assumption[]        # 推断默认；须上确认单
  open_questions: string[]         # 未清空 → validate ok=false
```

```text
Assumption
  key: string                      # 如 "phases.p0.planned_start"
  value: any
  source: inferred | user_confirmed
  display: string                  # 确认单「假设」行文案
```

#### 3.4.2 子结构

```text
PhaseSpec
  key: string                      # 稳定引用 p0/p1…
  op: patch_shell | add            # 见编译约束
  name: string
  why?: string                     # 确认单「说明」列；短句 ≤40 字
  planned_start / planned_end      # YYYY-MM-DD
  gates: GateSpec[]
  tasks: TaskSpec[]

GateSpec
  key: string
  name: string
  form: material | status          # **默认 material**（C33）
  planned_due: date                # 默认 = 本阶段 planned_end → assumptions（C33）
  why?: string

TaskSpec
  key: string
  title: string
  owner_username: string
  produces_gate_key?: string       # 同阶段 gate.key；**每个 GateSpec 须恰好被一个任务引用**；start_sign 必须省略
  role?: produce | start_sign      # start_sign = M5 启动签收
  why?: string

HandoffSpec
  from_gate_key: string
  to_task_key: string

BoundarySpec
  start_sign_task_key: string      # → 任务 role=start_sign 或可复用的 PM 任务
  end_entry_gate_key: string       # 末业务阶段退出门控
  # deferred: 禁止（C34）
```

系统实体 **`项目启动` / `结项复盘`** 不进 Plan 列表；执行器用图内固定名解析。

#### 3.4.3 编译与 assert（Harness）

| 断言 | 规则 |
| ---- | ---- |
| 日期 | 均为 `YYYY-MM-DD`；`start≤end`；due∈阶段窗 |
| B 定位 | `project_ref.id` + `shell.placeholder_phase_id` |
| A 定位 | `program_ref` + `name` + `pm_username`；无 project_ref |
| `phases[0].op` | `enrich_shell` ⇒ **必须** `patch_shell`；其后仅 `add`；N=1 无后续（C31） |
| handoff | N≥2 ⇒ ≥1 条且 key 合法；N=1 ⇒ 空（C32） |
| **produce** | **每个业务门控须被本阶段恰好 1 个非 `start_sign` 任务的 `produces_gate_key` 引用**；0 → `gate_without_producer`；≥2 → `gate_multiple_producers`；错阶段 → `produces_gate_mismatch` |
| start_sign | `owner_username=pm` 且无 produce；N=1 无可用 PM 任务 ⇒ **强制**注入「确认启动」（C24）；可将 `start_sign_task_key` 指到已有 PM 产出任务 |
| end_entry | `end_entry_gate_key` ∈ 最后业务阶段 gates |
| enrichable 再检 | commit 前读图；已非 enrichable ⇒ 拒绝 |
| open_questions | 非空 ⇒ 不可 commit |

#### 3.4.4 确认单表格（人读投影 · Normative）

对话中渲染 **Markdown 表格**（可多表），字段与 Plan 一一对应。推荐结构：

**表 A · 总览**

| 项 | 内容 |
| -- | ---- |
| 模式 | 新建 / **补空壳** |
| 项目 | 名 + id（B）或「将新建」 |
| 父专项 | … |
| 专项周期 | `period_start`～`period_end`（约束全部阶段） |
| PM | 显示名（username） |
| 通知 | 图齐后欢迎信（是/否） |
| 状态 | 可落库 / **只读·无写权** / **日期不合格·须改期** |

**表 B · 阶段与交付（须含系统占位行 · C41）**

| 阶段 | 说明 | 窗 | 门控（形态·due） | 任务（负责人·产出） |
| ---- | ---- | -- | ---------------- | ------------------- |
| **开始**（系统） | 占位·不可当业务阶段改 | 派生有效窗 | — | 项目启动（系统） |
| 设计 | … | 07-08～07-31 | … | … |
| … | … | … | … | … |
| **结束**（系统） | 占位·通常占专项末周 | 派生有效窗 | — | 结项复盘（系统） |

> 业务阶段行的窗 **必须** 落在「开始.end < 业务 < 结束.start」且 ⊆ 专项周期；不合规则表 A 状态=须改期，**禁止同意**（C42–C43）。

**表 C · 边界与假设**

| 类 | 内容 |
| -- | ---- |
| 启动签收 | 确认启动 → 项目启动 |
| 结项前置 | 设计文档 → 结项复盘 |
| 假设 | 开始日=今天；due=阶段结束日（默认） |
| 排期 | 若曾超专项/撞起止 → 列出已拒绝的日期与建议窗 |

用户回「同意」= 整单确认（C30）。

#### 3.4.5 N=1 样例（数据基座筹备 · 验收锚）

```text
mode: enrich_shell
project_ref.id: b2f22153-…
shell: 方案 → patch_shell → 设计阶段 · 2026-07-28～08-15
gates: [{ 设计文档, form: material, due: 2026-08-15 }]
tasks: [{ 确认启动, role: start_sign, owner: pm }]   # 强制注入
handoffs: []
boundary: { start_sign_task: 确认启动, end_entry_gate: 设计文档 }
assumptions: [开始日=2026-07-28, due=阶段结束]
```

#### 3.4.6 计划约束

- 业务阶段窗须满足 GE `require_business_phase_window` 与项目/专项日程校验（以 GE 错误码为准）。  
- **须在 `governance_project_plan_validate` 预检**（C42/C54）；与 commit 时 GE 校验一致；不合格 → `ok=false` + `issues[]`，**不得**出可同意确认单。  
- 预检项至少包括：⊆ 专项 `period_*`；不与派生 **开始/结束** 有效窗重叠；业务段间不交叉（对齐 GE `phase_schedule_overlap` / `phase_schedule_outside_program`）。  
- 超专项周期：**只允许改日期**；禁止本路径自动延专项（C43）。  
- 门控 `planned_due` 须落在阶段有效窗内。  
- 用户改阶段窗且未改过 due ⇒ due 随 `planned_end` 重算并更新 assumptions。  
- 共商未给日期时的默认须进 assumptions 并上表，禁止静默。

### 3.4.7（历史别名）ProjectCreateIntent

v0.1.9 及以前的 Intent 字段表并入 §3.4.1–3.4.2；实现与 EVAL 以 **Plan** 为准。

### 3.5 落库顺序（固定 · 由 `governance_project_plan_commit` 执行器驱动）

> **M7**：Agent 只调 commit tool；下列顺序由 **执行器**按已 validate ok 的 Plan 编译结果驱动；**禁止** 同意后逐步 invent action（C6 / C31 / C53）。

| 步 | Mode | action | 说明 |
| -- | ---- | ------ | ---- |
| 0 | A/B | （前置）最近一次 validate **`ok=true`** + 整单同意 | 绑定 `plan_id` / `fingerprint` |
| 1 | A | `goal_mutate` create project | 回执含 `entity` + **`shell.placeholder_phase_id`**（C13）；**仅执行器内** |
| 2 | A/B | `project_mutate` **`patch_phase`** | 仅当 `phases[0].op=patch_shell`；改名+窗；target=`shell` id 或 `phase_name=方案`（C15） |
| 3 | A/B | `add_phase` × (N−1) | 仅 `op=add`；N=1 则 **跳过**；**禁止** 用 add 顶替步 2（C31） |
| 4… | A/B | 见 §3.5.1 微序 | 门控 / 任务 / produce / handoff / **边界边** |
| 9 | A/B | **`notify_project_ready`（M4）** | 图成功后必调（§3.10 / §4.8）；**建壳后不要调** |
| 尾 | — | 回执 | 简述；**`open_ge_embed`**；禁止声称 activate；Plan → `committed` |

纪律：`user_confirmed=true`；一次一项；禁 `goal_mutate` 改执行图；禁改删系统开始/结束（**允许** §3.11 边界 `add_prerequisite` · C26）；参数 400 → **停失败步** + 结构化 detail，**禁止** 换无关 action 盲重试（C11）。

#### 3.5.1 阶段内与跨阶段微序（Normative）

对每个业务阶段（已 `patch`/`add` 之后），**按阶段序**执行：

1. 该阶段全部 `add_gate_item`（name + **planned_due**；target=phase id）→ 记 gate ids  
2. 该阶段全部 `add_task`（title + **`assignee_username`**）→ 记 task ids  
   - **第一业务阶段 · M5**：若尚无 owner=`pm_username` 的任务可作启动签收路由 → 额外 `add_task`「确认启动」、`assignee_username=pm`（**不** `link_produce`）  
3. 该阶段全部 `link_produce`（task → gate；签收路由任务跳过）  

全部阶段完成后：

4. 全部 `add_prerequisite`（业务 handoffs：from_gate → to_task）  
5. **M5 边界**（§3.11）：  
   - `add_prerequisite`：启动签收任务 → gate=`项目启动`  
   - `add_prerequisite`：任务=`结项复盘` → gate=末业务退出门控  

**禁止** 依赖「可选 `patch_gate_due`」补 due——due 在 `add_gate_item` 一次给齐。  
**id 链**：每步以回执 `entity` / 明确字段中的 id 为准；禁止向用户索 UUID。  
**系统实体定位**：`项目启动` / `结项复盘` 用图内 **固定名称**（系统 GI / 系统 Task title）解析 id；禁止向用户索。

#### 3.5.2 部分失败续跑（C11）

- 已 `create` 成功 → 续跑 **禁止** 再 create；改走 B 语义补剩余步。  
- 向用户报告：已完成步 / 失败 action 与错误码 / 下一步建议。  
- 用户再次同意后，从失败步重试或从下一未完成步继续（**同 `plan_id` + Run** · C37）。  
- **M5**：若业务 handoff 已齐、边界边失败 → 续跑只补 §3.5.1 步 5，**禁止**重开 create / 重做已成功 notify（notify 仅整图齐后调一次）。  
- **M6/M7**：Run 记录已完成步；`failed_partial` 后若改 Plan 导致新 fingerprint → 须 **再 validate** 出表再同意。

### 3.6 「方案」处置

| 项 | 规则 |
| ---- | ---- |
| 策略 | **改名复用** 为 `phases[0]` 且 `op=patch_shell`（C4 / C31） |
| 禁止 | 长期保留空「方案」；把系统开始/结束当「方案」；**用 `add_phase` 顶替改名** |
| 删除 | v0.1 **不实现** |

### 3.7 确认与失败

| 项 | 规则 |
| ---- | ---- |
| 确认 | validate **`ok=true`** 的 **表格确认单**（§3.4.4）→ 整单「同意」→ `governance_project_plan_commit` |
| 未同意 / `blocked` / `ok=false` | 禁止任何写图（含 Agent 逐步 invent） |
| 改字段 | 改 Plan → **再 validate** → 再出表 → 再同意（C30/C51） |
| 失败 | §3.5.2；半截同 plan 续跑；禁止盲换 action / 二次 create（C11/C52） |

### 3.8 交接

| 来源 | 规则 |
| ---- | ---- |
| DQ | 一句引导本 skill（C12） |
| PQ | 在跑修复 **不**进本 skill；空壳 / 「帮我创建」且 enrichable → Plan-B +「按补空壳确认单」（C36） |
| Web 向导 | 可出空壳；完整图由本 skill A/B |

### 3.9 示例 Plan（验收参照）

#### 3.9.1 M1 / M5 · N=2 create（PC-T01）

```text
mode: create
program_ref: 「某某专项」
name: 「PC-T01 签收样例项目」
pm_username: <当前用户或共商指定>
phases:
  - { key: p0, op: add, name: 调研, planned_start/end: <专项期内两周>,
      gates: [{ key: g0, name: 调研报告签收, form: material, planned_due: <窗内日> }],
      tasks: [
        { key: t_start, title: 确认启动, owner_username: <pm>, role: start_sign },
        { key: t0, title: 撰写调研报告, owner_username: <x>, produces_gate_key: g0 }
      ] }
  - { key: p1, op: add, name: 落地, planned_start/end: <随后两周>,
      gates: [{ key: g1, name: 落地验收, form: material, planned_due: <窗内日> }],
      tasks: [{ key: t1, title: 完成落地包, owner_username: <y>, produces_gate_key: g1 }] }
handoffs: [{ from_gate_key: g0, to_task_key: t1 }]
boundary: { start_sign_task_key: t_start, end_entry_gate_key: g1 }
notify: { enabled: true }
```

若第一阶段已有 owner=PM 的产出任务，可将 `start_sign_task_key` 指到该任务，**不必**再造「确认启动」。

#### 3.9.2 M6 · N=1 enrich_shell（数据基座筹备锚）

见 §3.4.5；确认单须含「补空壳」总览 + 阶段表 + 边界/假设；同意后 commit 仅走 `patch_shell` + 一门控 +「确认启动」+ 边界边，**零** `add_phase`。

### 3.10 PC-NOTIFY · 成员欢迎 inform（Normative · M4）

#### 3.10.1 时机

| 时点 | 是否发信 |
| ---- | -------- |
| `goal_mutate` **仅建壳** | **不发**（C16） |
| A/B 共商图按 §3.5 / §3.5.1 **落库成功后** | **发**（统一模板） |
| 图链中途失败 | **不发**；续跑成功后再发 |
| 未同意 | **不发** |

#### 3.10.2 收件人（S1）

服务端在通知动作执行时计算（确认单「将通知」预告应与此一致）：

```text
recipients = unique( project.pm_user_id ∪ 非系统业务任务的 assignee_user_id )
recipients -= 本轮同意落库的调用方（sender）
```

- **不**按角色分叉文案（C20）。  
- **不**以空的三分名单为准（名单后配不在 M4 范围；后置可另议「名单入职通知」）。  
- 收件人为空（仅调用方自己是 PM 且无其它负责人）→ **no-op 成功**（仍 200，`notified: []`）。

#### 3.10.3 通道与发送者

| 项 | 规则 |
| ---- | ---- |
| 通道 | BFF **域侧**调用现网 PA inform 投递（写入对方「我的助手」thread） |
| GA | **禁止** 启用 `inform` toolset；Agent **只**调 `governance_project_mutate` 的通知动作（见 §4.8） |
| 发送者 | mutate 请求的 **sender**（本轮同意的调用方 · C19） |
| 文案 | A/B **同一模板**；须含项目名 + 欢迎语 + **项目深链**（与 `open_ge_embed` 同语义：`/execution/projects/{id}?tab=define`） |
| 模板示例 | 「项目「{name}」已就绪，你已是项目成员。欢迎参与推进：{deep_link}」 |

#### 3.10.4 失败与同意

| 项 | 规则 |
| ---- | ---- |
| 建图 vs 通知 | 图已成功则 **不因** inform 失败回滚（C21） |
| 部分失败 | 记录 skipped；回执可含 `notified` / `skipped`；Agent 对人话可一句带过 |
| 同意 | 表格确认单可列将通知名单；整单同意即覆盖通知（C22） |

#### 3.10.5 Skill 职责（M4）

落库微序成功后 **必须** 再调一次通知动作（§4.8）；**禁止** 自行编造已通知而未调工具；**禁止** 引导用户去 PA 手搓 inform 代替本钩子。

### 3.11 PC-BOUNDARY · 系统起止衔接（Normative · M5）

对齐 [需求 §3.4.3](./目标与执行及其组织支撑(需求).md)：系统已 seed `项目启动` / `结项复盘` / `确认结项`；**启动签收路由不 seed**；结项签收路由已 seed。PC **补齐产品期望的可跑边界**。

#### 3.11.1 启动（签收路由 · PM）

| 项 | 规则 |
| -- | ---- |
| 边 | `TaskGateItemPrerequisite`：业务任务 → GateItem **`项目启动`** |
| 签收人 | 该任务 `assignee` **必须** = 项目 `pm`（C23）；禁止用非 PM 业务任务挂启动边「凑齐」 |
| 任务选择 | C24：复用第一业务阶段已有 PM 任务；否则新增「确认启动」（`produces` 空） |
| 禁止 | `启动项目` 任务自环连 `项目启动`（produce+prereq 同 GI）；改系统开始阶段/系统 GI |
| DoD | 读图：`项目启动.eligible_signers` **含** PM 且非空 |

#### 3.11.2 结项（E1 · 任务前置）

| 项 | 规则 |
| -- | ---- |
| 边 | `TaskGateItemPrerequisite`：系统任务 **`结项复盘`** → GateItem = **末业务退出门控** |
| 退出门控 | Plan `boundary.end_entry_gate_key`；缺省 = 末业务阶段 **排序最后** 的业务门控 |
| 签收 | **不变**：仍由系统 `确认结项` → `结项复盘`（PM）；**禁止** E2（业务任务再挂为结项签收路由） |
| 语义 | 解锁 / 图完整；阶段级开门仍有效；通常结束 `active` 时该门控已 `signed` |
| 禁止 | 删改 `确认结项` 边；改系统结束阶段 |

#### 3.11.3 与「禁动系统」关系（C26）

| 禁止 | 允许 |
| ---- | ---- |
| 改名/删系统「开始」「结束」 | `add_prerequisite` → `项目启动` |
| 删/改名系统 Task·GI；断系统 produce | `add_prerequisite`：`结项复盘` ← 末业务门控 |
| | 第一业务阶段新增「确认启动」 |

#### 3.11.4 OUT（M5）

- 改 GE `seed_system_lifecycle_graph` / §3.4.3「启动不 seed」条文  
- PQ 把系统边界计入衔接硬断  
- 存量已跑项目批量补边（本里程碑仅 **新建 A / enrich B**；存量另议）  
- activate / 代提交 `项目启动`

---

## 4. 实现规格（Normative）

### 4.1 切片

| 切片 | 内容 | DoD |
| ---- | ---- | --- |
| **M0** | skill 同步 · 打开 skills · SOUL 路由（文档已备） | PC-INST-* |
| **M1** | C13 `shell` + C14 `assignee_username` + C15/`patch_phase` + OpenAPI/Hermes + A 竖切 | PC-API-* · PC-T01 A |
| **M2** | B + 拒绝 | PC-T01 B/R |
| **M3** | 签收全勾 · 入口文档收口 · 可选 eval | PC-T01 全绿 |
| **M4** | **PC-NOTIFY**：`notify_project_ready` + inform 投递 + 深链 | PC-NOTIFY-* · [PC-NOTIFY-signoff](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-NOTIFY-signoff.md) |
| **M5** | **PC-BOUNDARY**：启动签收（PM）+ 结项 E1 前置 · skill/PC-T01 | PC-STATIC-04 · PC-T01 边界步 · **无**新 API |
| **M6-0** | Harness：schema assert · fingerprint · confirmation markdown · C31/C32/C34 | PC-PLAN-01～03 |
| **M6-1a** | Plan+Run 表 · `propose_plan` / `revise_plan` · 服务端出表 · 无写权 blocked | PC-PLAN-06 + propose/revise API |
| **M6-1b** | `commit_plan` 执行器 · 幂等 · failed_partial 续跑 | PC-PLAN-04/05/07～09 · **CI 即可合** |
| **M6-2** | A/B 必须经 commit · SKILL/SOUL 改口 · `PC-PLAN-signoff` | PC-STATIC-05 · 对话竖切 |

### 4.2 Profile / Skill 安装

| 项 | 规则 |
| ---- | ---- |
| 真源 | `platform-docs/.../skills/governance/project-create/` |
| Install | 对齐 PA `_sync_project_docs_skill`：copytree 同步；`_DISABLED_TOOLSETS` **去掉** `skills` |
| overlay | 去掉 `- skills`（与脚本一致） |
| 白名单 | 只同步本目录；禁止 master/PA 整包 |
| 生效 | reinstall + gateway restart |

### 4.3 SOUL

仅瘦路由（已在 profile SOUL 草案）。**禁止** 贴 Plan JSON / 表格全表到 SOUL。

### 4.4 契约增量（详）

#### 4.4.1 `patch_phase`

| 项 | 规则 |
| ---- | ---- |
| action | `patch_phase`（**≠** `patch_phase_window`：后者只改窗不改名） |
| target | `{ kind: phase, id }` **或** 省略 id 且 `fields.phase_name` 唯一解析（C15） |
| fields | **必填** `name`, `planned_start`, `planned_end`；可选 `phase_name`（解析用，不与新名混淆：解析名 vs 目标名——见下） |

**命名消歧（Normative）**：

- `fields.phase_name` = **查找键**（通常 `"方案"`）  
- `fields.name` = **改成的新名**（Plan `phases[0].name`）  
- 二者不得都空；查找键缺省时必须有 `target.id`

#### 4.4.2 create project 回执 `shell`（C13）

`StructureMutateResponse`（或等价）在 `action=create` + `entity_kind=project` 成功时增加：

```yaml
shell:
  placeholder_phase_id: <uuid>
  placeholder_phase_name: "方案"
```

BFF 在 `_create_project` 后读 GE graph（或 create 返回体）填充；**禁止** 让模型猜 id。

#### 4.4.3 `add_task` · `assignee_username`（C14）

| 项 | 规则 |
| ---- | ---- |
| fields | `title` 必填；**`assignee_username` 与 `assignee_user_id` 至少一**；本 skill 路径优先 username |
| 解析 | 复用 GE/skstudio 用户解析（同 `owner_username`）；失败 → `owner_not_found` 类 400 |
| 对话 | **禁止** 向用户索数字 id |

#### 4.4.4 OpenAPI / Hermes

- `ga-bo-m-pq.openapi.yaml`：enum + `FieldsPatchPhase` + `FieldsAddTask.assignee_username` + **`notify_project_ready`**；version bump  
- `ga-bo-m-structure-mutate.openapi.yaml`：`shell` on create project response；version bump  
- Hermes `skstudio-governance` tool schema 同步；plugin 小版本 +1  

### 4.5 编码触点

| 层 | 路径 | 动作 |
| -- | ---- | ---- |
| Docs | 本文件 · SKILL · PC-T01 · PC-NOTIFY / PC-BOUNDARY · SOUL · overlay · README · Hermes §13.15 · business-os §9 | 文档 |
| OpenAPI | pq + structure-mutate · **M6 propose/commit** | C13–C15 · M4 notify · C29–C38 |
| skstudio | `ga_project_mutate.py` · `ga_structure_mutate.py` · schemas · **inform 投递复用 `pa_inform`** · **Plan store + commit 执行器** | 实现 |
| skstudio | `install_governance_assistant_profile.py` | sync skill · 启用 skills |
| skstudio | `tests/…` | PC-API-* · PC-NOTIFY-* · PC-PLAN-* |
| Hermes | `plugins/skstudio-governance/tools.py` | schema（仍 **无** inform tool）；propose/commit 工具 |

### 4.6 实现默认

| # | 默认 |
| - | ---- |
| I1 | enrichable v0.1 = skill；增强项服务端位 |
| I2 | 无新 `governance_project_graph` tool（C7）；靠 shell + 逐步 entity id + phase_name |
| I3 | M1 绿 = §3.9 量级（2 阶段 + 门控 due + 负责人 + 1 handoff） |
| I4 | **执行图**仍 `_DEFAULT_PROJECT_PHASES`（方案空壳）；**建项编排**与 Web 同：`create_project_with_note`（KB 根 + `project_note_id` + K27 binding · **v29.00.07**） |
| I5 | 失败续跑 = §3.5.2 |
| I6 | 日程 400：据 GE detail 人话解释并请用户 **revise Plan** 日期后重出表 |
| I7 | M4 收件人 **以落库后 GE 图为准**（PM ∪ 业务 task assignee），与确认单预告对齐；不以三分名单为准 |
| I8 | 深链 = `resolve_entity_deep_link("project", project_id, tab="define")` → `/execution/projects/{id}?tab=define`（落地**定义** tab；PQ `open_deviation` 仍默认执行）写入 inform / `open_ge_embed` |
| I9 | **M5**：系统 GI/Task 按固定名从 mutate 链已返回的 graph / 逐步读侧定位；无新读图 tool（C7） |
| I10 | **M5**：`add_prerequisite` 目标阶段序约束仍适用（`项目启动` seq=0 ≤ 首业务；末业务门控 seq ≤ 结束） |
| I11 | **M6**：模型只负责共商填 Plan + 出表；mutate 链只走 commit 执行器 |
| I12 | **M6**：N=1 无 PM 产出任务 ⇒ 编译期强制注入「确认启动」（C24） |

### 4.6.1 GA 建项与 Web 对齐（C65 · v29.00.07 · Normative）

> 真源细则：[release-v29.00.07.md](../../platform_docs/migration/release-v29.00.07.md)

| # | 规则 |
| - | ---- |
| **C65-1** | `ga_structure_mutate._create_project` **必须**调用 `ge_project_note.create_project_with_note`，禁止仅 `create_ge_project`。 |
| **C65-2** | 绑库发生在 **create 一步**（`goal_mutate_create` / `structure-mutate` create project），非 plan commit 末尾 backfill。 |
| **C65-3** | GE 请求体与现网 GA 一致（含 `phases`、生命周期窗）；`project_note_id` 由编排注入。 |
| **C65-4** | 标题冲突 → **409** `note_title_conflict`（与 Web 同）；skill 引导 revise Plan 项目名。 |
| **C65-5** | C11 中途失败：**不回滚**已 create 的 Note；禁止二次 create。 |
| **C65-6** | C16 notify 仍在**整图 commit 成功后**；与 C65 不冲突。 |
| **C65-7** | **三分页种子**不在 C65 范围（非通用建项）。 |
| **C65-8** | **存量** GA 项目（`project_note_id` 空）：不强制批量 backfill；PM Canvas「项目知识库」/`ensure_project_note`。 |
| **C65-9** | **已知限制（本迭代）**：GA `_patch_project` 改名**不同步** KB 标题（follow-up）。 |

**验收**：**GA-PC-K27-T01～T03** · **GE-T47**（GA 路径）· 发版 Chrome checklist（项目知识库无二次确认）。

### 4.7 错误码（Agent 话术）

| 码 / detail | 话术方向 |
| ---- | ---- |
| `need_user_confirm` | 请用户对本轮 **表格确认单** 明确同意 |
| `note_title_conflict` | 项目管理主题内项目名与现有 Note 标题冲突；**改 Plan 项目名**后重 validate（C65 · 与 Web 同） |
| `invalid_fields` / `phase_planned_window_required` | 缺名/窗/due/负责人；revise Plan |
| `system_phase_immutable` | 不能改系统开始/结束 |
| `project_forbidden` / `graph_not_editable` | 无写权；仍可出只读确认单（C35） |
| `owner_not_found` | username 无法解析，请换登录名 |
| `gate_items_schedule_outside_phase` 等 | due/窗与阶段冲突，改日期后重出表 |
| `phase_not_empty` | （若误删）阶段非空 |
| `plan_not_ready` / `open_questions` | 未清空开放问题，不可 commit |
| `plan_fingerprint_mismatch` | 同意后 Plan 已变，须再确认 |
| `enrich_requires_patch_shell` | B 路径禁止 add 顶替 patch（C31） |
| notify 部分失败 | **不**当作建图失败；报 `skipped` 原因 |

### 4.8 `notify_project_ready`（M4 · Normative）

| 项 | 规则 |
| ---- | ---- |
| action | `notify_project_ready`（挂在 `governance_project_mutate`） |
| 入参 | `project_id` · `user_confirmed=true`（与 G29 一致；通常整图已同意，本步仍带 true） |
| 鉴权 | 同 `project_mutate` 写权 |
| 行为 | 算 S1 → 对每名收件人 `inform_personal_assistant(..., target_kind="user", sender=调用方, body=统一模板含深链)` |
| 回执 | `ok` · `notified: [{username/id…}]` · `skipped: [{…, reason}]` · 可仍带 `open_ge_embed` |
| **禁止** | 在 `goal_mutate` create 成功路径自动发信；在 GA overlay 打开 `inform` toolset |
| Soft-fail | 单收件人失败记 skipped，整体仍 `ok=true`（除非鉴权/项目不存在等硬错） |

**为何是 mutate action 而非「隐式钩子」**：共商链为多次 HTTP，服务端无法可靠推断「图已完成」；显式一步 = 域侧投递边界清晰，且 Agent 不接触 `inform_*`。

### 4.9 M6 工程默认（Normative · 2026-07-28 钉死 · **M7 废止三 action 主路径**）

> 产品层 C29–C38；本节钉 **M6 实现/测试默认**（执行器·Plan 存储·同意绑定仍有效）。  
> **M7（§4.11）**：Hermes/对外主路径改为独立 `validate` + `commit`；本节中 `propose_plan` / `revise_plan` / `commit_plan` **作废为 Agent 入口**，语义分别并入 validate（含整单替换再审）与 commit-once。编码以 §4.11 为准。

#### 4.9.1 同意绑定

| 项 | 默认 |
| -- | ---- |
| 用户动作 | 对话回复「同意」（或等价明确整单确认） |
| Agent | 调 **`governance_project_plan_commit`**（M7），**必须**带 `plan_id` + **`fingerprint`** |
| 服务端 | 校验 fingerprint 与存库 Plan 一致；不一致 → `plan_fingerprint_mismatch`，须再 validate 出表 |
| v1 不做 | 独立 `confirm_token` / 专用 confirm HTTP（后置可加硬） |

#### 4.9.2 确认单投影

| 项 | 默认 |
| -- | ---- |
| 生成方 | **服务端**：`governance_project_plan_validate` 在 `ok=true` 时回执含 **`confirmation_markdown`**（§3.4.4 表结构） |
| Agent | **只展示**回执表格；**禁止**手搓/改列导致与 JSON 漂移 |
| 改内容 | 改 Plan JSON → **再 validate**（整单替换再审）→ 新 `fingerprint` → 再出表 → 再同意 |

#### 4.9.3 挂载点（API / Hermes）

| 项 | 默认 |
| -- | ---- |
| 形态（**M7**） | 独立 tool：**`governance_project_plan_validate`** · **`governance_project_plan_commit`**（C49） |
| 形态（**M6 历史 · 作废**） | 曾挂 `governance_project_mutate`：`propose_plan` · `revise_plan` · `commit_plan` |
| OpenAPI | 新契约/enum；Hermes tool schema 同步；**无旧三 action 迁移** |
| 不做（v1） | 仅 Hermes 内存 Plan（须落库 · C37） |

#### 4.9.4 Plan + Run 存储

| 项 | 默认 |
| -- | ---- |
| 存储 | skstudio **同表**（或等价一行 JSON）：Plan 正文 + Run（已完成步、失败码、当前步） |
| 作用域键 | `plan_id`；读写鉴权绑 **sender + thread_id（会话）** |
| TTL | ≈ **7 天**未 commit 可 GC；`committed` 后归档或软删（续跑只读历史） |
| 续跑 | 只认 Plan+Run，**不**靠模型上下文回忆已完成步 |

#### 4.9.5 commit 执行器

| 项 | 默认 |
| -- | ---- |
| 调用 | **进程内**调现有 `ga_project_mutate` / `ga_structure_mutate` 逻辑（非自调 HTTP） |
| 步进 | 严格 §3.5；每步记入 Run；失败 → `failed_partial`，**禁止**换无关 action |
| 授权 | 入口「同意」= **整链** `user_confirmed` 授权；内部步不再问用户，仍逐步落库可审计 |
| 幂等 | 已 `committed` 且同 fingerprint 再 commit → **200**，回已有 `deep_link`，不重跑 mutate |
| B 硬约束 | 执行器编译结果：`enrich_shell` ⇒ 首业务步 **仅** `patch_phase`；出现 `add_phase` 顶替 → 内部错误 / 拒（对齐 C31） |
| A create commit | **已实现**（C40）：去掉 `create_commit_not_in_m61b`；步 1=`goal_mutate` create（回执 `shell`）→ 绑定「方案」id → 其后与 B 同 §3.5；`phases[0]` 必须 `patch_shell` |
| 排期 | validate 已预检则 commit 排期失败应极少；若仍遇 GE 400 → `failed_partial` + 人话；同 plan 续跑、**禁止**二次 create（C44） |

#### 4.9.6 双路径门禁

| 项 | 默认 |
| -- | ---- |
| A create / B enrich 共商落库 | **必须**经 `validate`（ok）→ 同意 → `commit`（C30/C49；M6 曾写 propose） |
| 裸逐步写图 | **禁止**作为 PC skill 主路径；**M7 方案 A**：GA 工具面裁剪逃逸入口；PQ / 单次偏差 mutate 等非 PC 场景仍可用现网原子 action |
| 并存期 | **M7 无旧三 action 迁移**；上线即仅 validate+commit |

#### 4.9.7 整单替换再审（原 revise）

| 项 | 默认 |
| -- | ---- |
| 语义 | **整单替换** Plan JSON 后再调 **validate**（非字段级 patch API；M6 曾用 `revise_plan`） |
| 后果 | 新 `plan_version` + 新 `fingerprint`；旧同意作废；须再出表再同意 |
| 失败后续跑 | 未改 fingerprint 可 `commit` 从 Run 失败步继续；改了则再 validate |

#### 4.9.8 测试与 DoD（题 8 钉死）

| 项 | 默认 |
| -- | ---- |
| **8a 夹具** | CI **合成** enrichable 空壳（临时 create「方案」）；**不**绑生产「数据基座筹备」id；该案例仅文档验收锚（§3.4.5） |
| **8b M6-1b DoD** | **`PC-PLAN-01～09`（至少 01～06+07）CI 绿即可合并**；不要求真人对话竖切 |
| **8c 签收文档** | **M6-2** 再补 `PC-PLAN-signoff.md`；M6-1 不强制 |
| 层 D | 续跑 / fingerprint mismatch / 二次 commit 幂等 → 建议进 CI（可标 PC-PLAN-07+） |

#### 4.9.9 编码触点（M6 增量）

| 层 | 动作 |
| -- | ---- |
| skstudio | Plan 表/模型 · `validate_project_create_plan` · propose/revise/commit · `confirmation_markdown` 渲染 · 执行器 |
| OpenAPI / Hermes | 三 action + 回执字段 |
| tests | `test_pc_plan_*`（与现有 `test_ga_progress_quality_api` PC-* 同风格） |
| docs | SKILL（M6-2）· PC-PLAN-signoff（M6-2）· 本 §4.9 |

---

## 4.10 M6-create · create commit + 整单排期（**已落地** · v0.1.15）

> **2026-07-29 共识钉死**（C40–C46）并落地。动机见 §1「慢病平台1.0」。不改 GE 起止派生算法；共商可见 + propose 预检 + A commit + SKILL 同发。

### 4.10.1 产品句

> Mode A：共商产出 **含系统开始/结束占位** 的整单 Plan；**propose 侧日期校验通过才可同意**；commit 按整单落库。Mode B **同一套**排期预检。

### 4.10.2 切片范围

| 必含（DoD） | 明确不做 |
| ----------- | -------- |
| 去掉 501；实现 create `commit_plan` | 自动延长专项周期 |
| 确认单表 B 含开始/结束占位行 + 专项周期 | 改 GE seed / 起止派生公式 |
| `propose`/`revise` 排期预检（A/B 共用） | `project-evolve` / 逐行勾选 UI |
| create 鉴权对齐现网新建项目 | 服务端 enrichable 硬门禁（仍为增强项） |
| CI：多阶段 create + 起止挤压夹具 | — |
| SKILL/SOUL 同发；对话竖切（四阶段+季度专项） | — |

### 4.10.3 微序与编译

| 步 | 说明 |
| -- | ---- |
| 1 | `goal_mutate` create → `shell.placeholder_phase_id`（名「方案」） |
| 2 | `patch_phase`：`phases[0]` 改名+窗（强制 `patch_shell`） |
| 3… | 与 enrich 相同：`add_phase` ×(N−1)、门控/任务/handoff/边界边、`notify`、deep_link |
| 续跑 | Run 已记 `create_project` 完成 → 禁止再 create |

### 4.10.4 排期预检（服务端）

在 `validate_project_create_plan` / propose 升 `ready` 之前（或同事务）：

1. 解析父专项 `period_start`/`period_end`（及 B 路径已有项目图上的系统阶段有效窗）。  
2. 派生或读取 **开始 / 结束** 有效占位（对齐 GE §4.8.2：开始≈专项起点+1 周；结束≈专项终点回 1 周）。  
3. 对每个业务阶段窗 assert：⊆ 专项；不与开始/结束重叠；段间 `next.start > prev.end`。  
4. 失败 → Plan `drafting` 或等价不可同意状态 + 错误码（建议：`phase_schedule_outside_program` / `phase_schedule_overlap` 人话映射）+ 建议窗写入确认单表 C。

### 4.10.5 测试增量

| ID | 意图 | 期望 |
| -- | ---- | ---- |
| PC-PLAN-10 | create commit N≥2 | 无 501；图含改名首阶段 + add 阶段 + 边界；deep_link |
| PC-PLAN-11 | propose 业务窗撞结束占位 | 不得 ready；确认单须改期 |
| PC-PLAN-12 | propose 超专项 period_end | 不得 ready（改日期才能同意） |
| PC-PLAN-13 | create 后 failed_partial 续跑 | 不二次 create |
| PC-PLAN-C · 竖切 | 「慢病平台1.0」类：四业务阶段 + 季度专项 | 一次同意落库或预检改期后再一次同意；无 501 绕路 |

### 4.10.6 编码触点

| 层 | 动作 |
| -- | ---- |
| skstudio | 删/改 `create_commit_not_in_m61b`；执行器跑 create 步；propose 排期预检；`confirmation_markdown` 起止行 |
| GE | **只读**派生规则；不改算法 |
| Hermes / SKILL | A 可 commit；禁「环境未开放」绕路；同发 |
| docs | 本 §4.10 · PC-PLAN-signoff 增层 C create 竖切 · TODO |

---

## 4.11 M7 · 独立 validate + commit-once（**现网** · v0.1.23）

**共识**：C49–C56。**锚**：毛新生「空中影像科」（2026-07-29）。

### 4.11.1 目标闭环

```text
共商齐结构（C48）
  → governance_project_plan_validate（全量 issues；落库 Plan）
  → ok=false：与用户改正 → 再 validate（可循环）
  → ok=true：展示 confirmation_markdown → 用户整单「同意」
  → governance_project_plan_commit(plan_id, fingerprint, user_confirmed)
       （一次生成：create/补图/boundary/notify；半截同 plan 续跑）
```

**作废**：`propose_plan` / `revise_plan` / `commit_plan`（mutate action 与话术主路径）。全新发版，无迁移。

### 4.11.2 Validate（`governance_project_plan_validate`）

| 项 | 规范 |
| -- | ---- |
| 入参 | `fields.plan` = ProjectCreatePlan JSON（create 或 enrich_shell）；可带既有 `plan_id` 做整单替换再审 |
| 回执 | `{ ok, issues[], plan_id?, fingerprint?, confirmation_markdown?, status? }` |
| `issues` | **对外唯一问题通道**（C50）：**一次尽量列全**；元素含 `code` / `message` / 可选 `phase_key`·`path`。**禁止**把「第一个 schema 400」或「排期另袋」当作主路径体验 |
| 落库 | 短生命周期 Plan 行（C37）；每次成功解析后更新 fingerprint |
| `ok=false` | 不可同意；问题清单必给；可选带问题标注的草稿表 |
| `ok=true` | 可同意确认单 + fingerprint；表含专项周期与系统起止占位（C41）；此时 `issues` 为空或仅 informational |
| 覆盖面 | **§4.11.7 必检表**（C54）；不靠 LLM 自审 |

复用并扩展现网 `validate_project_create_plan` + `precheck_business_phase_schedules`；内部可分段收集，**对外一律聚合进 `issues[]`**。

### 4.11.3 Commit（`governance_project_plan_commit`）

| 项 | 规范 |
| -- | ---- |
| 入参 | `plan_id` + `fingerprint` + `user_confirmed=true`（对话整单同意） |
| 拒绝 | 无/错 fingerprint；Plan 非最近一次 validate ok；未确认 |
| 执行 | 复用现网 commit 执行器（A：create+补图；B：enrich）；**含 boundary + notify** |
| 半截 | 同 plan 续跑；create 已成功 **禁止**二次 create（C11/C44/C52） |
| 成功 | `deep_link`（`?tab=define`） |

**禁止** commit 入参携带「未审裸 Plan JSON」作为落库真源。

### 4.11.4 强禁逃逸（C53 · **方案 A**）

| 场景 | 允许 | 禁止 |
| ---- | ---- | ---- |
| PC 共商建/补完整执行图 | 仅 validate ↔ 对话 ↔ commit | `goal_mutate` create 建壳；逐步 invent `add_phase`/`add_task`/…；把业务交付塞进系统开始/结束 |
| PQ 在跑单次修复 | 现有原子 `project_mutate`（一次一项） | 用 PQ 路径冒充整图共商落库 |

**机制真源 = 方案 A（2026-07-29 产品确认）**：

1. GA Hermes **PC 场景工具面只暴露** `governance_project_plan_validate` + `governance_project_plan_commit`。  
2. **不对 GA 注册/启用**用于替代该路径的 `goal_mutate` create 与逐步 invent 写图组合（PQ 原子 mutate 分流保留）。  
3. SKILL/SOUL 同步改口（辅助）；**单独 skill 文案不够**。  
4. 验收：PC-ESC-01/02（工具不可见或等价硬拒）。

### 4.11.5 测试增量（规划）

| ID | 意图 | 期望 |
| -- | ---- | ---- |
| PC-VAL-01 | 超专项窗 | validate `ok=false`；`issues` 含 `phase_schedule_outside_program`；**无**写图 |
| PC-VAL-02 | 缺 produce | `ok=false`；含 `gate_without_producer`；同响应可含其它已检出项 |
| PC-VAL-03 | 全合格 | `ok=true` + fingerprint + 确认单 |
| PC-VAL-04 | 改期后再 validate | 新 fingerprint；旧作废 |
| PC-CMT-01 | 无 fingerprint commit | 拒 |
| PC-CMT-02 | 同意后一次 commit | 图齐 + boundary + notify + deep_link |
| PC-CMT-03 | 半截续跑 | 不二次 create |
| PC-ESC-01 | 故意 goal_mutate create 代替 | **工具面不可用**或等价硬拒（方案 A） |
| PC-ESC-02 | validate 不过后逐步 invent | **工具面不可用**或等价硬拒 |
| PC-PLAN-D · 竖切 | 「空中影像科」类：四阶段含打磨超窗 | 先 validate 全量问题；改期后再 ok；一次 commit；**无**塞系统结束 |
| PC-REF-01～06 | C57 `program_ref.name` | 见 §0.2.1；pytest 必绿 |

### 4.11.6 编码触点（规划）

| 层 | 动作 |
| -- | ---- |
| skstudio BFF | 新路由/服务：validate + commit；作废 mutate 三 plan action；issues 聚合；配合 GA tool 裁剪 |
| Hermes plugin | **仅**注册两独立 tool（方案 A）；移除/停用旧 plan actions 与 PC 逃逸写图入口 |
| SKILL/SOUL | 主路径改 validate→commit；禁绕路/禁结构自决；版本新号与代码同发 |
| OpenAPI / docs | 新契约；本 §4.11；TODO；PC-PLAN-signoff 增 M7 行 |
| GE | 不改派生算法；commit 仍调现网 mutate API |

### 4.11.7 C54 · 本切片必检清单 / 后置 OUT

**必检（validate 必须覆盖；缺一不可宣称「全面审查」）**

| 类别 | 项 | 典型 code / 备注 |
| ---- | -- | ---------------- |
| Schema / 结构 | Plan JSON 可解析；必填顶层字段；`mode`/`op` 合法 | schema / mode 类 |
| Mode 编译 | A：create 字段齐；B：`enrich_shell` + `phases[0].op=patch_shell`；N≥2 handoff；N=1 handoff 空 | C31/C32 |
| Produce | 每业务 Gate 恰好 1 个非 `start_sign` 任务 `produces_gate_key` | `gate_without_producer` / `gate_multiple_producers` |
| Boundary / handoff | M5 边界不可 deferred；handoff 键可解析 | C34 |
| Open questions | `open_questions` 非空 → `ok=false` | — |
| 排期三件套 | 超专项窗；叠系统起止；段间交叉 | `phase_schedule_*` |
| Due | `planned_due` ∈ 阶段窗 | — |
| 写权 | 无写权 → `blocked`；可出只读表；commit 拒 | C35 |
| Username | PM / 任务负责人可解析 | 不可解析 → issue |
| B 准入 | enrichable 再检（结构） | §3.3 |
| 父专项（C57） | `program_ref.name` 全局可解析；validate 固化内部 id；确认单只展 name | `program_not_found` / `program_create_forbidden`；**禁止** commit 另要客户端 id |

**后置 OUT（本切片不进必检表 · 不挡 M7 / C57）**

- 跨项目重名策略细化（**项目**名，非专项名）  
- 通讯录缺失话术产品化  
- 仅 GE 运行时可知、且无法在 Plan 预检的约束  

新增 Plan 约束 → **必须**同步进上表后再宣称覆盖完整。

### 4.11.8 GA 工具面白名单（方案 A · 实现钉死）

PC 共商建/补完整执行图时，Agent **可见且可调**的写图相关入口：

| 保留 | 用途 |
| ---- | ---- |
| `governance_project_plan_validate` | 审查 |
| `governance_project_plan_commit` | 落库 |
| `governance_project_mutate` | **仅 PQ** 单次修复（非整图共商） |
| `governance_goal_mutate` | **仅** L1 目标结构；**禁止** create 项目 / invent 执行图代替 PC |
| 既有读/评 tool | `governance_scope` · `goal_dq` · `goal_pq` · `goal_pq_rollup` · … |

| 移除 / 不对 GA 暴露（PC 逃逸） | 说明 |
| ----------------------------- | ---- |
| `propose_plan` / `revise_plan` / `commit_plan` | 作废 |
| 用 `goal_mutate` create 顶 PC | 禁 |
| 用逐步 `add_phase`/`add_task`/… invent 顶 PC | 禁 |

**不是**「GA 只剩两枚 tool」——读/评/PQ/目标结构/组织 mutate 仍在；裁的是 **PC 逃逸写图组合**。

---

## 5. 测试与验收

### 5.1 层 A · CI

| ID | 意图 | 期望 |
| -- | ---- | ---- |
| PC-INST-01 | SKILL 同步 | frontmatter `name: project-create` |
| PC-INST-02 | skills 启用 | `skills` ∉ disabled |
| PC-API-01 | `patch_phase` 改名+窗 | 200；原方案 id 名变新名 |
| PC-API-02 | `patch_phase` 缺窗/空名 | 400 |
| PC-API-03 | `patch_phase` 系统阶段 | 不可变错误 |
| PC-API-04 | 未 confirmed | `need_user_confirm` |
| PC-API-05 | create → `shell.placeholder_phase_id` | 非空且指向名「方案」阶段 |
| PC-API-06 | `patch_phase` + `phase_name=方案`（无 target.id） | 唯一匹配成功 |
| PC-API-07 | `add_task` + `assignee_username` | 200；assignee 已解析 |
| PC-API-08 | 链式冒烟 | create→patch→add_phase→gate/task/produce/prereq→`open_ge_embed`（**M1 止于图、不含 notify**） |
| PC-NOTIFY-01 | `notify_project_ready` | PM∪assignee 去重且不含 sender 收到信；body 含深链 |
| PC-NOTIFY-02 | 仅建壳后误调或不调 | create **不**自动发信 |
| PC-NOTIFY-03 | soft-fail | inform 单人失败 → skipped；HTTP 仍 ok；图不回滚 |
| PC-NOTIFY-04 | 仅 sender=PM 且无其它 assignee | `notified=[]` 仍 ok |
| PC-PLAN-01 | schema：N=1 enrich 缺 `patch_shell` | assert 拒 |
| PC-PLAN-02 | schema：N≥2 无 handoff | assert 拒 |
| PC-PLAN-03 | schema：`boundary.deferred` | assert 拒 |
| PC-PLAN-04 | commit N=1 enrich | 仅 patch_shell；图齐 + deep_link；无 add_phase |
| PC-PLAN-05 | commit 中 `patch_phase` 400 | `failed_partial`；停该步；无盲换 add |
| PC-PLAN-06 | 无写权 propose | 只读表 + `blocked`；commit 拒绝 |
| PC-PLAN-07 | （建议）同 fingerprint 二次 commit | 幂等 200 + 原 deep_link |
| PC-PLAN-08 | （建议）fingerprint 变仍 commit | `plan_fingerprint_mismatch` |
| PC-PLAN-09 | （建议）`failed_partial` 后同 plan 续跑 | 从失败步继续；不二次 create |
| PC-PLAN-10 | create commit N≥2 | 见 §4.10.5 |
| PC-PLAN-11～13 | 排期预检 / 续跑 | 见 §4.10.5 |

夹具：**合成** enrichable 空壳（§4.9.8）；create 夹具用测试专项已知 `period_*`；禁止依赖生产项目 id。

### 5.2 层 B · 静态

| ID | 意图 |
| -- | ---- |
| PC-STATIC-01 | SKILL：A+B、enrichable、改名、微序、C13–C15、禁 activate；**M4 须调 notify、禁 inform tool**；**M5 边界边**；**M6 propose→表→commit** |
| PC-STATIC-02 | SOUL 无 Plan 全表；overlay **仍** disabled `inform` |
| PC-STATIC-03 | tool 文案区分 `patch_phase` vs `patch_phase_window`；含 `notify_project_ready`；含 propose/commit |
| PC-STATIC-04 | SKILL/本文件：C23–C28 · §3.11 · 「禁动」允许边界 prereq · 示例 Plan 含 boundary |
| PC-STATIC-05 | C29–C38 · §3.4 Plan · 表格确认单 · 禁自由文落库 |
| PC-BD-01～05 | 读图：基线无边 vs M5 样例有 PM 启动签收 + E1（见 [PC-BOUNDARY-signoff](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-BOUNDARY-signoff.md)） |
| PC-BD-C1～C5 | Chrome 定义 tab：确认启动 / 结项复盘前置签收可见 |

### 5.3 层 C · PC-T01 / PC-NOTIFY / PC-BOUNDARY / PC-PLAN

- 建图 + **M5 边界**：[PC-T01-signoff.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-T01-signoff.md)  
- 通知：[PC-NOTIFY-signoff.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-NOTIFY-signoff.md)  
- **M5 系统竖切**：[PC-BOUNDARY-signoff.md](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-BOUNDARY-signoff.md)（读图 + Chrome + GA create/enrich_shell）  
- **M6-1a DoD**：propose/revise + PC-PLAN-06  
- **M6-1b DoD**：PC-PLAN-01～09 CI 绿（§4.9.8）；对话竖切属 M6-2  
- **M6-2**：`PC-PLAN-signoff.md` + SKILL 改口 + 门禁  
- **M6-create（现网）**：§4.10 · PC-PLAN-10～13 CI 绿；SKILL 0.3.0 同发；竖切层 C 待勾

### 5.4 层 D · 可选

| ID | 说明 |
| -- | ---- |
| PC-EVAL-01 | eval fixture（可含 boundary） |
| PC-ENRICH-API | 服务端 enrichable |
| PC-API-09 | 部分失败后续跑不二次 create |
| PC-API-10 | （可选）链式冒烟断言：`项目启动` 有 PM 签收边；`结项复盘` 含末业务门控前置 |

### 5.5 DoD

- [x] M0：install 同步 + 启用 skills  
- [x] M1：PC-API-01～08 绿 + PC-T01 A（对话 A 见 PC-T01；层 A CI 已绿）  
- [x] M2：PC-T01 B + R  
- [x] M3：PC-T01 全勾；入口文档收口  
- [x] M4：PC-NOTIFY-01～04 + PC-NOTIFY 竖切；GA 仍无 inform toolset  
- [x] **M5**：§3.11 写入 SKILL · PC-STATIC-04 · PC-T01 边界步 · **[PC-BOUNDARY](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-BOUNDARY-signoff.md)** 层 A/B/C/D 绿（create + enrich_shell）  
- [x] **M6-0**：Plan schema assert（C31/C32/C34）+ fingerprint + markdown · `test_ga_project_create_plan.py`  
- [x] **M6-1a**：Plan+Run 表 · propose/revise · PC-PLAN-06  
- [x] **M6-1b**：commit 执行器 · **PC-PLAN-04/05/07～09 CI 绿**（§4.9）  
- [x] **M6-2**：门禁（skill+tool 文案）+ SKILL/SOUL 改口 + `PC-PLAN-signoff.md`  
- [x] **M6-create**：create commit + 确认单起止占位 + A/B 排期预检 + PC-PLAN-10～13 CI + SKILL 0.3.0 同发（§4.10 · C40–C46）；竖切层 C 待运维勾
- [x] **M7**：独立 `governance_project_plan_validate` + `governance_project_plan_commit`（§4.11 · C49–C56）；文档 v0.1.23；BFF/plugin/install 同发；PC-VAL/CMT/ESC + 空中影像科竖切（CI）

---

## 6. 文档与版本

| 版本 | 日期 | 说明 |
| ---- | ---- | ---- |
| v0.1.0 | 2026-07-28 | 共识首版 |
| v0.1.1 | 2026-07-28 | enrichable≠draft；due/assignee 必填 |
| v0.1.2 | 2026-07-28 | C13–C15 id/username 链；微序；续跑；示例 Intent；错误码；附录 B |
| v0.1.3 | 2026-07-28 | **C16–C22 PC-NOTIFY / M4**：S1 · 域侧钩子 · 统一文案+深链 · soft-fail |
| v0.1.8 | 2026-07-28 | 建项/补壳/`notify` 深链落地 **定义** tab（`?tab=define`）；`open_deviation` 仍默认执行 |
| v0.1.9 | 2026-07-28 | **M5 PC-BOUNDARY**：C23–C28 · §3.11 · 启动 PM 签收路由 · 结项 E1 · 仅 PC · 附录 D |
| v0.1.10 | 2026-07-28 | **M6 PC-Plan**：C29–C38 · §3.4 Plan+表格确认单 · commit 执行器 · 左伟事故锚 · 附录 E |
| v0.1.11 | 2026-07-28 | **§4.9 工程默认钉死**（C39）：同意+fingerprint · 服务端出表 · mutate 三 action · Plan+Run · 门禁 · 测试 DoD |
| v0.1.12 | 2026-07-28 | **切片拆分**：M6-0 / M6-1a / M6-1b / M6-2（契约不变） |
| v0.1.13 | 2026-07-28 | **M6 现网**：harness + propose/revise/commit + SKILL/SOUL + PC-PLAN-signoff · OpenAPI 0.1.9 · plugin 0.16.3 |
| v0.1.14 | 2026-07-29 | **M6-create 规划**：C40–C46 · §4.10 整单含系统起止 + propose 排期预检（A/B）· 去 501 · 慢病平台1.0 动机 · 附录 F |
| v0.1.15 | 2026-07-29 | **M6-create 现网**：排期预检 + 确认单起止 · create commit · PC-PLAN-10～13 · SKILL 0.3.0 / SOUL · 附录 F 现网 |
| v0.1.16 | 2026-07-29 | **Harness**：业务门控须恰好一生产者（C47 · `gate_without_producer` / `gate_multiple_producers`）· PC-PLAN-14/15 · sample N=1 含 produce · SKILL **0.3.1**；GE `add_phase`/`add_gate_item`/`add_task` 返回体带创建 id |
| v0.1.17 | 2026-07-29 | **Skill 共商门闩（C48）**：结构未齐禁止 propose；清单=阶段/门控/产出任务/衔接；禁臆造与 `gate_without_producer` 盲撞；SKILL **0.3.2** · SOUL 同发 |
| v0.1.18 | 2026-07-29 | **M7 规格冻结（C49–C56）**：独立 validate + commit-once 双 tool；作废 propose/revise/commit_plan；全量 issues；强禁逃逸；审查全面覆盖；空中影像科动机 · §4.11 |
| v0.1.19 | 2026-07-29 | **M7 细化**：逃逸=**方案 A**（C53）；C54 **§4.11.7 必检表**；issues 对外唯一通道（C50）；正文 scrub 旧 propose 主路径（§3.2/3.4/3.5/3.7/§4.9）；G9 去重；**附录 G 综合评价** |
| v0.1.20 | 2026-07-29 | **跨文档同步**：SKILL **0.4.0** · SOUL · Hermes **§13.15 v1.9.58** · OpenAPI **pc-plan 0.2.0-draft** / pq **0.1.10** · GA **v0.8.98** · BO **v1.3.91** · DOC-SYNC 表 · §4.11.8 工具白名单 · `ok` 取代对外 `ready` · 附录 G 同步分上修 · **附录 H 综合评价** |
| v0.1.21 | 2026-07-29 | **M7-0 暗上**：BFF `POST …/project-create-plan/validate` · issues 聚合 · PC-VAL-01～06；Hermes 仍 M6 propose |
| v0.1.22 | 2026-07-29 | **M7-1 暗上**：BFF `POST …/project-create-plan/commit` · PC-CMT-01～03；mutate `commit_plan` 过渡并存 |
| v0.1.23 | 2026-07-29 | **M7-2 现网同发**：Hermes 双 tool · 卸三 plan action · `goal_mutate` create+project 硬拒 · SKILL 0.4.0 install · OpenAPI pc-plan **0.2.0** / pq **0.1.11** · PC-ESC + PC-PLAN-D |
| v0.1.24 | 2026-07-29 | **话术补丁 + 生产 Chrome 竖切签收**：SKILL/SOUL **0.4.1** 禁对用户写旧短名；BFF 确认单脚注点名 `governance_project_plan_commit`；PC-PLAN-signoff 生产对话 ☑ |
| v0.1.25 | 2026-08-01 | **C57 规格冻结**：对外只 name；服务端 name→id；fingerprint 含固化 id；commit 统一 resolve；issue 码+用户话术；Skill **0.5.1** 最小完整样例；OpenAPI **0.2.1**；PC-REF-01～06；工程默认 §0.2.1；**附录 I 评价** |
| v0.1.26 | 2026-08-01 | **C57-M1**：BFF `ga_project_create_plan_program_ref` + validate 固化/fingerprint + commit 统一 resolve；`test_ga_project_plan_ref.py` PC-REF-01～06 绿；**C57-M2** Skill/SOUL install + DOC-SYNC |
| v0.1.27 | 2026-08-01 | **C58 规格冻结**：issue `owner`/`next_action` · 系统结项方案 A · 硬闸 H1–H4 · failed_partial 深链 · C58-M1～M4 · PC-OWN/SYS/GATE/PART · **附录 J 综合评价**；代码未动 |
| v0.1.28 | 2026-08-01 | **C58 工程默认**：结项 **A1+用户指定**；**撤销**轮次硬闸（改行为契约 B1–B4）；整体同发；仅系统起止相关任务要求 PM；pytest 挡合入 / PW 签收；PC-SYS-04；修订 §0.3 |
| v0.1.29 | 2026-08-01 | **C58-M1**：`ga_project_create_plan_issue_owner` + validate `next_action`；OpenAPI **0.2.2**；PC-OWN-01～04 绿 |
| v0.1.30 | 2026-08-01 | **C58-M2**：`end_entry_unspecified` · `end_entry_spurious_gate` · `closeout_task_conflict`；PC-SYS-01～04 绿 |
| v0.1.31 | 2026-08-01 | **C58-M3**：SKILL/SOUL **0.5.2** install · plugin validate/commit 文案 · PC-C58 profile 测 |
| v0.1.32 | 2026-08-01 | **C58-M4 / C58 现网**：PC-PART-01 failed_partial deep_link · `ga_pc_chrome_smoke` ask-user / end_entry / 评分 · DOC-SYNC 全绿 · 附录 J 残留清空 |
| v0.1.33 | 2026-08-01 | **C59-M1**：窄形状检测 + 空 gates→`invalid_plan_schema`；归属 A（name_required 等）/ B·C；OpenAPI **0.2.3**；PC-SHAPE-01/02 · PC-OWN-05；Skill 仍 0.5.2 |
| v0.1.34 | 2026-08-01 | **C59-M2**：`issues[].proposal` · OpenAPI **0.2.4** · SKILL/SOUL **0.5.3** install · PC-PROP-01/02 · plugin 文案 |
| v0.1.35 | 2026-08-01 | **C59-M3 / C59 现网**：`ga_pc_chrome_smoke` assisted 确认 + `c59_proposal_or_confirm`；DOC-SYNC 全绿 |
| v0.1.36 | 2026-08-01 | **C60 规划冻结**：低垂果三切片（SOUL 短样例 · A 档可粘贴 proposal · smoke/Chrome 硬门槛）；Mode B OUT；§0.5；实现未开始 |
| v0.1.37 | 2026-08-01 | **C60-M1**：SOUL「Plan 形状骨架」短 JSON · README · PC-SOUL-01/02 · signoff 层 B |
| v0.1.38 | 2026-08-01 | **C60-M2**：A 档 `invalid_plan_schema` proposal 可粘贴 JSON · 确认单 commit 脚注 · Skill **0.5.4** · OpenAPI **0.2.5** · PC-PROP-A01/A02 · PC-CONF-01 |
| v0.1.39 | 2026-08-01 | **C60-M3 / C60 现网**：smoke 终态/`session_rotated`/假阴性收敛 · PC-PW-C60 硬门槛 PASS（`PC-PW-202608010610` · `/execution/projects/53e2e9e1-…?tab=define`）· 软指标 validate=3 / assisted 一次（不挡）· DOC-SYNC 全绿 |
| v0.1.40 | 2026-08-01 | **C61-M1**：SOUL 双阶段短骨架 + 合法 `handoffs.to_task_key` · 禁 `to_phase_key` · PC-SOUL 扩测 · §0.6 规划冻结 |
| v0.1.41 | 2026-08-01 | **C61-M2**：Skill **0.5.5** · 禁 `to_phase_key` · fix_schema 后再 validate≤1 · plugin 描述 · profile 测 |
| v0.1.42 | 2026-08-01 | **C61-M3 / C61 软效率现网**：smoke `self_heal`+`soft_ok` · PC-PW-C61 硬+软 PASS（`PC-PW-202608010640` · validate=1 · 无 assisted · `/execution/projects/01004ece-…?tab=define`）· DOC-SYNC 全绿 |
| v0.1.43 | 2026-08-01 | **C62-M1**：smoke hard=session `deep_link` · c57 否定句白名单 · `deep_link_ui_missing` WARN · §0.7 规划 · 静态测 PC-PW-C62 |
| v0.1.44 | 2026-08-01 | **C62-M2**：Skill/SOUL **0.5.6** · 纯文本深链红线 · 样例 `wecom:example` · profile 测 · 同发纪律：install 与冒烟同 M3 |
| v0.1.45 | 2026-08-01 | **C62-M3 / C62 现网**：tag **v26.11.41** · install 0.5.6 · PC-PW-C62 hard+soft PASS（`PC-PW-C62-202608011735` · validate=1 · skill 17/17 · `/execution/projects/15f27f8e-…?tab=define` · GE active）· DOC-SYNC 全绿 |
| v0.1.46 | 2026-08-01 | **C63** 运维卫生 + **C64** sender 短名别名（OpenAPI **0.2.6** · PC-ALIAS） + scope/DQ 短冒烟脚本（修订表曾误标 C65） |
| v0.1.47 | 2026-08-23 | **C65 规格**：§4.6.1 GA/Web 建项同路径 · [release-v29.00.07](../../platform_docs/migration/release-v29.00.07.md) · I4 更新 |
| v0.1.48 | 2026-08-23 | **C65 Agent 文档齐**：Skill **0.5.7**（§C65 + 话术表）· SOUL/README/duplicate · eval C65-AGENT · §0.11 · **附录 K 评级** |
| v0.1.49 | 2026-08-23 | **C65-M1 落地**：`ga_structure_mutate._create_project` → `create_project_with_note` · GA-PC-K27-T01～T03 · GE-T47（`test_ga_project_plan_k27.py`）pytest 绿 |

---

## 附录 A · 评价摘要（v0.1.1 · 历史）

见 git 历史；要点：纠正 draft 误用；due/负责人必填；overlay M0 再开 skills。

---

## 附录 B · 文档综合评价（v0.1.2 · 历史）

见上版：implementation-ready（建图主链）。

---

## 附录 C · 文档综合评价（v0.1.3 · PC-NOTIFY）

### 结论

**建图（M0–M3）仍可按原计划编码；成员欢迎为独立 M4，需求/实现/测试已钉死。** 保持 GA 不启用 `inform` toolset，用 `notify_project_ready` 作为域侧投递边界，避免「多次 mutate 无法推断图完成」的隐式钩子难题。

### 本轮纳入

| # | 共识 | 落点 |
| - | ---- | ---- |
| 1 | S1 收件人 | §3.10.2 · I7 |
| 2 | 域侧钩子 · 非 GA inform | C18 · §4.8 |
| 3 | 发送者=调用方 | C19 |
| 4 | A/B 同文案 + 深链 | C20 · §3.10.3 |
| 5 | 建壳不发 | C16 · PC-NOTIFY-02 |
| 6 | soft-fail | C21 · PC-NOTIFY-03 |
| 7 | 独立 M4 | §4.1 · §5.5 |

### 残留风险（M4 编码）

| # | 风险 | 缓解 |
| - | ---- | ---- |
| N1 | Agent 忘调 notify | SKILL 硬步骤 + PC-NOTIFY 竖切 |
| N2 | inform 投递与 PA thread 环境差异 | 复用 `pa_inform`；单测 mock + 竖切真投 |
| N3 | 深链在助手气泡不可点 | 使用与现网 inform 一致的 URL/markdown 形态 |

---

## 附录 D · 文档综合评价（v0.1.9 · PC-BOUNDARY）

### 结论

**可进入 M5 实现（skill / 签收为主，无后端契约变更）。** 产品三角已钉死：启动签收人=PM、结项=E1、只改 PC。文档把「为何断 → 补哪条边 → 禁动改口 → 验收」写清，与 GE §3.4.3 不打架（启动仍可不 seed；PC 履行原属 Canvas 的手配）。

**成熟度**：规划 + skill + 签收竖切已绿（DoD M5 ☑ · create / enrich_shell GA 双路径）。

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| 与需求 §3.4.3 | ✅ 启动不 seed → PC 补签收路由；结项签收仍归 `确认结项`；E1 只加任务前置 |
| 与现网 `add_prerequisite` | ✅ 阶段序约束：系统开始 seq0 / 结束 ≥ 末业务 |
| 与 C7（无新读图 tool） | ✅ I9 用固定名 + 已有回执链 |
| 与 PQ | ✅ C27 明确本轮不改系统衔接评分 |
| 与「禁动系统」旧话术 | ✅ C26 / §3.11.3 改口，避免 agent 再省略边界边 |
| Intent / 微序 / 示例 / 测试 | ✅ §3.4 · §3.5.1 · §3.9 · §3.11 · PC-STATIC-04 · PC-T01 |

### 本轮纳入

| # | 共识 | 落点 |
| - | ---- | ---- |
| 1 | PM 签启动 | C23–C24 · §3.11.1 |
| 2 | 结项 E1 | C25 · §3.11.2 |
| 3 | 只改 PC | C27–C28 · M5 切片 |
| 4 | 纪律改口 | C26 · 红线/拒绝话术须同步 SKILL |
| 5 | 续跑边界失败 | §3.5.2 |

### 残留风险（M5 实现）

| # | 风险 | 缓解 |
| - | ---- | ---- |
| B1 | Agent 仍不敢碰系统 GI | SKILL 红线改写 + PC-STATIC-04 + 竖切读图 |
| B2 | 错把非 PM 任务挂启动边 | C23 硬约束；签收查 `eligible_signers` |
| B3 | 误做 E2（业务签结项） | §3.11.2 禁止；验收只查任务前置、不查结项 GI 多签收人 |
| B4 | 单阶段项目：末门控=首阶段门控 | 允许；E1 仍挂该退出门控 → `结项复盘` |
| B5 | 「确认启动」进 S1 通知 | 预期内（PM 任务）；若仅 PM=调用方仍可 notified=[] |
| B6 | 存量空壳 enrich 前已有脏边 | enrichable 仍挡；非 enrichable 走 GE/PQ |

### 实现顺序建议

1. 改 SKILL（红线 · 微序 · Intent · 示例）+ reinstall  
2. 更新 PC-T01 边界步 · 跑 A/B 各一 · 读图确认  
3. （可选）PC-API-10 冒烟断言  
4. 入口指针：TODO · Hermes §13.15 · profile README  

### 评分（文档本身）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | 根因与现象对齐 |
| 规范可执行 | 5 | 边、谁、禁/允、微序位次清楚 |
| 与上位一致 | 5 | 不改 GE 条文却补齐产品洞 |
| 测试可验 | 4 | 竖切为主；自动化可选 |
| 范围克制 | 5 | 只 PC · 独立 M5 |
| **总评** | **可开工** | 先 skill，后签收 |

---

## 附录 E · 文档综合评价（v0.1.10 · PC-Plan）

### 结论

**M0–M5 现网可继续运维；M6 已从「生产事故根因」升格为可编码规格，可按 M6-0 → M6-1 → M6-2 开工。** 核心跃迁：共商真源从 skill 散文 Intent → **可 assert 的 `ProjectCreatePlan` + Markdown 表格确认单 + `commit` 执行器**，使「同意后仍追问 / 400 后换 action 盲重试 / add 顶替 patch」在编译与执行层无空间。

**成熟度**：产品共识钉死（C29–C38 · §3.4）；实现与 API **待做**；验收锚已有（§3.4.5 数据基座筹备 N=1）。

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| 与 M0–M5 微序 / 边界 | ✅ commit 仍驱动 §3.5 / §3.11；不改 GE seed / PQ（C27） |
| 与 C5/C6/C11 | ✅ 确认对象=表格整单；mutate 由执行器；失败停步禁盲换 |
| 与左伟事故 | ✅ C31 硬禁 add 顶替；C30 禁未 Plan mutate；错误码扩 `enrich_requires_patch_shell` |
| 与 G29 / 一次一项 | ✅ commit 内仍原子一步一 HTTP；只是编排不归模型 |
| 与无写权 | ✅ C35 只读表 + blocked |
| 与通知 / 边界 | ✅ Plan 含 notify / boundary；deferred 禁（C34）；N=1 强制确认启动（C24） |
| UI 范围 | ✅ v1 对话表格即可；逐行勾选 OUT |

### 本轮纳入

| # | 共识 | 落点 |
| - | ---- | ---- |
| 1 | Plan 真源 + 表格投影 | C29 · §3.4 · §3.4.4 |
| 2 | validate → 整单同意 → commit（M7；原 propose） | C30 · §3.4.0 · §3.7 · §4.11 |
| 3 | B 必须 patch_shell | C31 · §3.5 步 2–3 · PC-PLAN-04/05 |
| 4 | handoff / boundary / 默认 due·form | C32–C34 · §3.4.3 |
| 5 | 无写权只读 · PQ 直 Plan-B | C35–C36 |
| 6 | Plan 短存 + 续跑 | C37 · §3.5.2 |
| 7 | 切片 M6-0/1/2 | §4.1 · §5.5 |

### 残留风险（M6 实现）

| # | 风险 | 缓解 |
| - | ---- | ---- |
| P1 | Agent 仍绕过 validate/commit 直接写图 | **方案 A 工具面裁剪** + SKILL 红线 + EVAL 拒路径（C53） |
| P2 | 表格与 JSON 漂移 | 确认单由同一 Plan 投影生成；fingerprint 绑同意 |
| P3 | Plan 存哪里 / TTL | C37 短生命周期；commit 后归档；续跑靠 Run |
| P4 | 大图表格过长 | 分表 A/B/C；why≤40 字；后续可 UI |
| P5 | 专项窗覆盖项目窗 400 | I6：detail 人话 + revise；执行器不换 add |
| P6 | M6-1 与现网 skill 并存期双路径 | M6-0 先 harness；skill 改口放 M6-2 |

### 实现顺序建议

1. **M6-0**：JSON Schema + assert 单测（C31/C32/C34 · N=1 注入确认启动）  
2. **M6-1**：BFF propose/revise/commit + Plan 表 + 执行器复用现网 mutate  
3. Hermes tool schema + OpenAPI  
4. **M6-2**：SKILL 改口为表格确认单；左伟锚竖切  
5. 入口：TODO · Hermes §13.15 · GA 产品指针  

### 评分（文档本身）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | 事故根因与「skill=建议」诊断清楚 |
| 规范可执行 | 5 | 顶层/子结构/编译 assert/确认单样例齐 |
| 与上位一致 | 5 | 不推翻 M5；升格 Intent→Plan |
| 测试可验 | 4 | PC-PLAN-* 已列；竖切待实现后绿 |
| 范围克制 | 5 | 独立 M6；无逐行 UI；无改 GE |
| **总评** | **可开工（先 harness）** | M6-0 当天可写；防再飘 |

---

## 附录 E.1 · 工程共识钉死（v0.1.11 · §4.9）

**九题全部按推荐采纳（2026-07-28）。** 实现规格完整度由「产品可编码」升为「可按 §4.9 无歧义开工」。

| # | 决议 |
| - | ---- |
| 1 | 同意 = 对话「同意」+ `commit(plan_id, fingerprint)` |
| 2 | 服务端回执 `confirmation_markdown`；Agent 只展示 |
| 3 | `project_mutate` 三 action：propose / revise / commit |
| 4 | Plan+Run 同表；sender+thread；TTL≈7d |
| 5 | 进程内执行器；已 committed 幂等 |
| 6 | A/B 共商必须经 commit；裸写图非 PC 主路径 |
| 7 | 入口一次授权整链 |
| 8 | 合成夹具；M6-1=CI DoD；`PC-PLAN-signoff` @ M6-2 |
| 9 | revise = 整单替换 + 新 fingerprint |

**残留风险更新**：P3/P6 已由 §4.9.4 / §4.9.6 消化；P1 靠 M6-1 门禁落地验证。

**下一步**：install sync skill **0.3.0** + gateway；勾 [PC-PLAN-signoff](../../platform_docs/integration/hermes-skstudio/profiles/governance-assistant/PC-PLAN-signoff.md) 层 C 对话竖切（enrich + create）。

---

## 附录 F · 文档综合评价（v0.1.15 · M6-create 现网）

### 结论

**Mode A create commit + 整单起止占位 + propose 排期预检已落地（§4.10）。** 张雯「慢病平台1.0」案例根因（501 半上线 + 无预检）已对症修复；共商真源为 **合格整单**。

**成熟度**：产品共识 C40–C46；skstudio CI PC-PLAN-10～13 绿；SKILL 0.3.0 / SOUL 同发；对话竖切层 C 待运维勾。

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| 与 M6 enrich / C31 | ✅ A 同样 `phases[0]=patch_shell`；微序 create + §3.5 |
| 与 GE §4.8 起止 | ✅ 不改派生算法；确认单展示占位；预检对齐 overlap / outside_program |
| 与 C11 续跑 | ✅ 同 plan 续跑；禁二次 create（C44） |
| 与写权 | ✅ 对齐现网新建项目（C45） |
| 与超专项 | ✅ 只改日期才能同意；不自动延专项（C43） |
| 与 skill 半上线 | ✅ 代码与 SKILL 同发（C46） |
| A/B 预检 | ✅ 同一套（C42） |

### 本轮纳入

| # | 共识 | 落点 | 状态 |
| - | ---- | ---- | ---- |
| 1 | 实现 create commit | C40 · §4.10.3 · PC-PLAN-10 | ✅ |
| 2 | 确认单含开始/结束 + 专项周期 | C41 · §3.4.4 | ✅ |
| 3 | propose 排期预检 A/B 共用 | C42 · §3.4.6 · §4.10.4 | ✅ |
| 4 | 超期只改日期 | C43 | ✅ |
| 5 | 续跑不二次 create | C44 · PC-PLAN-13 | ✅ |
| 6 | 鉴权对齐现网 | C45 | ✅ |
| 7 | SKILL 同发 + 竖切 | C46 · PC-PLAN-C | ✅ 文案；竖切待勾 |

### 残留风险

| # | 风险 | 缓解 |
| - | ---- | ---- |
| R1 | 预检与 GE 派生差一天 off-by-one | 预检对照 GE 同测夹具；竖切用真实季度专项 |
| R2 | 大表过长 | 系统占位仅两行；业务行压缩 why |
| R3 | Agent 仍绕路建壳 | 门禁 + SKILL 禁绕路 + EVAL |
| R4 | create 成功后 Note 标题冲突 | 现网错误码人话；续跑/revise 指引 |

### 实现顺序建议

1. ~~排期预检纯函数 + 单测~~  
2. ~~`confirmation_markdown` 起止行 + propose 升 ready 门闩~~  
3. ~~打开 create commit 执行器 + PC-PLAN-10/13~~  
4. ~~SKILL/SOUL 同发~~ · 竖切「四阶段+季度专项」待勾  
5. ~~勾 PC-PLAN-signoff 增补 create 行 · TODO 收口~~（层 C 对话待运维）

### 评分（文档本身）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | 501 + 起止占位 + 专项窗三条根因对齐案例 |
| 规范可执行 | 5 | 微序、预检项、确认单行、DoD 含/不含清楚 |
| 与上位一致 | 5 | 不改 GE；升格「合格整单」共商 |
| 测试可验 | 5 | PC-PLAN-10～13 + 竖切锚 |
| 范围克制 | 5 | 不做自动延专项、不改起止算法 |
| **总评** | **可开工** | 预检与 create commit 勿再拆成「半上线」 |

---

## 附录 G · 文档综合评价（v0.1.19 · M7 规格细化）

### 结论

**M7 产品规格已可开工实现；文档本身达到「无歧义编码」门槛。** 空中影像科根因（审查与落库耦合 + 可逃逸 + 结构自决）已对症升格为：独立 validate（全量 `issues[]`）→ 整单同意 → commit-once，并以 **方案 A 工具面裁剪** 作为机制真源（C53）。必检面有 IN/OUT 表（§4.11.7），不再停在口号式「全面覆盖」。

**成熟度**：共识 C49–C56 + 逃逸/必检/issues 细化 **冻结**；**跨文档（v0.1.23）已对齐**；BFF / Hermes plugin / SKILL **0.4.0 已同发现网**（C56）。禁止回滚只卸 BFF 留 0.4.0 Skill。

**总评一句话**：**规格+文档可开工；代码同发仍是唯一剩余硬门闩。**

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| 与空中影像科事故 | ✅ 绕路 invent / 超窗事后 / 塞系统结束 → validate 全量 issues + C55 + 逃逸 A + 竖切 PC-PLAN-D |
| 与 M6 执行器 / Plan / fingerprint | ✅ commit 复用执行器；Plan+Run/TTL/续跑保留；仅 Agent 入口改口 |
| 与 M5 边界 / M4 notify | ✅ commit 仍含 boundary + notify；C34 deferred 禁不变 |
| 与 G29 / 一次一项 | ✅ 执行器内仍原子 mutate；模型不见逐步 invent |
| 与 PQ 分流 | ✅ PQ 保留原子 `project_mutate`；禁止冒充整图共商 |
| 与 C48 结构门闩 | ✅ 共商齐 → validate；未齐禁审查/臆造 |
| 与无迁移 | ✅ C49/C56；§4.9.6 并存期改为「上线即仅双 tool」 |
| 规范主路径 scrub | ✅ §3.2/3.4.0/3.5/3.7/§4.9 已改 validate/commit；G9 去重 |
| 文档 ↔ SKILL / §13.15 / OpenAPI / GA / BO | ✅ **v0.1.20 DOC-SYNC** |
| Plan `status=ready` ↔ `ok=true` | ✅ 对外以 `ok` 为准（§3.4.1 / OpenAPI pc-plan） |
| 工具面「只暴露两枚」歧义 | ✅ §4.11.8 白名单：裁逃逸，非砍光读/评/PQ |

### 本轮纳入（相对 v0.1.18）

| # | 决议 | 落点 |
| - | ---- | ---- |
| 1 | 逃逸 = **方案 A** | C53 · §4.11.4 · §4.11.8 · PC-ESC |
| 2 | C54 必检表 + OUT | §4.11.7 |
| 3 | issues 对外唯一通道 | C50 · §4.11.2 |
| 4 | 正文 scrub 旧 propose 主路径 | §3 · §4.9 · G9/G9a |
| 5 | 后置项不挡开工 | OUT 三行 · TODO |
| 6 | **跨文档同步（v0.1.20）** | DOC-SYNC · SKILL 0.4.0 · OpenAPI · 指针 |

### 残留风险 / 实现前宜钉死的小项

| # | 项 | 建议 |
| - | -- | ---- |
| R1 | ~~方案 A 工具面清单~~ | ✅ §4.11.8 |
| R2 | ~~`status=ready` vs `ok=true`~~ | ✅ 对外以 ok 为准 |
| R3 | issues `code` 最小集合 | 实现时列出与 PC-VAL 对齐的 code 表（可复用现网 harness 名） |
| R4 | ~~文档/指针滞后~~ | ✅ v0.1.20；**剩** BFF/plugin 同发 |
| R5 | §4.10 / 附录 F 仍写 propose | 作 **历史现网** 可读；编码以 §4.11 为准 |
| R6 | ~~G1 文案~~ | ✅ 已改 |
| R7 | Username 解析失败话术 | 必检已含；具体 product copy 可后置（已在 OUT） |
| R8 | SKILL 0.4.0 先于代码 | **勿单独生产 install**；与 BFF 同切片 |

### 实现顺序建议

1. BFF：聚合 `issues[]` 的 validate 服务（复用 harness+排期预检）+ Plan 落库  
2. BFF：commit 入口仅 fingerprint（作废 mutate 三 plan action）  
3. Hermes：**方案 A** 注册两 tool + 裁剪逃逸入口；OpenAPI pc-plan 升正式版  
4. install SKILL/SOUL **0.4.0**（已齐文案）  
5. CI：PC-VAL / PC-CMT / PC-ESC  
6. 竖切：空中影像科类（PC-PLAN-D）→ 勾 PC-PLAN-signoff M7  

### 切流完成（v0.1.23）

BFF validate/commit + Hermes 双 tool + 卸三 plan action + SKILL 0.4.0 install 已同发；禁止回滚只卸 BFF 留 0.4.0。

### 评分（文档本身 · v0.1.20）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | 事故链完整；机制级逃逸而非再堆 skill |
| 规范可执行 | 5 | 双 tool 契约、闭环、必检表、白名单、OpenAPI 草稿齐 |
| 与上位一致 | 5 | 不改 GE；保留 M4/M5/执行器；PQ 分流清楚 |
| 测试可验 | 4 | 用例已列；代码与竖切未绿（预期） |
| 范围克制 | 5 | 无迁移、无自动延专项、OUT 明确 |
| 跨文档同步 | 5 | DOC-SYNC 表全绿（除代码实现） |
| **总评** | **可开工（整切片同发）** | 文档门闩已收；勿半上线 |

---

## 附录 H · 文档综合评价（v0.1.20 · 跨文档同步后）

### 结论

**文档面已闭环；实现同发已完成（v0.1.23）。** 相对附录 G（v0.1.19）时的短板「跨文档同步=3」，DOC-SYNC 与 BFF/plugin/install 已收口为 M7 现网。

**成熟度分层**：

| 层 | 状态 |
| -- | ---- |
| 产品共识 C49–C56 | ✅ 冻结 |
| 规范正文 §3 / §4.11 | ✅ 可编码 |
| 跨文档指针与 Agent 规程 | ✅ v0.1.20 齐 |
| OpenAPI 契约草稿 | ✅ pc-plan 0.2.0-draft；pq 弃用注 |
| 运行时代码 / 网关 tool | ⚠ 未实现（预期） |

**总评一句话**：**可以开工写代码了；不要再改产品口径，也不要半上线。**

### 一致性抽检（v0.1.20）

| 检查项 | 结果 |
| ------ | ---- |
| DOC-SYNC 表所列工件版本 | ✅ 与文件头一致 |
| SKILL 0.4.0 ↔ §4.11 主路径 | ✅ validate / issues / commit；禁 propose / invent / 塞系统结束 |
| SOUL 工具表含双 tool + PQ 分流 | ✅ |
| Hermes §13.15 ↔ 迭代 v0.1.20 | ✅ |
| OpenAPI pc-plan ↔ C50/C52 | ✅ `ok`+`issues[]`；commit 仅 fingerprint |
| pq 0.1.10 弃用三 action | ✅ 指向 pc-plan |
| GA v0.8.98 / BO v1.3.91 指针 | ✅ |
| 逃逸方案 A：§4.11.4 ↔ §4.11.8 | ✅ 白名单消歧「不是只剩两枚 tool」 |
| 对外 `ok` vs 历史 `ready` | ✅ §3.4.1 / OpenAPI 已钉 |
| 与空中影像科验收锚 | ✅ PC-PLAN-D / PC-ESC |
| 与 M4/M5/执行器 | ✅ commit 仍含 boundary+notify；微序保留 |
| `platform-tool-catalog` / tool-wiring | △ 未登记新 tool（实现时补；非规范真源） |

### 相对 v0.1.19 的跃迁

| 项 | v0.1.19 | v0.1.20 |
| -- | ------- | ------- |
| SKILL | 0.3.2 propose | **0.4.0** validate/commit |
| 跨文档同步分 | 3 | **5** |
| OpenAPI M7 | 无 | **pc-plan draft** |
| 工具面歧义 | 口语「只暴露两枚」 | **§4.11.8 白名单** |
| 实现前小项 R1/R2/R4/R6 | 开放 | **已消化** |

### 残留（不挡开工 · 实现期消化）

| # | 项 | 处置 |
| - | -- | ---- |
| H1 | BFF + plugin 未写 | M7 实现主链；同发 install |
| H2 | issues `code` 正式目录 | 实现时从 harness 抽出，对齐 PC-VAL |
| H3 | §4.10 / 附录 F 仍写 propose | 历史节；编码以 §4.11 为准 |
| H4 | C38/C39 共识行仍含历史 propose 措辞 | 可接受为里程碑考古；不必再 scrub |
| H5 | §4.11.4 第 1 条「只暴露 validate+commit」与 §4.11.8 白名单略紧 | 实现以 **§4.11.8** 为准（读/评/PQ/目标/组织仍在） |
| H6 | OpenAPI 仍 `-draft`；路径名以实现为准 | 升正式版时与 BFF 路由对齐 |
| H7 | SKILL 文案已超前代码 | **红线**：禁止单独生产 install（已写 DOC-SYNC / SKILL / 签收） |

### 实现顺序（不变 · 可执行）

1. BFF validate（issues 聚合）+ Plan 落库  
2. BFF commit-once（卸 mutate 三 plan action）  
3. Hermes 注册双 tool + 裁剪逃逸（§4.11.8）  
4. OpenAPI pc-plan 升正式版；catalog/wiring 补登记  
5. 同切片 install SKILL/SOUL 0.4.0  
6. PC-VAL/CMT/ESC + 空中影像科竖切  

### 评分（文档本身 · v0.1.20）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | 事故→机制闭环完整 |
| 规范可执行 | 5 | 契约、必检、白名单、测试 ID、编码触点齐 |
| 与上位一致 | 5 | GE/PQ/M4/M5 边界清楚 |
| 测试可验 | 4 | 文档用例齐；代码未绿 |
| 范围克制 | 5 | OUT / 无迁移 / 同发纪律清楚 |
| 跨文档同步 | 5 | DOC-SYNC 可审计 |
| 半上线防护 | 5 | 多处「勿单独 install」 |
| **总评** | **文档 Ready · 等代码同发** | 产品讨论可收口 |

---

## 附录 I · 文档综合评价（v0.1.25 · C57）

### 结论

**C57 产品+工程规格已可开工实现；文档达到「无歧义编码」门槛。** Chrome 实测假通过（validate 认 name、commit 要 id）已对症：对外只谈 `program_ref.name`、服务端解析固化、fingerprint/commit/续跑规则与 PC-REF 用例钉死；Skill **0.5.1** 给出能过审的最小完整样例，并取消强制先 scope。

**成熟度**：共识 C57 + §0.2 / §0.2.1 **冻结**；**C57-M1 BFF + PC-REF pytest 已绿**；SKILL / SOUL 文案齐，**M2 install 与 DOC-SYNC 现网化**为剩余门闩。禁止只装 Skill、回滚 BFF。

**总评一句话**：**M1 已落地；M2 同发后现网闭环。**

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| 与 2026-08-01 竖切事故 | ✅ 假通过 / schema 空转 / 逼 scope 取 id → C57 |
| 与「专项名全局唯一」 | ✅ 解析前提写死；0 命中话术固定 |
| 与「对外不扯 id」 | ✅ Skill/确认单/SOUL 禁索 uuid；HTTP 可对内回显 |
| 与 fingerprint / 同意 | ✅ 固化后算 hash；绑末次 ok |
| 与存量续跑 | ✅ commit 统一 resolve（PC-REF-06） |
| 与 C45 写权 | ✅ 解析后仍走现网新建鉴权；另码 `program_create_forbidden` |
| 与 C50/C54 | ✅ 必检表增父专项行；issues 通道不变 |
| 与 create-only | ✅ 样例 mode=create；enrich 仍废 |
| Skill 样例 vs pydantic | ✅ handoff=`to_task_key`；门控无瞎编 `op`；阶段 `op=add` |
| 半上线防护 | ✅ DOC-SYNC：Skill install 须随 BFF |

### 本轮纳入

| # | 决议 | 落点 |
| - | ---- | ---- |
| 1 | 对外只 name | C57 · §0.2 · SKILL/SOUL |
| 2 | 服务端 resolve + 固化 | §0.2 · E1/E2 |
| 3 | 用户话术 / 机器码 | §0.2 · PC-REF-03/04 |
| 4 | 最小完整样例 | SKILL **0.5.1** |
| 5 | 不强制先 scope | C57 · SOUL |
| 6 | pytest DoD | PC-REF-01～06 · E4 |

### 残留（实现期 · 非文档债）

| # | 项 | 处置 |
| - | -- | ---- |
| I1 | BFF `resolve_program_by_name` + commit 去 id 硬门槛 | ✅ C57-M1 |
| I2 | PC-REF pytest + 确认单无 uuid 断言 | ✅ C57-M1 |
| I3 | profile install Skill 0.5.1 | ✅ C57-M2 |
| I4 | Hermes §13.15 / GA 产品设计指针刷 C57 | ✅ C57-M2（§13.15 v1.9.60） |
| I5 | Playwright 竖切 | 可选，不挡合入（E4） |

### 实现顺序（可执行）

1. BFF：全局名查 program → 固化 id → fingerprint；确认单只渲染 name  
2. commit：去掉「客户端必须带 id」；入口 resolve；对齐续跑  
3. issues：`program_not_found` / `program_create_forbidden` + 用户句  
4. PC-REF-01～06 pytest  
5. 同切片 install SKILL **0.5.1** + SOUL  
6. （可选）Chrome 竖切回归 name-only 一次 commit  

### 评分（文档本身 · v0.1.25）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | 实测假通过根因→契约闭环 |
| 规范可执行 | 5 | 对外/对内、fingerprint、续跑、码与话术、样例字段齐 |
| 与上位一致 | 5 | 不改 GE 唯一性模型假设；写权仍 C45 |
| 测试可验 | 5 | PC-REF-01～06 + E4 范围清楚 |
| 范围克制 | 5 | 不做候选列表、不做强制 scope、竖切可选 |
| 跨文档同步 | 4 | 迭代+SKILL+SOUL+OpenAPI 已齐；§13.15/GA 指针待实现 PR |
| 半上线防护 | 5 | 禁止只装 Skill |
| **总评** | **文档 Ready · 可开工** | 无未决产品题 |

---

## 附录 J · 文档综合评价（v0.1.32 · C58 现网）

### 结论

**C58 已按 M1～M4 落地现网。**  
Chrome WEAK 竖切根因已对症：issue `owner`/`next_action`、结项 A1（用户指定）、Skill **0.5.2** ask_user 纪律（无轮次硬闸）、failed_partial 必出深链、Playwright 脚本侧禁狂 revalidate。与 C47/C25/C51/C55 **已对齐**。

**成熟度**：共识 **C58** + §0.3 **现网**；BFF + OpenAPI **0.2.2** + Skill/SOUL **0.5.2** + PC-OWN/SYS/PART pytest 绿；PC-PW-ASK 脚本就绪（Chrome 实跑签收不挡合入）。

**总评一句话**：**C58 现网 · 归属契约 + 结项 A1 + ask_user 行为面 + failed_partial 深链闭环。**

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| 与 2026-08-01 WEAK 竖切 | ✅ 自补 / 连打 / 结项环 / 无用户介入 → C58 |
| 与「方案 A」拍板 | ✅ §0.3.1 / §0.3.3；系统门不逼补 producer |
| 与 C47（业务门控须 produce） | ✅ A1 保留；仅系统门豁免 |
| 与 C25（E1 结项边） | ✅ A3 执行器做边，不发明同名业务任务 |
| 与 C55（禁塞系统结束） | ✅ A5 呼应 |
| 与 C50（全量 issues） | ✅ 超集字段；不改 issues 通道 |
| 与 C51（改正再 validate） | ✅ C58 改口：按 `next_action` 分流 |
| 与默认 PM 干任务 | ✅ §0.3.1；共商少问负责人 |
| 与硬闸选择 | ✅ **已撤销轮次硬闸**（v0.1.28）；靠 `next_action` + Skill |
| 与范围 1～4 | ✅ M1～M4 已交付 |
| 半上线防护 | ✅ DOC-SYNC：0.5.2 已同发 |

### 本轮纳入

| # | 决议 | 落点 |
| - | ---- | ---- |
| 1 | issue `owner` / `needs_user` / `next_action` | ✅ C58-M1 |
| 2 | 结项 A1（用户指定 end_entry） | ✅ C58-M2 |
| 3 | Skill/SOUL/plugin **0.5.2**（无轮次硬闸） | ✅ C58-M3 |
| 4 | failed_partial 必出深链 | ✅ C58-M4 |
| 5 | 用户介入验收 + Playwright ask-user | ✅ 脚本；Chrome 签收 |
| 6 | 里程碑切分 M1～M4 | ✅ 完成 |

### 残留（实现期 · 非文档债）

| # | 项 | 处置 |
| - | -- | ---- |
| J1 | BFF 打标 + OpenAPI 0.2.2 | ✅ |
| J2 | 系统结项 validate/commit 对齐 | ✅ |
| J3 | ~~硬闸计数~~ → 行为面 0.5.2 | ✅（不做硬闸） |
| J4 | Skill/SOUL **0.5.2** install | ✅ |
| J5 | failed_partial 话术 + Playwright | ✅ PC-PART-01 + smoke |
| J6 | 未知 issue code 默认 `user` | ✅ 实现约定 |

**附录 J 实现残留：清空。**

### 评分（现网 · v0.1.32）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | WEAK 竖切根因→机制闭环完整 |
| 规范可执行 | 5 | 白名单、回执字段、里程碑、测试 ID 齐 |
| 与上位一致 | 5 | C25/C47/C55/C50/C51 对齐 |
| 测试可验 | 5 | PC-OWN/SYS/PART 绿；PW-ASK 脚本就绪 |
| 范围克制 | 5 | 无轮次硬闸；未扩 evolve/GE seed |
| 跨文档同步 | 5 | DOC-SYNC 全绿 |
| 半上线防护 | 5 | 同发已完成 |
| **总评** | **C58 现网闭环** | 产品讨论可收口 |

---

## 附录 K · 文档综合评价（v0.1.48 · C65 Agent + 服务端规划）

### 结论

**C65 双轨文档已齐：Agent 面达 A-；服务端规格达 A-；合发前总评 A-（可开工）。**  
相对 v0.1.47（仅 §4.6.1 服务端规格 + SKILL 红线一条），本轮补齐 **SOUL / 话术表 / duplicate / README / eval 静态断言 / release Agent 步骤**，消除「SKILL 写了、模型读不到」的 B+ 缺口。

**成熟度分层**：

| 层 | 状态 |
| -- | ---- |
| 产品共识 C65（§4.6.1 · release D1–D8） | ✅ 冻结 |
| Agent 规程（Skill 0.5.7 + SOUL + duplicate + eval） | ✅ 文档齐 |
| BFF `create_project_with_note` 接线 | ☐ v29.00.07 |
| 生产 install + 对话探针 GA-PC-K27-AGENT-T01 | ☐ 发版签收 |

**总评一句话**：**Agent 与服务端文档均可开工；须同切片 install 0.5.7 + skstudio v29.00.07，禁止半上线。**

### 一致性检查

| 检查项 | 结果 |
| ------ | ---- |
| SKILL 0.5.7 ↔ §4.6.1 C65-1～C65-4 | ✅ 专节 + 话术表 |
| SOUL ↔ SKILL C65 | ✅ 主闭环三句 + ≥0.5.7 |
| SOUL 身份首句含「项目知识库」 | ✅ |
| project-duplicate ↔ 同 commit 执行器 | ✅ 红线 C65 |
| README 验证行 C65 | ✅ |
| release-v29.00.07 Agent 步骤 | ✅ |
| eval C65-AGENT 静态断言 | ✅ |
| §0.10 scope/DQ 与 C65 编号 | ✅ 已澄清（不冲突） |
| Hermes §13.15 C65 指针 | △ 可后置刷一行 |
| BFF 代码 | ☐ 待实现 |

### 评分（文档本身 · v0.1.48）

| 维 | 分（1–5） | 说明 |
| -- | --------- | ---- |
| 问题定义 | 5 | GA 空壳无 KB 根因 → D1–D8 + Agent 用户可感话术闭环 |
| 规范可执行 | 5 | §4.6.1 + Skill 话术表 + milestones C65-A/M 可勾选 |
| 与上位一致 | 5 | Web 同编排；C11/C16 不冲突；三分页明确 OUT |
| 测试可验 | 4 | GA-PC-K27-T01～03 + AGENT-T01 已列；代码/对话未绿 |
| 范围克制 | 5 | O1 rename 同步 OUT；存量不批量 backfill |
| 跨文档同步 | 5 | DOC-SYNC v0.1.48 可审计 |
| **Agent 可消费性** | **5（A-）** | SOUL+SKILL+duplicate+eval 五层对齐；**A 须 M3 探针 PASS** |
| 半上线防护 | 5 | release + DOC-SYNC 双写同发纪律 |
| **总评** | **A-（可开工 · 等同发后 A）** | Agent 文档从 B+ 升一级；剩代码+install+探针 |

### Agent 可消费性分级（本迭代专用）

| 级别 | 标准 | v0.1.48 |
| ---- | ---- | ------- |
| B+ | SKILL 有 C65 红线；SOUL/README 未齐 | ← v0.1.47 |
| **A-** | 五层文档齐 + eval 静态绿；探针未跑 | **← 现况** |
| A | A- + install 0.5.7 生产 + GA-PC-K27-AGENT-T01 PASS | 发版后 |

---
