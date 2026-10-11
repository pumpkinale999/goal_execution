# 目标与执行 · Person 身份硬切（M42）

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源 · **现网**）
- **版本**：**v1.0.0**（2026-08-21）
- **里程碑**：**M42**
- **状态**：**现网**（MS1–MS4 + 新建/修改项目冒烟 + residual=0）
- **适用对象**：产品、skstudio / goal_execution 研发、QA、Governance Assistant、PRA（只读影响）

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) §2.3–§2.7 | **Person ≡ `users.id`** 上位真源；文首已挂本迭代 |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) **§10.49** | DoD **现网** |
| [openapi/ge-v1.yaml](./openapi/ge-v1.yaml) | **ge-v1 1.31.0**（Person 硬闸 · 错误码） |
| [目标与执行-鉴权与API拓扑重构共识.md](./目标与执行-鉴权与API拓扑重构共识.md) | Actor uid = `str(users.id)`；本迭代对齐写路径 |
| [Hermes与组织及目标执行的集成.md](../../platform_docs/integration/hermes-goal_execution/Hermes与组织及目标执行的集成.md) | **§6.4 已纠错**（v1.9.78）；inform §6.4.3 / M42-F2 |
| [Governance-Assistant产品设计.md](./Governance-Assistant产品设计.md) | GA mutate / create 落库身份 |
| [数字员工与Actor身份共识.md](../../platform_docs/数字员工与Actor身份共识.md) | Actor / Initiator 与 Person 列分离（本迭代不改数字员工） |

> **一句话**：GE 业务 Person 列只存 `str(users.id)`；写收口 + 双端硬闸同发；**零过渡、无双读**。

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| **C1** | **Person ≡ `users.id`**：凡业务 Person 引用非空时必须 `^\d+$` ≡ `str(users.id)` |
| **C2** | **零过渡**：禁止 Person 鉴权/队列/UI/`X-Actor-User-Ids` 双读；禁止「兼容窗口再删」；同发硬切 |
| **C3** | **对话层可 username**：Skill / GA schema 可继续 `*_username`；**落库前** BFF 必须解析为数字 id |
| **C4** | **硬闸双端**：skstudio BFF（主责 · 可读 400）+ goal_execution（最后防线 · 防绕过） |
| **C5** | **同发仓**：`skstudio` + `goal_execution` + `platform-docs`；**本迭代不改** `active_agent` 代码（下游抄 GE；存量已回填） |
| **C6** | **身份 helper（方案 B）**：Person 写入只用 `ge_person_id(user) ≡ str(user.id)`（≡ `ge_jwt_uid_for_skstudio_user` 语义，可别名）；`ge_user_id_for_skstudio_user`（username）**禁止**写 Person 列 |
| **C7** | **`system` 白名单按列**：仅 §3.3.2；**禁止**进 §3.3.1 |
| **C8** | **发版验收含 residual=0**：按 §3.7 扫表；硬闸用例绿。CI 定期扫 = **M42-F1** follow-up |
| **C9** | **OUT**：见 §2.2 |
| **C10** | **错误码钉死**：Person 格式非法 → HTTP **400** · detail **`invalid_person_user_id`**（GE 包络 `{"detail":"invalid_person_user_id"}`）；空 assignee 等语义错误仍用现网 **`invalid_assignee`**（不得混用） |
| **C11** | **OpenAPI**：`ge-v1` **1.31.0** — 声明 Person 字段须 `^\d+$`；400 示例含 `invalid_person_user_id` |

---

## 1. 问题与动机

### 1.1 现场症状

生产门控项「工程测试设计」待 **尹玉梅** 提交，弹窗却进 **只读 view**（无提交 CTA）。UI 偶发显示 `wecom:yinyumei` 而非显示名。

### 1.2 根因（已确认）

| 层 | 行为 | 后果 |
| -- | ---- | ---- |
| **产品规范** | Person ≡ `users.id` | 读写应对齐数字 id |
| **GA 写路径** | `ge_user_id_for_skstudio_user` → **`user.username`**（`wecom:…` / 短名） | 污染 `assignee_user_id` 等 |
| **运行时鉴权 / FE** | JWT / `me.id` / `canSubmitGateItem` → **数字 id** | 严格相等失败 → 无提交 |
| **文档冲突** | Hermes 集成文默认 username + candidates | 把错误路径写成「规范」 |

Canvas `ExecutionUserSelect` → `String(user.id)` 路径干净，故部分用户（始终数字）正常、部分用户（GA 写入）异常——**非企微 display 问题，是身份字面量不一致**。

### 1.3 已完成（本迭代前置 · 非代码硬切）

| 环境 | 处理 |
| ---- | ---- |
| 生产 | `wecom:*` Person 引用已回填为对应 `users.id`（尹玉梅→356 等）；`system` 保留 |
| Mac 本地 | 短名 `victor`/`anne` → 数字 id；夹具 `reviewer-1`/`demo` 无 User 行，不进生产设计 |

---

## 2. 目标与非目标

### 2.1 目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | 任意 GA / BFF / GE 写路径：§3.3.1 列落库仅为 `^\d+$`；非法 → **400 / `invalid_person_user_id`** |
| **G2** | GE 队列 / submit / sign / effective 比较与 FE CTA：**仅比数字 id**；`X-Actor-User-Ids` **仅**发 `str(id)`（可与 `X-Actor-User-Id` 同值） |
| **G3** | 文档与测试不再把「username 作 GE Person id」或 Person 域 candidates 写成规范 |
| **G4** | 发版前 residual=0；发版后无法再写入脏 Person 引用；OpenAPI **1.31.0** |

### 2.2 非目标（C9）

- 过渡期 / Person 鉴权双读 / 分阶段「先兼容再删」
- 本迭代修改 **active_agent** 服务代码（skstudio→AA 头可收窄为单 id，无需 AA 改）
- 为测试夹具 `reviewer-1` / `demo` 开生产白名单
- 组织知识库 Note frontmatter `owner` username 语义
- 补全 `display_name`（运营另做）
- **inform 投递键** 改数字 id；**inform/org 权限** 侧 `ge_user_id_candidates` 收口 → **M42-F2**（本迭代仅划界，见 §3.6 / §9）

---

## 3. 规范要求（Normative）

### 3.1 身份与比较

```text
ge_person_id(user)  :=  str(user.id)           # 唯一合法 Person 落库值
Actor / JWT uid     :=  str(user.id)           # 已有
比较（鉴权·队列·UI）:=  stored == str(actor.id)   # 禁止 candidates
X-Actor-User-Ids    :=  str(user.id)           # 单值；禁止再拼 username
```

| 场景 | 允许形态 | 落库 / 比较 |
| ---- | -------- | ----------- |
| Skill / dialog `assignee_username` | username | BFF → `ge_person_id` 后写 GE |
| Canvas / Web 选人 | `users.id` | 原样字符串 |
| inform `recipient` / sender 投递 | username 或可解析 id | **inform 通道**；不写 §3.3.1 |
| 审计 `actor_user_id` = `system` | 字面 `system` | **仅** §3.3.2 |

### 3.2 硬闸与错误码（C10）

| 层 | 时机 | 行为 |
| -- | ---- | ---- |
| **skstudio BFF / GA** | 解析后、调用 GE 前 | §3.3.1 字段非空且非 `^\d+$` → **400** · `detail=invalid_person_user_id`；username 可解析 → 写成 `str(id)` |
| **goal_execution** | 创建/PATCH/图/members/grants 写入 §3.3.1 | 同上；响应 `{"detail":"invalid_person_user_id"}`（与现网 `invalid_assignee` 包络一致） |

| 条件 | 码 |
| ---- | -- |
| Person 引用非空且 `!~ /^\d+$/`（含 `wecom:`、短名、`system` 误入业务列） | **`invalid_person_user_id`** |
| assignee/pm 为空等**语义**非法（现网已有） | **`invalid_assignee`**（不变） |
| username 无法解析为 User | BFF：**400** · 建议 `assignee_not_found` / 沿用现网「查无此人」码（**不得**静默透传） |

**正则（Normative）**：`PERSON_USER_ID_RE = re.compile(r"^\d+$")`（两端同形）。

### 3.3 列清单（对照 DDL · Normative）

> 来源：`goal_execution` Alembic `001`/`002`/`003`/`007`/`014`/`024`/`030`/`031` + 《实现》§2。空值允许处：**非空才**校验数字。

#### 3.3.1 必数字（硬闸 · residual 扫描）

| 表 | 列 | 备注 |
| -- | --- | ---- |
| `ge_objectives` | `owner_user_id` · `pmbp_user_id` | PMBP 可空 |
| `ge_programs` | `owner_user_id` · `pmbp_user_id` | 同上 |
| `ge_projects` | `pm_user_id` · `created_by_user_id` | NOT NULL |
| `ge_tasks` | `assignee_user_id` | 可空；非空必数字 |
| `ge_gate_items` | `submitted_by` · `signed_by` · `rejected_by` | 可空；API 队列或映射为 `submitted_by_user_id` |
| `ge_deviations` | `opened_by_user_id` | NOT NULL |
| `ge_project_members` | `user_id` | PK 组成部分 |
| `ge_project_note_write_grants` | `user_id` | |
| `user_org_profiles` | `user_id` · `manager_user_id`（若列仍存） | org 权威在 skstudio；GE 残留表若仍写则同闸 |
| `org_departments` | `manager_user_id` · `hrbp_user_id`（若有） | 组织任命 · Person |
| `org_teams` | `lead_user_id` | |
| `user_org_memberships` | `user_id` | |

**AA（不闸 · 间接）**：`actions.owner_user_id` / `executor_user_id` — 靠 GE 源头 + 存量回填；本迭代不改 AA。

#### 3.3.2 允许非数字（按列白名单）

| 表 / 字段 | 允许值 | 规则 |
| --------- | ------ | ---- |
| `ge_audit_events.actor_user_id` | `system` **或** `^\d+$` | `system` **仅此列族** |
| AA / PRA timeline `actor`（若镜像） | 同上 | 不进 §3.3.1 |

#### 3.3.3 明确不在本闸（避免误伤）

| 对象 | 原因 |
| ---- | ---- |
| inform 投递 payload 内 username | 非 GE Person 列 |
| `X-Sender-User-Id`（inform） | 约定为 username |
| KB ACL / Note frontmatter | 其他产品面（OUT） |

### 3.4 skstudio helper 纪律（方案 B · C6）

| 符号 | 返回值 | 用途 |
| ---- | ------ | ---- |
| **`ge_person_id`** | `str(user.id)` | **唯一** GE Person 写入；实现可 `return ge_jwt_uid_for_skstudio_user(user)` |
| `ge_jwt_uid_for_skstudio_user` | `str(user.id)` | JWT / `X-Actor-User-Id` |
| `ge_org_user_id_for_skstudio_user` | `str(user.id)` | org 同步 PK |
| `ge_user_id_for_skstudio_user` | `username` | **仅** inform 等非 Person 落库；注释：**禁止**写 §3.3.1 |
| `ge_user_id_candidates` / `ge_user_id_matches` | set / bool | **禁止**用于 GE Person 鉴权、队列、submit/sign、FE CTA、`X-Actor-User-Ids`；inform/org 见 §3.6 |

### 3.5 代码触点清单（P0 · 实现核对表）

| 仓 | 路径 | 动作 |
| -- | ---- | ---- |
| skstudio | `backend/app/services/ge/ge_user_identity.py` | 增 `ge_person_id`；注释收紧 |
| skstudio | `backend/app/services/ga_project_mutate.py` | `_lookup_*` → `ge_person_id` |
| skstudio | `backend/app/services/ga_structure_mutate.py` | `_normalize_owner_ref` → 数字；禁 opaque 非数字透传 |
| skstudio | `backend/app/services/ga_project_create_plan_commit.py` 等 create 链 | `assignee_username` → person id |
| skstudio | `backend/app/services/active_agent_client.py` | `X-Actor-User-Ids` **仅** `str(id)`（去掉 candidates 拼接） |
| skstudio | `frontend/src/execution/utils/gateItemWorkflow.ts` | 保持单轨；补 FE-M42 测 |
| goal_execution | 共享 `require_person_user_id(value)`（新） | 供 create/PATCH/graph/members/grants |
| goal_execution | `ge_orchestrator.py` · `ge_project_create.py` · graph/task PATCH · members · grants · deviations open | 写入前调用 |
| goal_execution | `ge_queues.py` / submit/sign | 确认无 candidates；否定测 GE-T233 |
| platform-docs | `openapi/ge-v1.yaml` | **1.31.0** + 字段 description / 400 例 |

### 3.6 inform / org 与 candidates（本迭代划界）

| 项 | M42 | M42-F2（follow-up） |
| -- | --- | ------------------- |
| `pa_inform.py` 用 `ge_user_id_for_skstudio_user` 作投递键 | **保留** | 可选改为 id（另议） |
| `org_scope.py` / Hermes §6.4 `ge_user_id_candidates` 比对 lead/manager | **保留读路径**（org 列已应为数字；candidates 成冗余） | 改为只比 `str(id)`；废止 Hermes Person 双读表述 |
| Person 列写 / GE 鉴权 / FE / AA Actor 头 | **禁止** candidates | — |

**Normative**：M42 合入后，任何 **新** 把 `ge_user_id_candidates` 用于 §3.3.1 比较的 PR **拒收**。

### 3.7 residual=0 扫描（C8 · 发版门禁）

对 §3.3.1 每列（非空）计数：

```sql
-- 示例：assignee（其余列同形替换）
SELECT count(*) FROM ge_tasks
WHERE assignee_user_id IS NOT NULL
  AND btrim(assignee_user_id) <> ''
  AND assignee_user_id !~ '^[0-9]+$';
```

**通过条件**：所有 §3.3.1 列计数之和 **= 0**（`ge_audit_events` **不**纳入）。  
**建议**：`goal_execution/scripts/scan_person_user_id_residual.py`（本迭代可手工 SQL；脚本化优先但非代码 DoD 阻塞）。  
**CI 定期扫** → **M42-F1**。

### 3.8 前端

- `me.id` / Act-As effective id 与图上 Person 字段 **字符串数字相等** → 提交/签收 CTA。
- 展示失败可降级显示 id；**不得**把 raw username 当鉴权成功信号。

### 3.9 OpenAPI（C11）

- 版本：**1.31.0**
- `info.description` 增一行：M42 Person 硬闸 · `invalid_person_user_id`
- 凡 request body 中 §3.3.1 对应字段：`pattern: '^[0-9]+$'`（可空字段允许 omit/null）
- 400 响应：`example: { "detail": "invalid_person_user_id" }`

---

## 4. 实现切片（MS1–MS4）

| MS | 交付 | 仓 | 依赖 |
| -- | ---- | -- | ---- |
| **MS1 · 写收口 + BFF 闸** | `ge_person_id`；GA/create 全路径；opaque 拒绝；`invalid_person_user_id`；AA 头单 id；SK-M42-* | skstudio | residual 前置已完成 |
| **MS2 · GE 硬闸 + OpenAPI** | `require_person_user_id`；写入点全覆盖；GE-T230～；**ge-v1 1.31.0** | goal_execution · platform-docs openapi | 与 MS1 **同发** |
| **MS3 · FE 回归** | FE-M42-*；冒烟：GA 指派 → 提交 CTA | skstudio | MS1 |
| **MS4 · 文档收口** | 本文 → 现网；§10.49 DoD 勾选；OpenAPI 1.31.0 已随 MS2；冲突纠错 **已提前完成** | platform-docs | MS1–MS3 绿 |

**发布顺序（同窗口）**：residual=0 复核 → 部署 **GE + skstudio** → 冒烟 → 合文档。**禁止**单侧先发。

---

## 5. 测试追溯（Normative）

> 避开 **GE-T220～T227**（M41）。本迭代：**GE-T230～T235** · **SK-M42-*** · **FE-M42-***。

| ID | 断言 |
| -- | ---- |
| **GE-T230** | PATCH/图写 `assignee_user_id=wecom:foo` → **400** `invalid_person_user_id`；`^\d+$` → 200 |
| **GE-T231** | `pm_user_id` / `owner_user_id` / members.`user_id` 非数字 → 400；`system` 写 assignee → 400 |
| **GE-T232** | `ge_audit_events.actor_user_id=system` 仍可写（不误伤） |
| **GE-T233** | 队列：assignee 与 JWT uid 均为数字且相等 → 入队；username 字面 **不**匹配（否定） |
| **GE-T234** | OpenAPI 文件 `info.version == 1.31.0`（允许；非模型 catalog 刷数） |
| **GE-T235** | 空 `assignee_user_id` 仍 → `invalid_assignee`（与格式码分离） |
| **SK-M42-01** | GA mutate：`assignee_username` → GE 落库 `str(users.id)` |
| **SK-M42-02** | GA structure：username/id 解析后数字；无法解析 → 400 |
| **SK-M42-03** | opaque 非数字 Person → `invalid_person_user_id`（禁透传） |
| **SK-M42-04** | Person 写路径不调用 `ge_user_id_for_skstudio_user`（单测或轻量 import 审计） |
| **SK-M42-05** | `active_agent_client`：`X-Actor-User-Ids` == `X-Actor-User-Id` == `str(id)`（无 username） |
| **FE-M42-01** | `canSubmitGateItem`：`"356"`/`356` → true；`wecom:x` → false |
| **FE-M42-02** | `canSignGateItem`：eligible 数字与 `me.id` 对齐 |

**禁止**：模型 catalog / config version 刷数 / candidates 集合长度快照。

---

## 6. DoD（= 《实现》§10.49）

- [x] **MS1**：写收口 + BFF 闸 + SK-M42-01～05 绿
- [x] **MS2**：GE 硬闸 + GE-T230～T235 绿 + OpenAPI **1.31.0**
- [x] **MS3**：FE-M42-01/02 + 端到端冒烟（新建/修改项目拒脏 Person）
- [x] **MS4**：§10.49 勾选 · 本文 → **现网**（Hermes/鉴权/GA/需求挂链 **已完成**）
- [x] **发版门禁**：§3.7 residual **= 0**（本地 GE 库复核）
- [x] **同发**：skstudio ↔ goal_execution 代码同窗落地（冒烟测覆盖 create/patch）

---

## 7. 文档回写清单（MS4）

| 文档 | 动作 | 规划态进度 |
| ---- | ---- | ---------- |
| 本文 | 状态 → 现网 | ✅ **v1.0.0** |
| 《实现》§10.49 | DoD 勾选 | ✅ **现网** |
| 《需求》§2.3 + 文首关联 | 交叉引用 M42 | ✅ **v2.38.76** |
| Hermes 集成 §6.4 / §7 / GO-11 | 废止默认 username · Person 禁 candidates · inform 划界 | ✅ **v1.9.78**（文档纠错，不等代码） |
| GA 产品设计 | mutate → `ge_person_id` | ✅ 结构 mutate 段已挂 M42 |
| 鉴权共识 | 写路径 = Actor uid 数字同形 | ✅ **C12 · v0.1.17** |
| `openapi/ge-v1.yaml` | **1.31.0** | ✅ |

---

## 8. 风险与回滚

| 风险 | 缓解 |
| ---- | ---- |
| 漏网脏行 → GE 闸误伤 | §3.7 residual=0；上线后盯 `invalid_person_user_id` 率 |
| inform candidates 残留造成「文档仍双读」误解 | §3.6 划界 + MS4 改 Hermes + M42-F2 |
| AA 仍接受多 id 头 | skstudio 只发单 id（SK-M42-05）；AA 代码不改 |
| 单侧先发 | **禁止** |

回滚：恢复旧写路径会再脏库。**优先修闸 / 修解析，不回滚硬闸。** 若紧急回滚 skstudio 写收口，须停 GA Person 写或接受立即再回填。

---

## 9. Follow-up（不挡 M42 现网）

| ID | 项 | 触发 |
| -- | -- | ---- |
| **M42-F1** | CI/cron residual 扫描 | M42 现网后 |
| **M42-F2** | inform/org：`ge_user_id_matches` 改为只比 `str(id)`；删或收窄 candidates | org 列 residual=0 已稳后 |
| **M42-F3** | 若发现直写 AA API 脏源 → AA 硬闸 | 出现新脏数据时 |

---

## 10. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-21 | **v1.0.0** | **现网**：MS1–MS4 · SK/GE/FE 测绿 · create/patch 冒烟拒脏 Person · 本地 residual=0 |
| 2026-08-21 | **v0.3.0** | **文档冲突纠错提前落地**：Hermes §6.4/§7/GO-11 · 鉴权 **C12** · GA mutate Person 注 · 需求/实现挂链；MS4 仅余现网勾选 |
| 2026-08-21 | **v0.2.0** | 钉死 C10/C11 错误码与 OpenAPI 1.31.0；DDL 级列清单；residual SQL；触点表；AA 头单 id；inform 划界与 M42-F*；扩测 GE-T234/235 · SK-M42-05；上位挂链 |
| 2026-08-21 | **v0.1.0** | 初稿：C1–C9 · 双端硬闸 · 方案 B · MS1–MS4 |
