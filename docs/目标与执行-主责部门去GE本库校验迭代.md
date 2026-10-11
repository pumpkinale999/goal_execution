# 目标与执行 · 主责部门去 GE 本库校验（ORG-DEPT-GE-VAL）

- **文档类型**：产品共识 + 实现/测试规格（本迭代真源）
- **版本**：**v0.1.6**（2026-08-29）
- **里程碑**：**ORG-DEPT-GE-VAL**
- **状态**：**Accepted · 现网（`v29.01.02`）**（MS1–MS6 全勾；生产闸见评价 v0.1.4；读路径 Follow-up 见 F1/F2 迭代）
- **适用对象**：产品、skstudio / goal_execution 研发、QA、运维
- **代码范围**：`goal_execution`（写路径）· `skstudio`（BFF 校验 + FE 文案）· `platform-docs`；**不改** knowledge_base / active_agent；**本迭代不** DROP GE `org_*` 表

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [平台控制面与Postgres迁移共识.md](../../platform_docs/平台控制面与Postgres迁移共识.md) | **D2** 组织权威→skstudio；**M3** GE 去组织真源 / org 表依赖 |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | 战略字段 · 主责部门必填语义 |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) | 现行运行时：组织权威在 skstudio；本迭代收口写路径残留 |
| [目标与执行-Person身份硬切迭代.md](./目标与执行-Person身份硬切迭代.md) | **对照模式**：卫星验形态/非空，目录存在性在控制面 |
| [目标与执行-主责部门去GE本库校验评价.md](./目标与执行-主责部门去GE本库校验评价.md) | 文档闸 / 实现闸 / 发版前置 / **生产闸**综合评价与评级 |
| [skstudio-组织与企微同步.md](../../skstudio/docs/skstudio-组织与企微同步.md) | org 真源 = skstudio |

> **一句话**：GE 写 `primary_department_id` **禁止**再查本库 `org_departments`；存在性由 skstudio BFF/`org_local` 校验；同发解生产「创建子目标/专项失败」。写路径双胞胎（子目标+专项）同刀；组合读路径另开 F1。

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| **C1** | **组织权威 ≡ skstudio**：部门目录真源为 skstudio `org_departments`；GE **不得**以本库 `org_*` 行判定「部门是否存在」 |
| **C2** | **写路径收口（本刀）**：`create`/`patch` **子目标与专项**时，GE 对 `primary_department_id` 仅保留 **非空**；**删除** `_validate_department` 内 `db.get(OrgDepartment, …)` |
| **C3** | **BFF 存在性硬闸**：凡把非空 `primary_department_id` 交给 GE 的入口（`POST/PATCH` 目标与专项；GA structure mutate 同 helper）须先 `org_local` 验存在；失败 → **400** · `detail=department_not_found` |
| **C4** | **禁止灌镜像**：不得为「让 GE 校验过」再把 skstudio org 同步回 GE 空表（开倒车） |
| **C5** | **同发仓**：`goal_execution` + `skstudio` + `platform-docs`；发版顺序 **先 GE（止血）**，同日 skstudio（BFF+FE） |
| **C6** | **FK**：`primary_department_id` 对 GE 本库 `org_departments` 的 FK **DROP if exists**（`ge_objectives` + `ge_programs`）；列保留为普通引用 TEXT |
| **C7** | **本迭代不 DROP** GE `org_*` 表 / 不卸 ORM；表为空壳废墟，待组合路径另刀 |
| **C8** | **OUT（本迭代不做）**：`ge_goal_portfolio` / `ge_accountability` 对本库 org 的子树与 membership 依赖；物理 DROP `org_*`；改 OpenAPI 大版本（除非错误码叙述需补一行） |
| **C9** | **错误码**：BFF 存在性失败 = `department_not_found`；GE 缺主责 = 仍 `primary_department_required`；GE **不再**因本库查无返回 `department_not_found` |
| **C10** | **FE**：`formatGeError` 映射 `department_not_found` → 明确中文（禁止再落「操作失败，请稍后重试」） |
| **C11** | **Follow-up（已收口现网）**：[ORG-DEPT-GE-VAL-F1/F2](./目标与执行-组织组合读路径去GE本库依赖迭代.md) **v1.0.1** / `v29.01.03`；维护债 [ORG-DEPT-GE-MAINT](./目标与执行-GE组织遗留维护迭代.md) **v1.0.0** 代码就绪 |
| **C12** | **生产 schema（硬）**：生产常态 `ensure_dev_schema` = create_all + **stamp**，**不**执行增量 Alembic DROP。发版前须 **二选一**：(A) `GE_ALEMBIC_UPGRADE=1` 跑 `upgrade` 含 `032_drop_dept_org_fk`；或 (B) 先验生产两表已无 `primary_department`→`org_departments` FK。**禁止**仅 stamp 到 032 却未真正 DROP |
| **C13** | **写路径范围**：本刀覆盖 **新建/改子目标、新建/改专项、结构/详情改主责、GA 写主责**；不覆盖公司总目标无主责路径、纯建项目（不写主责）、部门组合读路径（F1） |

---

## 1. 问题与动机

### 1.1 现场症状

生产「目标管理」→ 总目标结构 Tab → **新建子目标**（例：十倍成长(测试用) · 主责「人力资源」· 2026 Q3）→ 红条 **「操作失败，请稍后重试」**。

nginx：`POST /api/v1/ge/objectives` **400**，body 长 33 → `{"detail":"department_not_found"}`；偶发 40 → `primary_department_required`。

### 1.2 根因（已确认 · 生产实证）

| 层 | 行为 | 后果 |
| -- | ---- | ---- |
| **迁移共识** | D2 / M3：组织权威 → skstudio；GE 去 org 依赖 | 目标态 |
| **切流半完成** | org 数据在 skstudio（61 行，含人力资源）；GE `org_departments` **0 行**；GE `/org` 路由已卸 | 读权威正确 |
| **UI / BFF 读** | `get_org_departments` → `org_local`（skstudio） | 可选「人力资源」 |
| **GE 写** | `_validate_department` → `db.get(OrgDepartment)`（**GE 空表**） | 恒 `department_not_found` |
| **FE** | 未映射该码 | 泛化「请稍后重试」 |
| **FK 残留（本地实证）** | 去校验后若仍有 `…_primary_department_id_fkey` | INSERT **500** IntegrityError → 仍泛化文案 |

生产复现（service + reviewer actor · 人力资源 id · 十倍成长 parent）→ 同码。**非**权限、周期、Person、企微展示问题。

### 1.3 为何必须彻底切（禁镜像）

往 GE 灌 org 副本会恢复「双真源」，与 D2 冲突，且日后企微 sync 只写 skstudio 时再次漂移。正确收口是 **断 GE 对本库 org 的写校验依赖**，并 **DROP FK**。

### 1.4 为何不止「子目标」

`primary_department_id` 写在 **`ge_objectives`（sub）与 `ge_programs`（专项）**；`_validate_department` 与 Alembic 020 FK 对两张表对称。只修子目标会留下专项/改主责双胞胎坑。部门 Portfolio 等是 **读路径**（查本库 org 子树），症状与手术不同 → **F1**，不混本刀。

---

## 2. 目标与非目标

### 2.1 目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | GE 写入非空 `primary_department_id` **不**查询本库 `OrgDepartment`；缺省仍 400 `primary_department_required` |
| **G2** | skstudio BFF：未知部门 id → 400 `department_not_found`；已知 id → 透传 GE 且创建/改成功 |
| **G3** | 生产：在「十倍成长(测试用)」下选「人力资源」可创建子目标；**并**可新建专项（同真实主责） |
| **G4** | FE 对该码展示明确文案；不再「请稍后重试」 |
| **G5** | Alembic：`032_drop_dept_org_fk`（revision id ≤32）DROP FK if exists；测试对齐 C2/C3 |
| **G6** | 本刀写路径场景全覆盖：子目标 create/patch · 专项 create/patch · GA 写主责（C13） |

### 2.2 非目标（C8）

- 本迭代 DROP GE `org_*` 表或删除 `routes_org.py` 遗留文件  
- 修复部门目标组合 / accountability 对本库 org 的读依赖（**F1**）  
- 改主责部门产品必填规则、战略周期规则、Person 规则  
- 新写 Playwright（单元测 + 手工清单足够）

---

## 3. 规范要求（Normative）

### 3.1 职责分工（对齐 M42 模式）

```text
UI / GA          →  选出或传入 department id
skstudio BFF     →  org_local 存在性（非空时）；非法 400 department_not_found
goal_execution   →  非空则落库引用；禁止查本库 org_departments；无 FK 拦 INSERT
展示名（若有）   →  skstudio / FE 目录解析；不依赖 GE 本库 org 行
```

### 3.2 GE `_validate_department`（改后）

| 输入 | 行为 |
| ---- | ---- |
| 缺省 / 空串 | 400 `primary_department_required`（子目标/专项创建等现网必填点不变） |
| 非空 | **通过**（不查表）；落库原样 trim 后字符串 |

调用点：`create_objective` / `patch_objective`（sub）/ `create_program` / `patch_program` 中凡走 `_validate_department` 者一律按上表。

### 3.3 BFF helper

| 时机 | 行为 |
| ---- | ---- |
| body 含非空 `primary_department_id` | skstudio `OrgDepartment` 按 id 查找；不存在 → 400 `department_not_found` |
| 字段缺省 / 显式清空（patch 语义允许时） | 不验存在；透传 GE 既有语义 |

**必挂入口（最小集）**

- `POST/PATCH /api/v1/ge/objectives`  
- `POST/PATCH /api/v1/ge/programs`  
- GA structure mutate 中写入 `primary_department_id` 的路径（`ge_primary_department.require_known_primary_department_id`）

### 3.4 Schema

- Alembic revision：**`032_drop_dept_org_fk`**（文件可长名；**version_num ≤32**）  
- 对 `ge_objectives` / `ge_programs` 的 `primary_department_id` FK **DROP IF EXISTS**  
- 生产可能已无 FK；迁移须幂等  
- **C12**：生产发版不得依赖 stamp  alone 完成 DROP

### 3.5 FE

| 码 | 文案（定稿） |
| -- | ------------ |
| `department_not_found` | 主责部门无效或不存在，请重新选择 |
| `primary_department_required` | 已有：须指定主责部门 |

### 3.6 本刀覆盖的写路径场景（C13）

| 场景 | 本刀 | 说明 |
| ---- | ---- | ---- |
| 新建 / 改 **子目标** 主责 | ✅ | 现场故障入口 |
| 新建 / 改 **专项** 主责 | ✅ | 同校验 + 同 FK 表 |
| 结构 / 详情 **改主责**（PATCH） | ✅ | 同字段 |
| GA structure mutate 写主责 | ✅ | 同 BFF helper |
| 公司总目标 / 年组（通常不写主责） | — | 非本链主战场 |
| 已有专项下纯建项目 | — | 项目本身一般不写该字段 |
| 部门 Portfolio / accountability | ❌ → F1 | 读路径，另刀 |

---

## 4. 实现切片与 DoD

| 切片 | 仓 | 交付 | 状态 |
| ---- | -- | ---- | ---- |
| **MS1** | goal_execution | 改 `_validate_department`；GE-T240～242 | ✅ |
| **MS2** | goal_execution | Alembic `032_drop_dept_org_fk`（≤32）；幂等 DROP | ✅ |
| **MS3** | skstudio | `ge_primary_department` + BFF/GA；SK-T240/241 | ✅ |
| **MS4** | skstudio | FE `geConstants`；FE-T240 | ✅ |
| **MS5** | platform-docs | 本文 + 评价；《实现》§5；迁移共识挂链 | ✅ |
| **MS6** | 运维 | C5+C12 发版；冒烟 G3（子目标+专项） | ✅（`v29.01.02` · 2026-08-29） |

**DoD**

- [x] C1–C13 文档与代码一致  
- [x] GE-T240～242 / SK-T240～241 / FE-T240 绿  
- [x] 本地 MS-L：子目标创建成功（含 skstudio 有、GE 无行的部门 id）  
- [x] 三仓合码 / tag（发版前置 · MS6a）  
- [x] 生产 G3 冒烟通过（MS6e：子目标 + 专项）  
- [x] 未引入 GE←skstudio org 镜像同步  

### 4.1 Mac Chrome 签收（MS-L · 本地）

| 项 | 值 |
| -- | -- |
| 日期 | 2026-08-29 |
| 账号 | victor |
| 父目标 | 在2026年数坤要成为公众公司（`312400de-…` · 结构 Tab） |
| 签收 1 | `ORG-DEPT-GE-VAL-MSL-0829` · 主责 **研发部** → 成功（201） |
| 签收 2 | 去校验后未 DROP FK 时选 **测试部门pbc** → **500**；`alembic upgrade` 032 后 `测试子目标100100-retry` → **成功** |
| 范围 | 本地 dev 栈；不新写 Playwright |
| 教训 | 半修（只去校验、留 FK）= 500 泛化文案；生产必须落实 C12 |

### 4.2 生产签收（MS6e · 2026-08-29）

| 项 | 值 |
| -- | -- |
| Tag | `v29.01.02`（GE 先 · skstudio 同日） |
| 方式 | 生产机旁 service + `X-Actor-Is-Reviewer`（浏览器登录被客户端门禁，无法用系统 Chrome 扫码） |
| 父目标 | 十倍成长(测试用) `13777cb1-d4ff-4617-994d-703feeae8e11` |
| 子目标 | `ORG-DEPT-MS6e-sub-5dcf95` · 主责 **人力资源** `066354b5-…` → **201** |
| 专项 | `ORG-DEPT-MS6e-prog-5dcf95` · 主责 **智能体** `57899d10-…` → **201** |
| 禁镜像 | 冒烟后 GE `org_departments` **仍 0 行** |
| health | `https://skbizmgmt.shukun.net/health` ok；GE `/api/v1/ge/health` ok |

---

## 5. 测试追溯

| ID | 断言 | 层 |
| -- | ---- | -- |
| **GE-T240** | 创建子目标：opaque `primary_department_id`（本库无行）→ **201** | GE |
| **GE-T241** | 缺 `primary_department_id` → 400 `primary_department_required` | GE |
| **GE-T242** | patch 子目标/专项主责：同 GE-T240 | GE |
| **SK-T240** | BFF：未知部门 → 400 `department_not_found`；未成功写 GE | skstudio |
| **SK-T241** | BFF：已知部门 → 透传成功 | skstudio |
| **FE-T240** | `formatGeError(department_not_found)` = 定稿中文 | FE |

禁止：为绿测试在 GE 测试库「假权威」恢复成生产双源叙事。

---

## 6. 发版与回滚（Normative · MS6）

| 项 | 规则 |
| -- | ---- |
| **合码** | 先合 `goal_execution` / `skstudio` / 本迭代相关 `platform-docs`；未进远程不算可发 |
| **顺序** | **GE 先** → **同日 skstudio**（C5） |
| **Schema（C12）** | (A) upgrade；或 (B) 先验 FK 已空。**禁止** stamp alone |
| **C12 实测（2026-08-29）** | 生产查询 **FK_COUNT=0** → C12-B；发版仍跑 `PROD_TAG=v29.01.02` 触发 upgrade → `032_drop_dept_org_fk`（幂等）· `alembic current` = head |
| **冒烟最小集** | ① 新建子目标；② 新建专项；③ 可选改主责/脏 id |
| **回滚** | **禁止**长期只回滚 GE 到旧校验版；须整列车回滚 |
| **禁令** | 热修「把 org 导入 GE」（C4） |

**生产 FK 检查 SQL（B 选项）** — 期望 0 行（已验）。

---

## 7. Follow-up

| ID | 项 | 说明 |
| -- | -- | ---- |
| **ORG-DEPT-GE-VAL-F1/F2** | 组合读路径 + DROP `org_*` | **现网**：[迭代](./目标与执行-组织组合读路径去GE本库依赖迭代.md) **v1.0.0** · `v29.01.03` |

---

## 8. 修订记录

| 日期 | 版本 | 说明 |
| ---- | ---- | ---- |
| 2026-08-29 | **v0.1.6** | C11 挂链 ORG-DEPT-GE-MAINT |
| 2026-08-29 | **v0.1.5** | C11/§7：挂链 F1/F2 迭代 v0.1.0（读路径另刀已开文档闸） |
| 2026-08-29 | **v0.1.4** | MS6 现网：C12 无 FK + upgrade 幂等 · GE/skstudio `v29.01.02` · 生产签收子目标+专项 201 · GE org 仍 0 |
| 2026-08-29 | **v0.1.3** | MS6a 三仓合码/tag（`v29.01.02`）；状态仍待生产 MS6b–e |
| 2026-08-29 | **v0.1.2** | 冻结 C12/C13：生产 schema 硬闸 · 写路径场景表 · 发版/冒烟/合码前置；本地 FK→500 教训入 §4.1；评价链升 v0.1.2 |
| 2026-08-29 | **v0.1.1** | MS1–MS5 落地 · Alembic revision ≤32 · 本地 Chrome · 实现闸 |
| 2026-08-29 | **v0.1.0** | 初版：生产根因 · C1–C11 · MS1–MS6 · 测试 ID |
