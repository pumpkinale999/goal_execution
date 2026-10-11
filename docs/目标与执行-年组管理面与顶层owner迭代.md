# 目标与执行 · 年组管理面与顶层 owner（M39）

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源 · **现网**）
- **版本**：**v0.1.3**（2026-07-26）
- **里程碑**：**M39**
- **状态**：**现网**（MS1 GE · MS2 BFF+FE · MS3 GA/文档收口）
- **适用对象**：产品、skstudio / goal_execution 研发、QA、Governance Assistant

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [目标与执行-同年多顶层战略目标迭代.md](./目标与执行-同年多顶层战略目标迭代.md) | **M38 现网基线**（v0.1.5）；本迭代修订其 UI/owner 约定 |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | §3.3.8.1 / §3.3.5 |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) | §4.2.0.4 · **§4.2.0.12** · **§10.39**（DoD 真源） |
| [skstudio-壳层与导航UI迭代.md](./skstudio-壳层与导航UI迭代.md) | 左树年组 / 新建年度战略 |
| [Governance-Assistant产品设计.md](./Governance-Assistant产品设计.md) | D8 `strategic_objective` create |

> **相对 M38 被本迭代取代**：§3.3.1 强制 owner=actor · §3.4 根 ↑↓ 仅结构 Tab · 弹窗无 owner · 点年组右栏空白。交付后以本文 + 《实现》§10.39 为准。

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| C1 | 点年组头 → 右栏 **年组管理面**（虚拟节点 · 非 GE 实体） |
| C2 | 管理面：列表（name·owner·lifecycle）· ↑↓（仅 active）· 新建（年锁定）· 空态同结构 Tab |
| C3 | 左上「+ 新建年度战略」**保留**；年组面另有新建（双入口 OK） |
| C4 | 顶层 reorder **唯一**入口 = 年组面；结构 Tab **删除**「同年顶层战略」 |
| C5 | 左树只读序 · 无树内 ↑↓/拖拽 |
| C6 | **UI** 须选 owner（默认当前用户）；**API** 省略/空白 → **actor**；已传则禁止覆盖 |
| C7 | 两处新建均有负责人下拉；复制源 = **任意年**正式 company 根 |
| C8 | 行/创建成功 → 进根详情；创建后选中新根并展开年组 |
| C9 | **无** 行内改名/换 owner/归档 |
| C10 | 深链：主路径 **`/execution/years/{YYYY}`**；兼容 query `?year=` → 同面板 |
| C11 | **OUT**：年组 owner、跨年 reorder、树内拖拽、联合考核、行内编辑 |

---

## 1. 问题与动机

（同 v0.1.1）点年组空白 + 创建强制 actor，与「目标维护子目标 / 非默认须选人」心智不一致。

---

## 2. 目标与非目标

| 编号 | 成功标准 |
| ---- | -------- |
| G1 | `/execution/years/2026` 与点年组头均可打开管理面；刷新不丢 |
| G2 | 结构 Tab 无同年根 ↑↓；年组面可 ↑↓ active 根 |
| G3 | UI 提交带 owner；GE 传入原样、省略→actor |
| G4 | 左上弹窗保留且含 owner |
| G5 | GA 传 owner 则尊重；省略 → caller（经 GE fallback） |

非目标：C11。

---

## 3. 规范要求（Normative）

### 3.1 选中模型与深链

| 项 | 规则 |
| ---- | ---- |
| **主路由** | **`/execution/years/:planningYear`** → 渲染年组管理面（`GoalYearGroupDetail`） |
| **兼容** | 进入 `/execution`（或现网首页）且 query **`year={YYYY}`** → **navigate** 到 `/execution/years/{YYYY}`（replace 可） |
| **树点击** | 年组头 `onClick` → `navigate(/execution/years/{year})`；expand 行为不变 |
| **树选中态** | pathname 匹配该年时 `ExecutionTreeNode selected=true`（现网年组 `selected={false}` **须改**） |
| **与根详情互斥** | 打开某根详情时清除年组选中（或仅路径互斥，由路由自然保证） |
| **非法年** | 非 4 位年 / 越界 → 空态或 404 页内提示「无效年份」（不炸壳） |
| **无根年** | 合法年但 0 条（按过滤）→ 空态 + 新建区（C2） |

### 3.2 年组管理面 UI

| 项 | 规则 |
| ---- | ---- |
| **标题** | `{year} 年度顶层目标` · 副文案 `共 N 个`（N=当前过滤列表长度） |
| **过滤** | 与左树「全部」**同一状态源**（`showArchived` / 等价）：默认仅 active；勾选后含非 active |
| **列表** | 复用 `ExecutionStructureReorderList`（或等价）· 行：name · owner 显示名 · lifecycle · href=`/execution/objectives/{id}` |
| **↑↓** | 仅 `lifecycle_status=active` 渲染按钮并调用 `bffReorderObjective`；非 active **无** 按钮 |
| **权限** | 与现网结构写一致：`canEditStrategic` / 评审员；只读用户可见列表、无 ↑↓/无新建 |
| **空态** | testid `execution-year-group-empty` · 文案「暂无顶层战略目标」类 · **新建区仍在** |
| **新建区** | 内嵌或复用 `CreateObjectiveYearForm`：`lockedYear={year}` · 必填 name/owner · 复制源任意年 · testid `execution-year-group-create` |
| **面板 testid** | `execution-year-group-panel`（可带 `data-year`）· reorder 前缀仍 `execution-reorder-annual-root` |

### 3.3 左上弹窗

| 项 | 规则 |
| ---- | ---- |
| 组件 | `CreateObjectiveYearModal` / `CreateObjectiveYearForm` |
| 增字段 | **`ExecutionUserSelect`** · name=`owner_user_id` · 默认 `me.id`（或目录 self） |
| body | `{ planning_year, name, owner_user_id, copy_from_objective_id? }` |
| 本地校验 | 无 owner → 不提交 · 提示「请选择战略目标负责人」 |
| 成功 | 现网：关弹窗 · navigate 根详情 · expand 年组 |

### 3.4 结构 Tab 收敛

| 项 | 规则 |
| ---- | ---- |
| **删除** | `GoalObjectiveDetail` 中 `execution-objective-card-annual-roots` 整块（含 `sameYearRoots.length > 1` 条件） |
| **删除/改写测试** | `GoalObjectiveDetail.test.tsx` **M38-UI-T04**「结构 Tab 根 ↑↓」→ 改为断言卡片 **不存在**（并入 **M39-UI-T02**） |
| **保留** | 子目标 ↑↓ / 新建子目标 |

### 3.5 GE API

**文件**：`goal_execution/app/services/ge_strategic.py` · `create_objective_year`

```text
raw = body.get("owner_user_id")
owner = str(raw).strip() if raw is not None and str(raw).strip() else str(actor_user_id)
# 写入 GeObjective.owner_user_id = owner
# 禁止：忽略 body 强制 actor
```

| 输入 | 结果 |
| ---- | ---- |
| `owner_user_id: "U2"` | 存 U2 |
| 字段缺省 / `null` / `""` / `"  "` | 存 actor |
| 其它字段 | M38 不变（name/limit/copy） |

**OpenAPI** `CreateObjectiveYearRequest`：增可选 `owner_user_id`（string）；**不**入 `required`；description：`Omit or blank → actor (X-Actor-User-Id)`.

**审计** `create_objective_year` payload 含最终 `owner_user_id`。

### 3.6 BFF

| 项 | 规则 |
| ---- | ---- |
| `bffCreateObjectiveYear` | TS body 类型增 `owner_user_id?: string`；原样 POST |
| 后端透传 | 不校验、不补写 owner（GE fallback） |
| 权限 | 仍评审员 gate（现网） |

### 3.7 GA D8

**文件**：`skstudio/backend/app/services/ga_structure_mutate.py` · `_create_strategic`

| 项 | 规则 |
| ---- | ---- |
| 有 `owner_username` / `owner_user_id` | `_resolve_owner_fields` → 写入 body（与 sub 一致） |
| 皆无 | **不** 写 body.owner → GE fallback=caller（经 service actor） |
| **禁止** | 静默覆盖已解析出的非空 owner |

### 3.8 实现触点清单（Normative · 编码地图）

| 层 | 路径（预期） | 动作 |
| -- | ---- | ---- |
| GE | `app/services/ge_strategic.py` | owner fallback |
| GE | `openapi/ge-v1.yaml` | schema |
| GE | `tests/ge/test_m38_annual_roots.py` 或 `test_m39_*.py` | GE-T200/T201；T191 仍表示 omit→actor |
| BFF | `backend/.../goal_execution` years 路由 | 透传 |
| BFF | `frontend/.../api/geBff.ts` | 类型 |
| FE | `CreateObjectiveYearForm.tsx` | owner 下拉 · lockedYear |
| FE | **新** `GoalYearGroupDetail.tsx`（或 pages/） | 管理面 |
| FE | `ExecutionLayout.tsx` + router | 注册 `/execution/years/:planningYear` |
| FE | `ExecutionGoalsTree.tsx` | 年组 click + selected |
| FE | `GoalObjectiveDetail.tsx` | 删同年顶层卡片 |
| FE | 相关 `*.test.tsx` | M39-UI-* · 改写 M38-UI-T04 |
| GA | `ga_structure_mutate.py` `_create_strategic` | 透传 owner |
| GA | `test_ga_structure_mutate.py` | M39-GA-T01 |
| Docs | 本文件 · 《需求》· 《实现》§10.39 | 现网勾选 |

### 3.9 实现默认

| # | 默认 |
| - | ---- |
| I1 | owner 显示名：目录/`users` 解析；未知则回退 user id 字符串 |
| I2 | 「全部」状态：树与年组面 **共享**（layout state 或 context）；禁止两处各管一份导致不一致 |
| I3 | OpenAPI **1.25.0**（相对 1.24.0 · MS1 已登记） |
| I4 | 切片：MS1 GE → MS2 BFF+FE → MS3 GA+文档 |

---

## 4. 测试与验收

**DoD / GWT 真源**：《实现》**§10.39**（下文为索引；冲突以 §10.39 为准）。

| ID | 意图 |
| -- | ---- |
| GE-T200 | 显式 owner ≠ actor |
| GE-T201 | 省略/空白 → actor |
| M39-UI-T01 | 点年组 → 面板 + selected + 路由 |
| M39-UI-T02 | 结构 Tab **无** annual-roots 卡片（OOS 反向 / 取代 M38-UI-T04 正向） |
| M39-UI-T03 | 双新建 owner · 空态 · 非 active 无 ↑↓ |
| M39-UI-T04 | `/execution/years/YYYY` 与 `?year=` |
| M39-UI-T05 | 年组面 ↑↓ 调用 reorder · 左树序变 |
| M39-BFF-T01 | 透传 / 省略 |
| M39-GA-T01 | 有/无 owner |
| M39-OOS-01 | 不在管理面提供行内改 owner（断言无对应控件） |

**回归**：GE-T191～T199 仍绿；T191 语义 = omit owner → actor（与 T201 一致，可保留一条即可，勿重复打架）。

---

## 5. 文档回写状态

- [x] v0.1.2 实现触点 + 路由 + GWT 索引
- [x] 《需求》/《实现》/壳层/GA 指针
- [x] MS1：GE owner fallback · OpenAPI **1.25.0** · GE-T200/T201 · §10.39 DoD #1
- [x] MS2：BFF/FE 年组面 · 弹窗 owner · 结构收敛 · §10.39 DoD #2/#3
- [x] 代码 + §10.39 DoD 全勾 → **现网**

---

## 6. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-07-26 | **v0.1.3** | **现网收口**：MS1～MS3 落地 · OpenAPI 1.25.0 · DoD §10.39 全勾 |
| 2026-07-26 | **v0.1.2** | 扎实实现：主路由 `/execution/years/:year` · 触点清单 · GE/BFF/GA 伪代码级规则 · 共享「全部」状态 · 测试 ID 补 T05/OOS · 明确废止 M38-UI-T04 正向 |
| 2026-07-26 | **v0.1.1** | 边角：空态 · 非 active · 复制任意年 · API fallback · 深链 · 行内 OUT |
| 2026-07-26 | **v0.1.0** | 初版 Accepted |
