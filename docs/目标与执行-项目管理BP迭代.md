# 目标与执行 · 项目管理 BP（PMBP · M41）

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源 · **现网**）
- **版本**：**v0.2.0**（2026-08-18）
- **里程碑**：**M41**
- **状态**：**现网**
- **适用对象**：产品、skstudio / goal_execution 研发、QA、Governance Assistant、PRA

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | §3.3.5 · §3.3.9 · §3.4.5 · §4.9.4 |
| [目标与执行-鉴权与API拓扑重构共识.md](./目标与执行-鉴权与API拓扑重构共识.md) | 谓词 · 能力矩阵 |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) | §2.2 · §4 · **§10.48**（DoD 真源 · **v1.39.90**） |
| [business-os共识.md](./business-os共识.md) | `goal_scope` · `owned` vs `staffed` |
| [PRA产品设计.md](./PRA产品设计.md) | `review_project` 拍板链 |
| [组织PBC共识.md](./组织PBC共识.md) | **对照** HRBP C28（组织侧 · **不**自动映射 PMBP） |

> **相对现网新增**：Objective / Program 可选 **`pmbp_user_id`**（项目管理 BP）。**能办事 ≈ owner 子树 governor**；**问责身份仍仅 `owner_user_id`**。

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| C1 | 字段 **`pmbp_user_id`**（可空）挂在 **Objective / Program**；**项目层无** PMBP（项目负责 = `pm_user_id`） |
| C2 | **能力**：PMBP 并入 **`is_goal_subtree_governor`**（读 · 结构写 · 执行治理）。项目 `POST …/activate` 已随 draft 生命周期删除；**偏差 activate 仍仅 PM**（**GE-T223**） |
| C3 | **问责**：`owner_user_id` **唯一** · PMBP **不是**「负责」· **不是** PRA/GA 默认拍板 · **不能** PATCH `owner_user_id` |
| C4 | **继承**：节点 `pmbp_user_id` 空 → **沿祖先链**取最近非空为 **effective**；**不落库复制**到子节点 |
| C5 | **任命**：写 `pmbp_user_id` = 该节点 **direct owner** ∨ **祖先 owner** ∨ **评审员**；PMBP **不能**改自己所在节点的 BP 字段 |
| C6 | **UI**：基本设置 **「负责人」正下方** 增 **「项目管理 BP」**（可选）；摘要 `负责人：A · 项目管理 BP：B`；空显示 **effective** + hint「沿自上级」 |
| C7 | **GA**：`goal_scope.active=true`（有 staffed 子树）· 节点 **`owned:false`** · 另标 **`staffed:true`**（当 effective PMBP = actor） |
| C8 | **三档能力**（见 §3.2）：办事 ✓ · 可见/会签 ✓ · 问责槽 ✗ |
| C9 | **OUT**：多人 BP · 部门 HRBP 自动映射 · 年组虚拟节点 · 项目名单角色 · 排行榜 BP 列 · 每次代操作必通知 owner（P2） |

---

## 1. 问题与动机

VP/子目标 owner 需对整棵子树负责，但日常树卫生、专项/项目落地常由 **项目管理 BP** 代跑。仅「参与」或项目名单无法覆盖 **子树结构写**；把 BP 写成第二个 `owner_user_id` 又会污染 PRA 拍板链与「负责」人事视图。

---

## 2. 目标与非目标

| 编号 | 成功标准 |
| ---- | -------- |
| G1 | PMBP 可读/可治理 owner 同范围的子树（含左树 · Program 全量 `projects[]`） |
| G2 | 人员「负责」、portfolio accountable、GA `owned`、PRA 拍板 **仍仅 owner** |
| G3 | 公司/子目标/专项详情与新建表单：负责人下可选 BP；effective 继承可见 |
| G4 | GA 对 PMBP：`governance_active` 真 · `owned` 假 · 可 mutate/建项（审计记 actor） |

非目标：C9。

---

## 3. 规范要求（Normative）

### 3.1 数据模型

| 实体 | 列 | 规则 |
| ---- | --- | ---- |
| `ge_objectives` | `pmbp_user_id` | NULLABLE · FK → `users.id` |
| `ge_programs` | `pmbp_user_id` | 同上 |

API 响应（读）建议附带（**只读派生 · 不持久化**）：

- `effective_pmbp_user_id` — 本节点或祖先最近非空
- `effective_pmbp_inherited_from` — `{ kind, id, name }` 当且仅当继承时

### 3.2 能力三档

| 档 | 示例 | PMBP |
| --- | --- | --- |
| **办事** | 左树 · 建专项/项目 · 改 graph · submit-sign · PATCH 名称/PM（非 owner） | ✓ · AuditEvent `actor_user_id` = PMBP |
| **可见/会签** | PRA 升 GA 抄送 · 结项相关 inform | ✓ 可见 · **非**默认审批槽 |
| **问责槽** | `review_project` 通过/驳回 · 战略评定生效 · 转交 `owner_user_id` · 人员「负责」 | ✗ |

**`review_project`**（《需求》§4.9.4）：审批槽 **仍** 专项 `owner_user_id`（阶梯上收子目标/公司 owner）· **不含** PMBP。

**战略评定**（§3.3.8.2）：评审员终局 · owner **可** 提交建议 · PMBP **可** 代拟建议 · **不** 单独生效。

### 3.3 谓词（实现名 · 真源链 [鉴权共识](./目标与执行-鉴权与API拓扑重构共识.md)）

```text
is_goal_direct_owner(user, scope) =
  该 Objective/Program 的 owner_user_id = user（不含祖先 · 不含 PMBP）

is_goal_subtree_governor(user, scope) =   // 修订：owner 链 ∪ PMBP 链（沿 parent 上溯）
  原 owner 链判定
  ∨ 沿 Objective 祖先链或 Program→Objective 路径上
      存在节点 effective_pmbp(user) = true

effective_pmbp(user, node) =
  node.pmbp_user_id = user
  ∨ (∃ 祖先 A · A.pmbp_user_id = user 且 node 在 A 的子树内)
```

`can_read_project` / `can_govern_project` / `can_struct_*` **不变式**：仍 OR `is_goal_subtree_governor`（已含 PMBP）。

**PATCH 门禁**：

| 字段 | 可写者 |
| --- | --- |
| `owner_user_id` | direct owner 链 governor（**仅 owner 身份**）∨ 评审员 |
| `pmbp_user_id` | direct owner ∨ 祖先 owner ∨ 评审员 · **非** 当前节点 effective PMBP  alone |

### 3.4 UI（Normative）

| 面 | 规则 |
| --- | ---- |
| **GoalObjectiveDetail / GoalProgramDetail** | 基本设置：负责人 `ExecutionUserSelect` **下** 增 BP 行 · 可选 · testid `execution-objective-pmbp-select` / `execution-program-pmbp-select` · 三态：本节点指定 / 继承（hint「沿自 {ancestor}」） / 空 · PMBP-only **disabled** |
| **摘要 meta** | `负责人：{owner} · 项目管理 BP：{effective}` · 继承时 `(沿自 {ancestor})` |
| **ExecutionDetailPageTitle** | 同上片段 · **不** 把 BP 标为「负责人」 |
| **新建子目标/专项** | 负责人下可选 BP · **默认空**（继承）· **不** 默认 = 父 owner |
| **年组管理面** | **无** BP 列（C9） |
| **项目 / 任务** | **无** BP 字段 |

### 3.5 GA / PA / PRA 消费

| 面 | 规则 |
| --- | --- |
| **GA `goal_scope.stewardship`** | `owned` = direct owner only · `staffed` = effective PMBP = actor · 子树可见性同 steward |
| **GA `goal_scope.active`** | `owned` 子树 **或** `staffed` 子树 **或** reviewer |
| **PA `goal_my_stewardship`** | **仍仅** `owner_user_id` 匹配 · PMBP **不进** owned 列表 |
| **PA 项目读集** | ≡ Web `can_read_project`（PMBP 经 governor 自动覆盖） |
| **PRA 拍板链** | 不变 · §PRA 升 GA / `review_project` |
| **M2a org alignment** | **不** 对 PMBP 做 `owner_outside_primary_dept`（允许跨部门 BP） |

---

## 4. 实现切片（MS1–MS4）

| MS | 交付 | 仓 |
| --- | --- | --- |
| **MS1 · GE** | ✅ migration `030_ge_pmbp_user_id` · `ge_goal_subtree_governor` + `_governed_program_ids_for_user` · PATCH 字段门禁 · OpenAPI **1.30.0** · **GE-T220～T227** | goal_execution |
| **MS2 · BFF+FE** | ✅ 透传 `pmbp_user_id` / `effective_pmbp_*` · 详情/新建 UI（负责人下 BP 行 · 三态）· **M41-UI-T01/T02** | skstudio |
| **MS3 · 问责面** | ✅ GA `staffed` · PA stewardship 仍仅 owner · PRA 拍板链契约测 | skstudio · active_agent |
| **MS4 · 文档收口** | ✅ 需求/鉴权/实现/本体/BO/PRA 修订 · 本文状态 → **现网** | platform-docs |

---

## 5. 测试追溯（Normative）

> 编号避开现网证据层 **GE-T210 / T211**（《实现》§10.14a）。M41 用 **GE-T220～T227**。

| ID | 断言 |
| --- | --- |
| **GE-T220** | 仅 PMBP：子树 `can_read`/`can_govern` · stranger 403 |
| **GE-T221** | 公司 PMBP：下级子目标/专项/项目可见（非 owner 的 sibling 不可见） |
| **GE-T222** | PMBP PATCH `owner_user_id` → 403 |
| **GE-T223** | PMBP activate **偏差** → 403（仅 PM；项目 activate 端点已删） |
| **GE-T224** | `list_projects` 仍无 per-project governor 调用（GE-PERF-04 回归） |
| **GE-T225** | portfolio accountable **不含** PMBP-only 行 |
| **GE-T226** | owner 任命 BP → 200 + audit；PMBP 再 PATCH `pmbp_user_id` → 403 |
| **GE-T227** | 子节点 `pmbp` 空、父有 BP → `effective_pmbp_user_id` + `inherited_from` |
| **M41-UI-T01** | 详情：负责人下 BP 行 · 摘要含 effective · 继承 hint |
| **M41-UI-T02** | 新建专项：BP 可选 · 默认空 |
| **GA-S-PMBP-01** | PMBP：`goal_scope.active` · 节点 `owned:false` · `staffed:true` |
| **PA-G-PMBP-01** | `goal_my_stewardship` 空 · `can_read_project` 非空 |
| **PRA-PMBP-01** | 升 GA 拍板人仍为子目标 owner（非 PMBP） |

**禁止**：owner 人数快照 · 模型 catalog 字面量 change-detector。

---

## 6. DoD（§10.48 摘要）

- [x] MS1：migration + 谓词 + PATCH 门禁 + GE-T220～T227 绿
- [x] MS2：三节点详情/新建 UI + M41-UI-T01/T02
- [x] MS3：GA/PA/PRA/portfolio 否定测 + GA-S-PMBP-01 + PA-G-PMBP-01 + PRA-PMBP-01
- [x] MS4：关联文档版本链 · 生产 smoke（可选 Chrome：任命 BP → 左树可见 → 负责列不出现 BP）

---

## 7. 修订记录

| 日期 | 版本 | 变更 |
| --- | --- | --- |
| 2026-08-18 | **v0.2.0** | **现网**：MS1–MS4 DoD 全勾（Chrome 冒烟仍可选） |
| 2026-08-18 | **v0.1.3** | **MS3 代码**：GA `staffed` · PA 否定 · PRA 契约测 |
| 2026-08-18 | **v0.1.2** | **MS2 代码**：详情/新建 BP 行三态 · testid 定稿 · MS2 DoD 勾选 |
| 2026-08-18 | **v0.1.1** | **MS1 代码**：测试表改 **GE-T220～T227**（避开证据层 T210/T211）· C2 注明偏差 activate 仅 PM · MS1 DoD 勾选 |
| 2026-08-18 | **v0.1.0** | 初稿：C1–C9 · 三档能力 · 谓词 · UI · GA staffed · 测试 ID |
