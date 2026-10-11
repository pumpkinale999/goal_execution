# 目标与执行 · 鉴权与 API 拓扑重构共识

- **文档类型**：架构 / 鉴权 **Normative 真源**（本轮重构）
- **版本**：**v0.1.17**（2026-08-21）
- **状态**：**CLEAN 完成**（M1–M11 + M12 残留扫尾）；**v0.1.17** M42 Person 写路径挂链；**v0.1.16** M41 谓词 **现网**（governor ∪ PMBP · `is_goal_direct_owner`）；**v0.1.15** M41 谓词修订；**v0.1.14** §5.1 双计数角标 **v0.3.1**
- **适用对象**：产品、skstudio / goal_execution 研发、QA、运维
- **系列代号**：GE-AUTHZ-API · **M1–M4** §8.2–§8.3 · 收口 **M5–M7** §8.4 · 续作 **M8–M11** §8.7 · **M12 CLEAN**

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [数字员工与Actor身份共识.md](./数字员工与Actor身份共识.md) | **Actor 主语**：人类 / 数字员工；代行 vs 履职；缺省 Actor=人类（与现网一致） |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | 产品语义（§2.6 评审员 · §3.3.5 子树负责）；谓词实现名以**本文**为准 |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) | REST / BFF / 测试；§1.4 / §4.0 旧双通道表述以本文废止并回写 |
| [平台控制面与Postgres迁移共识.md](./平台控制面与Postgres迁移共识.md) | org 权威在 skstudio；GE 不挂 `/org`（本文沿用） |
| [skstudio-建群审批-需求与设计.md](./skstudio-建群审批-需求与设计.md) | 评审员名单 `SKSTUDIO_GROUP_CREATION_REVIEWERS` |
| [组织知识库-项目Note权限迭代.md](./组织知识库-项目Note权限迭代.md) | K27 项目文档；读权与 `can_read_project` 对齐 |
| [组织知识库-鉴权与API拓扑共识.md](./组织知识库-鉴权与API拓扑共识.md) | **KB-AUTHZ**：kbase 镜像本文原则（单门 `/api/v1/kbase`） |
| [目标与执行-项目管理BP迭代.md](./目标与执行-项目管理BP迭代.md) | **M41** PMBP · 谓词 · UI · 测试 |
| [目标与执行-Person身份硬切迭代.md](./目标与执行-Person身份硬切迭代.md) | **M42** Person≡`str(users.id)` · 写路径与 Actor uid 同形 |

**冲突处理**：本轮鉴权传输与 API 拓扑以**本文**为准；与《实现》§4.0 旧「`/ge-api` vs BFF / service 上帝模式」冲突时，**以本文为准**并修订《实现》。产品能力边界（谁可读/可建）与《需求》冲突时，以《需求》为准并回写本文。

---

## 0. 统一共识（Normative）

| # | 共识 |
| - | ---- |
| C0 | **skstudio 是唯一产品入口**：浏览器、PA、GA、Hermes 等访问 GE/组织相关业务 API **必须**经 skstudio；**禁止**产品调用方直连 GE `:8092`（运维探活 / 卫星单测除外）。与 [KB-AUTHZ K0](./组织知识库-鉴权与API拓扑共识.md) 同原则。测试：前缀门禁（GE-AUTHZ-T12/T13）保持；**不得**新增「Agent 直连 GE」正路径测 |
| C1 | **skstudio** 负责 Authentication + 平台已断言事实（`actor`、`is_reviewer`、**组织事实头**）；**GE** 负责**一切 GE 能力**的 Authorization |
| C2 | **`service` token** 只表示「请求来自可信平台」，**绝不**等于已授权；废除 `auth_method==service → can_*=True` |
| C3 | **skstudio → GE** **唯一**传输：`SERVICE` + `X-Actor-User-Id` + `X-Actor-Is-Reviewer` +（按需）**组织事实头**；**任何**产品调用方**永不**持 GE service token 直打卫星 |
| C4 | **浏览器 → skstudio** 仅 `/api/v1/ge/*`；Agent 经 skstudio（`/api/v1/ge/*` 或 `/internal/pa|ga/*` 同语义门）；**`/ge-api` 已删除**（命中 **404**；**不**再承诺 308） |
| C5 | **GE 进程**仅暴露 `/api/v1/ge/*`（含助手、portfolios、health）；零例外 |
| C6 | **GE → skstudio** 回调走 skstudio `/api/v1/callbacks/ge/*`（与浏览器 BFF 前缀分离）；**禁止** GE HTTP 回调 skstudio 查组织/鉴权 |
| C7 | 谓词 **`is_goal_subtree_governor`** = 目标树 **owner 链 ∪ effective PMBP 链**（沿 parent 上溯 · [M41](./目标与执行-项目管理BP迭代.md)）；**`is_goal_direct_owner`** = 仅该节点 `owner_user_id`（问责 · **不含** PMBP）；二者 **永不**因 `is_reviewer` 变 true |
| C8 | 读/写最终权威在 **GE 谓词**；skstudio **不作**第二鉴权权威；**已删** `GE_BFF_AUTHZ_PRECHECK` / GE 侧 `require_ge_reviewer*` 符号（M9/M12；org 的 `*_org_subtree_manager` 仍保留） |
| C9 | 组织 **CRUD** 权威在 skstudio `/api/v1/org/*`；GE **不**挂 `/org`；**GE 能力**（含 portfolio/migrate）一律 `/api/v1/ge/*` 且 **在 GE 鉴权** |
| C10 | GE 若需组织关系做判定：由 skstudio **经 headers 下推最小事实集**；**API 层 skstudio ↔ GE 互不依赖**（无同步互调） |
| C11 | 浏览器 GE 读路径 **单轨**（无 jwt/bff 分叉）；兼容符号与旧 JWT 面 **硬删**（M10） |
| C12 | **`X-Actor-User-Id` ≡ `str(users.id)`**；GE 业务 Person 列写入与比较 **同形数字 id**（[M42](./目标与执行-Person身份硬切迭代.md)）；**禁止** username / candidates 作执行域 Person 鉴权 |

---

## 1. 背景与问题

现网叠了多层历史：

1. 浏览器双门：`/ge-api/*`（参与者代理）与 `/api/v1/ge/*`（治理 BFF）
2. GE 曾设想 JWT 直连；M3 AUTH-BFF-01 后只收 service，但 **service 被当成上帝模式**，参与者 ACL 被掏空
3. 评审员建项目：产品允许，GE create 只验 governor → 403 `not_subtree_governor`
4. GE 另挂 `/api/v1/internal/ge/*`、裸 `/api/v1/health`；portfolio 仍指向未挂载的 `/api/v1/org/*`

目标：一套通道、一套鉴权、清晰谓词、可测矩阵。

---

## 2. 目标态架构

```text
Browser --JWT--> skstudio /api/v1/ge/*
PA/GA/Hermes --svc+sender--> skstudio (/api/v1/ge/* 或 /internal/pa|ga/*)
                    |
                    | SERVICE + Actor + Is-Reviewer + OrgClaims(按需)
                    v
              GE /api/v1/ge/*   (仅收 skstudio 上游；全部 GE 域鉴权)
                    |
                    | SERVICE (事件回调 only · 不查组织)
                    v
         skstudio /api/v1/callbacks/ge/*

禁止：Browser / Agent 直连 GE :8092
```

| 面 | 路径 | 认证 |
|----|------|------|
| 浏览器 → skstudio | `/api/v1/ge/*` | 用户 JWT / session |
| Agent → skstudio | `/api/v1/ge/*` 或 `/internal/pa|ga/*` | skstudio internal service + sender → Actor |
| skstudio → GE | `/api/v1/ge/*` | service + Actor + IsReviewer +（按需）组织事实头 |
| GE → skstudio | `/api/v1/callbacks/ge/*` | GE service token（**仅通知**；不回查鉴权） |
| 组织 CRUD | skstudio `/api/v1/org/*` | 用户 JWT；不经 GE |

---

## 3. 传输契约（Normative）

### 3.1 通道头（始终）

| Header | 谁写 | 含义 |
|--------|------|------|
| `Authorization: Bearer <GOAL_EXECUTION_SERVICE_TOKEN>` | skstudio / GA 等 | 通道信任 |
| `X-Actor-User-Id` | 同上 | 当事人（含 act-as） |
| `X-Actor-Is-Reviewer: 0\|1` | 同上 | 是否组创建评审员（`SKSTUDIO_GROUP_CREATION_REVIEWERS`） |

### 3.2 组织事实头（Normative · 已钉死 · M8 实现）

对齐 skstudio `can_read_*_goal_portfolio` / manager·lead 语义；**不**传整棵 org 树、**不**用 JSON 巨头。普通 ge 读（projects 等）**不强制**；**仅** portfolio（及日后显式声明的 org 依赖 API）需要。

| Header | 何时 | 含义 | 格式 |
|--------|------|------|------|
| `X-Actor-Org-Portfolio-Department-Ids` | portfolio GET/相关 | actor 可读部门 portfolio 的部门 id 集合（直接/祖先 manager 可见闭包，**skstudio 计算**） | 逗号分隔；可空 |
| `X-Actor-Org-Portfolio-Team-Ids` | portfolio GET/相关 | actor 可读团队 portfolio 的团队 id 集合（team lead ∪ 可见部门下团队，**skstudio 计算**） | 逗号分隔；可空 |
| `X-Target-Org-Department-Id` | **仅** `GET …/portfolios/users/{id}` | 目标用户所属部门（skstudio 断言） | 单值；可缺 |
| `X-Target-Org-Team-Id` | **仅** user portfolio | 目标用户所属团队 | 单值；可缺 |

GE：

- 校验 service；无 Actor → 401
- **仅** service 合法时采纳 Actor / Is-Reviewer / 组织事实头；缺省 `Is-Reviewer=0`
- portfolio 等 org 依赖 API：非 reviewer 且缺判定所需头 → **403**（不默默放行）
- **禁止**浏览器 JWT 直连 GE（AUTH-BFF-01）
- **禁止**为鉴权再 HTTP 调用 skstudio
- 组织事实头 **仅** service 通道可信

---

## 4. 谓词（Normative）

| 谓词 | 定义 |
|------|------|
| `actor` | `X-Actor-User-Id` |
| `is_reviewer` | `X-Actor-Is-Reviewer == 1` |
| `is_pm(P)` | `P.pm_user_id == actor` |
| `is_participant(P)` | PM ∪ 名单成员 ∪ 任务 assignee |
| `is_creator(P)` | `P.created_by_user_id == actor`（含 draft 语义） |
| `is_goal_direct_owner(scope)` | 该 Objective/Program 的 **`owner_user_id` = actor**（**不含** PMBP · **不含**祖先 · M41） |
| `is_goal_subtree_governor(scope)` | **owner 链 ∪ effective PMBP 链**（沿 parent 上溯）；project → 其 program（**不含** PM） |
| `can_read_project(P)` | participant ∨ creator ∨ `is_goal_subtree_governor` ∨ **reviewer** |
| `can_govern_project(P)` | PM ∨ `is_goal_subtree_governor` ∨ **reviewer** |
| `can_create_project(program)` | `is_goal_subtree_governor(program)` ∨ **reviewer** |
| `can_force_delete(P)` | `is_goal_subtree_governor` ∨ reviewer（**不含**仅 PM） |
| `can_struct_objective` / `can_struct_program` | `is_goal_subtree_governor` ∨ reviewer |

说明：

- 旧名 `is_subtree_governor` / `subtree_governor` → **一律**改为 `is_goal_subtree_governor`（与 org 子树 manager 区分）
- 用户话术仍只说「负责 / 参与」，不暴露实现词
- check API：`GET /api/v1/ge/goal-subtree-governor/check` —— **忽略** reviewer（纯目标树查询）

---

## 5. 能力权限矩阵（Normative）

下列「允许」均在 **GE** 判定。失败 detail 现网只认 **`not_goal_subtree_governor`**（旧码已硬删 · M10/M12）。

### 5.1 战略树

| API | 允许当 |
|-----|--------|
| `GET /objectives` · `GET /programs` | **个人投影**（GE-VIS-1）；评审员全量；真源 [个人左树投影迭代.md](./目标与执行-个人左树投影迭代.md) |
| `GET /objectives` program 角标 | `my_visible_project_count` ≡ ACL ∩ 有效生命周期；`my_related_project_count` ≡ PM∪名单 ∩ 同排除集；不变量 related≤visible；**仅投影内 program**；真源 [左树专项相关项目数角标.md](./目标与执行-左树专项相关项目数角标.md)（「所参与」过滤已废止） |
| `GET /programs/{id}` | program ∈ 个人投影否则 **404 `not_found`**；`projects[]` 每项 `can_read_project`；响应另含双计数（**徽章口径**） |
| people-summary（prog） | `is_goal_subtree_governor ∨ is_reviewer` |
| people-summary（project） | 上 ∨ `can_read_project` |
| `POST /objectives` · PATCH/DELETE/reorder | `can_struct_*` |
| `POST /objectives/years` · `…/assess` | **仅** `is_reviewer` |
| `POST /programs` · PATCH/DELETE/reorder/assess | 结构写同上；assess **仅**评审员 |
| PATCH `owner_user_id`（objective/program） | **`is_goal_direct_owner` ∨ reviewer**（PMBP **不可** · M41） |
| PATCH `pmbp_user_id`（objective/program） | direct owner ∨ 祖先 owner ∨ reviewer（**非** 仅 effective PMBP · M41） |

### 5.2 项目

| API | 允许当 |
|-----|--------|
| `GET /projects` · `GET …/{id}` · graph | `can_read_project` |
| `POST /projects` | `can_create_project`；`created_by_user_id=actor` |
| `PATCH /projects/{id}` | `can_govern_project` |
| `PATCH …/program` | PM，或源+目标均为 goal_subtree_governor，或评审员（对齐现网 migrate） |
| `DELETE` | `can_govern_project`；非 empty 另需 `can_force_delete` 否则 409 |
| members 写 · Canvas CRUD · deviation | `can_govern_project` |
| submit | assignee 相关 ∨ `can_govern_project` |
| sign/reject | eligible signer ∨ `can_govern_project` |
| `POST /project-role-options` | **仅** `is_reviewer` |

### 5.3 队列 / 批表 / 助手

| API | 允许当 |
|-----|--------|
| `/me/queues` · `project-queue-counts` | 仅 actor 自己的；评审员**不**因此见全站队列 |
| `/me/project-access` | service+actor；评审员可 `all_visible` |
| `/users/{id}/project-access` | 同通道；平台代查 |
| `/goal-subtree-governor/check` | 同通道；**忽略** reviewer |

### 5.4 Portfolios（GE 域内鉴权 · 头名见 §3.2 · 代码 M8）

| API | 允许当（在 **GE** 判定；**不得**仅因 service 放行） |
|-----|--------------------------|
| `GET …/portfolios/departments/{id}` | `is_reviewer` ∨ `{id} ∈ X-Actor-Org-Portfolio-Department-Ids` |
| `GET …/portfolios/teams/{id}` | `is_reviewer` ∨ `{id} ∈ X-Actor-Org-Portfolio-Team-Ids` |
| `GET …/portfolios/users/{id}` | `is_reviewer` ∨ `actor == {id}` ∨ (`X-Target-Org-Department-Id` ∈ Portfolio-Department-Ids) ∨ (`X-Target-Org-Team-Id` ∈ Portfolio-Team-Ids) |
| `POST …/migrate-primary-objectives` | **仅** `is_reviewer` |

浏览器可继续打 skstudio `/api/v1/org/.../goal-portfolio`（产品 URL），内部转发 GE 时 **必须**带 Actor + Is-Reviewer + §3.2 所需头。

### 5.5 skstudio 编排

Note / ensure-docs / doc-snapshots：KB ACL 在 skstudio；调用 GE 前后仍受上表约束。编排路由**不**替代 GE 域 403。

---

## 6. API 拓扑与迁移（Normative · 零例外）

### 6.1 完成判据

GE 进程路由表中 **除** `/api/v1/ge/*` **外无其它路径**。

### 6.2 迁移表

| ID | 现网 | 目标 |
|----|------|------|
| E1 | `/api/v1/internal/ge/subtree-governor/check` · `…/users/{id}/project-access` | `/api/v1/ge/goal-subtree-governor/check` · `/api/v1/ge/users/{id}/project-access` |
| E2 | 未挂载 `/api/v1/org/.../goal-portfolio` · migrate | `/api/v1/ge/portfolios/departments\|teams\|users/{id}` · `…/migrate-primary-objectives`；删 GE `routes_org` 死代码 |
| E3 | `/api/v1/health` | `/api/v1/ge/health`（部署探活改 URL） |
| E4 | 浏览器 `/ge-api/*` | 废；统一 skstudio `/api/v1/ge/*` |
| E5 | skstudio `POST /internal/ge/deviation-notify` | skstudio `POST /api/v1/callbacks/ge/deviation-notify` |
| E6 | OpenAPI / 测试旧路径 | 一并改完，不保留双路径文档 |

**E2 浏览器面**：仍可 `GET /api/v1/org/.../goal-portfolio`（skstudio org BFF 产品 URL），内部只打 GE portfolios，并注入组织事实头；**鉴权在 GE**（§5.4）。

### 6.3 GE `/api/v1/ge/*` 能力组（收束后）

战略树 · 项目/成员 · Canvas · 偏差/队列/审计/me · portfolios · goal-subtree-governor check · users project-access · health。  
已 410：`tasks/.../start|done`、`gates/.../includes`（可删注册或继续 410）。

---

## 7. 相对现网必改（验收）

1. 废 GE service 上帝模式；stranger 不可读他人项目  
2. 统一 `X-Actor-*`；`/ge-api` 与 BFF 语义合一后废 `/ge-api`  
3. 评审员可 `POST /projects`  
4. E1–E6 路径迁移完成  
5. 谓词/符号/API 使用 `is_goal_subtree_governor` / `goal-subtree-governor`  
6. 矩阵测：IsReviewer=0/1 · governor · PM · stranger · create/delete/force  
7. DOC-SYNC：本文 + 《需求》谓词名 + 《实现》§1.4/§4.0

---

## 8. 实现切片（Normative · Phase A→E）

**原则：先谓词与矩阵测（旧路径变绿），再迁 URL；最后统一浏览器门。禁止先废 `/ge-api`。**

| Phase | 内容 | 完成判据 |
|-------|------|----------|
| **A · 谓词 + 头** | GE：`AuthUser.is_reviewer`；deps 读 `X-Actor-Is-Reviewer`；废 service 上帝模式；`is_goal_subtree_governor` 重命名；`can_create_project` / access / force_delete / struct 对齐矩阵。skstudio：proxy + `goal_execution_client` **双写** Is-Reviewer。**不改**浏览器 URL、不卸 `/ge-api` | 评审员可建项；stranger 不可读；governor check 忽略 reviewer |
| **B · 矩阵测** | 夹具 `service_headers(actor, is_reviewer=0\|1)`；补/修 stranger · PM · governor · reviewer 读写删；years/assess 仅评审员；**仍走现网路径** | GE（及必要 skstudio 契约）矩阵测绿 |
| **C · 后端路径** | E1–E3/E5；client / 探活 / OpenAPI；**同发一次切**（无长双读） | GE 路由仅 `/api/v1/ge/*`；探活与回调新 URL |
| **D · 浏览器门** | `/api/v1/ge` 透传化；PREFIX 统一；`/ge-api` → ~~308~~ **现网 404**；vite/nginx/e2e | 浏览器仅打 `/api/v1/ge/*` |
| **E · 收口** | 删旧；《实现》§1.4/§4.0 重写；状态 → **现网** | 无旧前缀；DOC-SYNC 完 |

**已完成（文档）**：本文 + 《需求》v2.38.28 / 《实现》v1.39.43 指针与废止标注。

### 8.1 Phase A 边角（已锁）

| 项 | 锁定 |
|----|------|
| 战略树结构写 + years/assess/role-options | **纳入 A** |
| BFF `require_ge_reviewer*` | **A–C 曾保留**；**现网目标：M9 硬删**（C8） |
| `/me/project-access` | **A** 去 `jwt_required` |
| act-as → `Is-Reviewer` | **effective user** |
| GA/PA → GE | A 起 Actor + IsReviewer |
| 错误码 | `not_goal_subtree_governor`；**M10 硬删**旧码兼容 |
| Phase C / M2 路径 | **同发一次切** |
| Portfolio / 废 `/ge-api` / §4.0 重写 | **M2 / M3 / M4**（portfolio **域鉴权**见 M8） |

### 8.1.1 续作边角（已锁 · 2026-08-02 · v0.1.8）

| 项 | 锁定 |
|----|------|
| Portfolio / migrate | **GE 域鉴权**；禁止 `require_service_user` 即放行（C1/C9/§5.4） |
| 组织事实 | §3.2 头名**已钉死**；skstudio 下推；GE **不** HTTP 回查；API 互不依赖（C6/C10） |
| 浏览器读路径 | **单轨**；删 `geReadVariant` / jwt\|bff 分叉（C11 · M9） |
| BFF 预检 | **硬删** `GE_BFF_AUTHZ_PRECHECK` 与作为门禁的 `require_ge_*`（C8 · M9） |
| 兼容层 | **硬删** `is_subtree_governor` alias、旧错误码双读、`*_with_user_jwt` 误导名、`decode_jwt_user` / 无用 JWT mint（C11 · M10） |
| 旧路径 | **`/ge-api` 已删 → 404**；文档/README/deploy **不再**写 308（C4 · M11） |
| 范围 | **都做**；分 **M8–M11**（§8.7） |

### 8.2 里程碑总览（Normative）

```text
M1→M4 基线现网 · M5–M7 收口已完成
M8 portfolio/组织头鉴权 → M9 单轨读+删预检 → M10 硬删兼容符号 → M11 文档/契约扫陈旧
```

| 里程碑 | Phase | 为何独立成碑 |
|--------|-------|--------------|
| **M1** | A+B | 安全债+建项 403；不碰 URL |
| **M2** | C | 后端/运维契约；与前端门解耦 |
| **M3** | D | 前端爆炸半径最大 |
| **M4** | E | 无行为变更；清双真源 |
| **M8** | 续作 | GE portfolio 鉴权 + 组织事实头（安全边界） |
| **M9** | 续作 | 读路径单轨 + 删 BFF 第二门禁 |
| **M10** | 续作 | 兼容符号/JWT 面硬删 |
| **M11** | 续作 | OpenAPI/README/《实现》陈旧表述扫净 |

不拆更碎：废上帝模式与评审员建项同改；rename 并入 M1；不合并 M2+M3。

### 8.3 里程碑 DoD 与触点

#### M1 · 鉴权语义（Phase A+B）

**DoD**

- [x] GE：无 `auth_method==service → can_*=True`（`ge_access` 及同类旁路）
- [x] GE：`AuthUser.is_reviewer`；deps 采纳 `X-Actor-Is-Reviewer`
- [x] 符号：`is_goal_subtree_governor`；403 detail 新码（兼容旧码可读）
- [x] `can_create_project`；结构写 / years / assess / role-options 按 §5
- [x] `/me/project-access` 同通道（无 `jwt_required`）
- [x] skstudio：`routes_ge_proxy` + `goal_execution_client` 双写 Is-Reviewer（effective）
- [x] 前端：`not_goal_subtree_governor` 文案映射
- [x] ~~**保留** `/ge-api` 与 BFF 强门禁~~ → **M4 已删除** `/ge-api`；BFF 门禁降为可选预检（见 M3/M4）
- [x] 矩阵测绿（§8.4）

**主触点（非穷尽）**

| 仓 | 路径 |
|----|------|
| GE | `app/auth.py` · `app/deps.py` · `app/services/ge_access.py` · `ge_subtree_governor.py`（rename）· `ge_project_create.py` · `ge_accountability.py` · `ge_orchestrator.py` · `routes_ge.py` |
| skstudio | `routes_ge_proxy.py` · `goal_execution_client.py` · `frontend/.../geConstants.ts`（错误码） |
| 测 | `tests/conftest.py` · `tests/ge/test_access.py` · `test_subtree_governor.py` · `test_create_project.py` · `test_permission_simplify.py` · `test_project_access.py`；skstudio proxy 头契约测 |

#### M2 · GE 路径收束（Phase C · 同发一次切）

**DoD**

- [x] GE 进程路由 **仅** `/api/v1/ge/*`（含 health / portfolios / check / users/…/project-access）
- [x] 卸 `/api/v1/internal/ge/*`、`/api/v1/health`；删或不再引用 `routes_org` 死代码
- [x] skstudio：`goal_execution_client` 改新路径；`POST /api/v1/callbacks/ge/deviation-notify`；GE 回调 URL 同步
- [x] 探活 / deploy / smoke 改 `/api/v1/ge/health`
- [x] OpenAPI + GE/skstudio 相关测路径更新
- [x] org BFF 浏览器仍 `/api/v1/org/.../goal-portfolio`，内部打 GE portfolios
- [x] **goal_execution + skstudio 同发**（一次切）

**主触点**

| 仓 | 路径 |
|----|------|
| GE | `main.py` · `routes_ge_internal.py`→并入 ge · portfolio 挂载 · `ge_ws_callback.py` · `openapi/ge-v1.yaml` · `scripts/ge-smoke.sh` · `deploy/**/ge-deploy*` · `tests/test_health.py` · `test_goal_portfolio.py` |
| skstudio | `goal_execution_client.py` · `routes_ge_ws.py` · `routes_org_bff.py`（portfolio）· `test_ge_deviation_pa_notify.py` · `test_org_goal_portfolio_bff.py` · `executionManifest` healthPath |

#### M3 · 浏览器单门（Phase D）

**DoD**

- [x] 浏览器只请求 skstudio `/api/v1/ge/*`（参与者透传 ≈ 旧 `/ge-api` 语义）
- [x] `/ge-api/*` **已删除**；命中 **404**；新代码不新增 `/ge-api`
- [x] 前端去掉 jwt/bff 分叉读（**M9**）
- [x] BFF 预检硬删（**M9** · C8）
- [x] vite proxy · nginx · e2e stub / 单测 URL 更新（PREFIX）；双前缀见 M5

**主触点**

| 仓 | 路径 |
|----|------|
| skstudio | `routes_ge_proxy.py` · `routes_ge_bff.py` · `routes_ge_projects.py` · `frontend/src/execution/api/client.ts` · `geViewerReads.ts` · `geBff.ts` · `executionManifest` · `vite.config.ts` · `deploy/**/nginx*` · `frontend/e2e/execution/**` · `*Mutations*.test.ts` |

#### M4 · 文档现网（Phase E）

**DoD**

- [x] 删除废弃路由/nginx `/ge-api` location（若 M3 仅 308，本碑删除）
- [x] 《实现》§1.4 / §4.0 **重写**为目标态；去掉「废止中」框
- [x] 《需求》§3.3.5 伪代码全面 `is_goal_subtree_governor`；外链版本对齐
- [x] 本文状态 → **现网**；§9 记 M1–M4 完成
- [x] 全仓无 `/api/v1/internal/ge`、`/ge-api` 业务引用（兼容期除外已结束）

### 8.4 测试 ID（建议登记到《实现》§10）

| ID | 覆盖 | 碑 |
|----|------|----|
| **GE-AUTHZ-T01** | stranger 不可读 list/graph | M1 |
| **GE-AUTHZ-T02** | participant/PM/governor 读 | M1 |
| **GE-AUTHZ-T03** | IsReviewer=1 可读非参与项目 | M1 |
| **GE-AUTHZ-T04** | governor 可建；stranger 不可建；reviewer 可建 | M1 |
| **GE-AUTHZ-T05** | force delete：governor/reviewer vs 仅 PM | M1 |
| **GE-AUTHZ-T06** | years/assess/role-options 仅 reviewer | M1 |
| **GE-AUTHZ-T07** | check API **忽略** reviewer | M1 |
| **GE-AUTHZ-T08** | `/me/project-access` service+actor；reviewer all_visible | M1 |
| **GE-AUTHZ-T09** | skstudio 上游头含 Is-Reviewer | M1 |
| **GE-AUTHZ-T10** | health / check / portfolios / callbacks 新路径 | M2 |
| **GE-AUTHZ-T11** | 浏览器 `/ge-api` → **404**（无业务入口） | M3/M4 |
| **GE-AUTHZ-T12** | e2e/fixture 无 `/api/v1/ge/ge/` 双前缀 | 收口 M5 |
| **GE-AUTHZ-T13** | 生产源码无业务 `/ge-api`（负向测例外） | 收口 M6 |
| **GE-AUTHZ-T14** | OpenAPI **1.26.1** 含 health/check/portfolios/project-access；§3.2 头说明；无 internal/ge-api 路径 | 收口 M7 / 文档续迭代 |
| **GE-AUTHZ-T15** | portfolio GET：非授权 actor 403（§5.4）；migrate 非 reviewer 403 | M8 |
| **GE-AUTHZ-T16** | §3.2 头缺失 → 不放行；非 service 通道上头无效 | M8 |
| **GE-AUTHZ-T17** | 前端无 `geReadVariant` / jwt\|bff 分叉；同 URL 行为 | M9 |
| **GE-AUTHZ-T18** | 无 `GE_BFF_AUTHZ_PRECHECK`；无 BFF 门禁替代 GE 403 | M9 |
| **GE-AUTHZ-T19** | 无 `is_subtree_governor` / `*_with_user_jwt` / `decode_jwt_user` 生产引用 | M10 |
| **GE-AUTHZ-T20** | OpenAPI summaries / README / deploy / 《实现》旧表无 JWT直连·ge-api·308 | M11 |

#### 收口碑摘要（M5–M7 · 已完成）

| 碑 | 目标 | DoD |
|----|------|-----|
| **M5** | e2e/fixture 双前缀 | stub 与 `PREFIX=/api/v1/ge` 一致 · T12 |
| **M6** | 清 `/ge-api` 残留 | manifest / act_as / proxy 测 · DoD 无「保留 ge-api」 · T11/T13 |
| **M7** | OpenAPI + 《需求》谓词名 | yaml **1.26.0** · §3.3.5 新名 · T14 · 镜像同步 |

### 8.5 逐里程碑工作包（Normative · 实现 → 测试 → 文档）

每碑固定三步，**不可跳过文档迭代**（碑末 DOC-SYNC 是 DoD 一部分）。顺序：先实现、再测绿、再改文档状态。

---

#### M1 · 鉴权语义

**1) 实现**

| 序 | 仓 | 工作 |
|----|----|------|
| 1 | GE | `AuthUser` + `deps`：读 `X-Actor-Is-Reviewer`；通道仍只收 service |
| 2 | GE | `ge_access` 等：废 service 上帝模式；合成谓词接 `is_reviewer` |
| 3 | GE | rename `is_subtree_governor` → `is_goal_subtree_governor`；detail 新码+旧码兼容 |
| 4 | GE | `can_create_project`；struct / years / assess / role-options；`/me/project-access` 去 jwt |
| 5 | skstudio | proxy + `goal_execution_client` 双写 Is-Reviewer（effective user） |
| 6 | skstudio FE | `geConstants` 映射 `not_goal_subtree_governor` |
| 7 | — | **不改** `/ge-api`、internal、health、BFF 强门禁 |

**2) 测试**

| 序 | 工作 |
|----|------|
| 1 | 夹具：`service_headers(actor, is_reviewer=0\|1)`（废「jwt≡service 上帝」语义） |
| 2 | 修红：stranger 403、list 过滤（T01/T02） |
| 3 | 新增/改：T03～T08（reviewer 读/建、force delete、years、check 忽略 reviewer、project-access） |
| 4 | skstudio：T09 抓 proxy/client 上游头 |
| 5 | 跑 GE `scripts/run_tests.sh` 相关 + skstudio 对应测；**旧 URL 仍绿** |

**3) 迭代文档**

| 序 | 工作 |
|----|------|
| 1 | 本文：M1 DoD 勾选；状态加「M1 现网 / M2–M4 规划」；§9 +1 |
| 2 | 《实现》：§10 登记 GE-AUTHZ-T01～T09；文首可注「鉴权语义已按共识 M1」 |
| 3 | 《需求》：§2.6 / 建项相关若仍写「均经 BFF 先验」则改为「域判定在 GE（M1）」 |
| 4 | **不**重写 §4.0 全文（留 M4） |

---

#### M2 · GE 路径收束（同发一次切）

**1) 实现**

| 序 | 仓 | 工作 |
|----|----|------|
| 1 | GE | check / users project-access 挂到 `/api/v1/ge/...`；卸 internal router |
| 2 | GE | `GET /api/v1/ge/health`；删裸 `/api/v1/health` |
| 3 | GE | 挂 `/api/v1/ge/portfolios/...`；删 `routes_org` 死挂载意图 |
| 4 | GE | 回调 URL → skstudio `/api/v1/callbacks/ge/deviation-notify` |
| 5 | skstudio | client 路径；`routes_ge_ws` 迁 callbacks；org BFF 内部打 portfolios |
| 6 | 运维 | smoke / deploy / manifest healthPath 同改 |
| 7 | — | **goal_execution + skstudio 同发** |

**2) 测试**

| 序 | 工作 |
|----|------|
| 1 | T10：health、check、project-access、portfolios、callbacks 新路径 200/契约 |
| 2 | 旧 internal / 裸 health → 404（确认无残留） |
| 3 | portfolio BFF 浏览器路径不变、上游为 GE portfolios |
| 4 | deviation-notify 新路径测；GE 回调集成冒烟 |
| 5 | OpenAPI paths 与运行时一致 |

**3) 迭代文档**

| 序 | 工作 |
|----|------|
| 1 | 本文：§6.2 E1–E3/E5 标完成；M2 DoD 勾选；§9 +1 |
| 2 | 《实现》/ OpenAPI：路径表改新前缀；废 internal 描述 |
| 3 | 《开发和部署》或 deploy 说明：探活 URL |
| 4 | 登记 T10 |

---

#### M3 · 浏览器单门

**1) 实现**

| 序 | 仓 | 工作 |
|----|----|------|
| 1 | skstudio | `/api/v1/ge/*` 参与者透传（≈旧 ge-api）；编排路由保留 |
| 2 | skstudio | BFF 门禁 → 可选预检；最终以 GE 403 为准 |
| 3 | FE | `client.ts` / manifest PREFIX 统一 `/api/v1/ge`；合并分叉读 |
| 4 | skstudio | `/ge-api` → 308；vite/nginx 兼容 |
| 5 | FE | e2e stub / 单测 URL |

**2) 测试**

| 序 | 工作 |
|----|------|
| 1 | T11：业务请求不打 `/ge-api`（或仅见 308） |
| 2 | 参与者：读项目/队列/canvas 经 `/api/v1/ge` 仍 200 |
| 3 | 非评审员：不再被 BFF 误 403（预检关闭或放行后 GE 判定） |
| 4 | 评审员：治理写仍成功（IsReviewer=1） |
| 5 | e2e 关键执行力冒烟（树+建项或读 graph） |

**3) 迭代文档**

| 序 | 工作 |
|----|------|
| 1 | 本文：E4 完成；M3 DoD 勾选；§9 +1 |
| 2 | 《实现》§4.0：标注「浏览器单门已落地，全文重写见 M4」或开始替换信任模型表 |
| 3 | README / 开发代理说明：去掉「必须用 `/ge-api`」 |
| 4 | 登记 T11 |

---

#### M4 · 文档现网与收口

**1) 实现（仅收口代码/配置）**

| 序 | 工作 |
|----|------|
| 1 | 删除 `/ge-api` 308 与 nginx location（兼容期结束） |
| 2 | 全仓 grep：无业务旧前缀 |
| 3 | 无行为功能开发 |

**2) 测试**

| 序 | 工作 |
|----|------|
| 1 | 回归：M1–M3 测例全绿 |
| 2 | grep/CI 门禁（可选）：禁止新增 `/ge-api`、`/api/v1/internal/ge` |
| 3 | 探活与回调生产配置抽检 |

**3) 迭代文档（本碑主业）**

| 序 | 工作 |
|----|------|
| 1 | 《实现》§1.4 / §4.0 **整节重写**为目标态；删「废止中」 |
| 2 | 《需求》§3.3.5 伪代码全面新名；读者指南 `subtree_governor` → 新名 |
| 3 | 本文：状态 **现网**；M1–M4 DoD 全勾；§9 收官 |
| 4 | OpenAPI / platform-docs 外链版本对齐；《实现》§10 GE-AUTHZ-T* 全 ☑ |

---

### 8.6 碑间纪律

| 规则 | 说明 |
|------|------|
| 一碑一合并列车 | M1 可多 PR，但发版/验收以碑为单位 |
| 测绿才 DOC-SYNC | 文档勾选不得早于测绿 |
| 禁止跨碑偷跑 | M1 不做路径；M2 不改前端 PREFIX；M3 不删文档废止框（可预写草稿） |
| 同发 | M2 / **M8**（组织头+GE portfolio）强制 GE+skstudio 同发；其余以行为兼容为准 |
| DoD 诚实 | **禁止**未落地勾选（M3 分叉读曾误勾 → 已改 M9） |

### 8.7 续作里程碑（Normative · M8–M11 · 实现 → 测试 → 文档）

边角真源：§8.1.1。每碑仍走 **实现 → 测绿 → DOC-SYNC**。

#### M8 · Portfolio 域鉴权 + 组织事实头

**状态：现网** · 头名 §3.2 · 代码已落地（T15/T16）。

**1) 实现**

| 序 | 仓 | 工作 |
|----|----|------|
| 1 | skstudio | 计算 Portfolio-Department/Team-Ids（对齐 `can_read_*_goal_portfolio`）；user portfolio 填 Target-* |
| 2 | skstudio | org BFF→GE：注入 Actor + Is-Reviewer + §3.2 头；**去掉**仅靠 BFF 的放行假设 |
| 3 | GE | `routes_ge_portfolios`：按 §5.4；migrate 非 reviewer 403 |
| 4 | GE | 缺头不放行；不 HTTP 回查 skstudio |

**2) 测试**：T15 · T16 · 回归 portfolio BFF 产品 URL。

**3) 文档**：本文 M8 DoD 勾选；《实现》§10 T15/T16 ☑；OpenAPI portfolio security 与运行时一致。

#### M9 · 读路径单轨 + 删除 BFF 第二门禁

**状态：现网** · T17/T18。

**1) 实现**

| 序 | 仓 | 工作 |
|----|----|------|
| 1 | FE | 删 `geReadVariant` / jwt\|bff；统一 `client.ts` PREFIX 读 |
| 2 | skstudio | 删 `GE_BFF_AUTHZ_PRECHECK`；`require_ge_*` 不再作门禁（编排可留，不替代 GE） |
| 3 | 测 | 评审员与参与者同 URL；过滤差在 GE 响应 |

**2) 测试**：T17 · T18。

**3) 文档**：M3 遗留 DoD 勾完；《实现》§1.4 删预检行。

#### M10 · 兼容层硬删

**状态：现网** · T19。`GOAL_EXECUTION_JWT_SECRET` **保留**（mapped-actor mint / PA·GA 仍用；非浏览器直连 GE）。

**1) 实现**：删 `ge_subtree_governor` compat、`is_subtree_governor` alias、旧错误码双读、`decode_jwt_user`、误导性 `*_with_user_jwt` 命名（改为 actor/service API）；评估废 `GOAL_EXECUTION_JWT_SECRET`（若无调用方）。

**2) 测试**：T19 + 全量相关回归。

**3) 文档**：《需求》兼容期句删除；OpenAPI 去 JWT 参与者表述。

#### M11 · 文档与外围契约扫陈旧

**状态：现网** · T20。

**1) 实现**：README / deploy / nginx 说明 / 《实现》深层历史段 / OpenAPI path summaries 与 **v0.1.10** 对齐；活文档不教「浏览器 JWT 直连 GE」或业务 `/ge-api`（负向「禁止/已废」例外）。

**2) 测试**：T20 grep 门禁（可扩 `test_ge_authz_prefix_guard` / openapi 测）。

**3) 文档**：本文状态可标「续作完成」；《实现》《需求》外链版本对齐。

---

## 9. 修订记录

| 日期 | 版本 | 说明 |
|------|------|------|
| 2026-08-21 | **v0.1.17** | **C12**：Actor uid 与 Person 写/比同形 `str(users.id)` · 链 [M42](./目标与执行-Person身份硬切迭代.md) |
| 2026-08-18 | **v0.1.16** | **M41 现网**：谓词/PATCH 门禁已落地 · 链 [M41](./目标与执行-项目管理BP迭代.md) **v0.2.0** |
| 2026-08-18 | **v0.1.15** | **M41 谓词**：C7 修订 governor = owner∪effective PMBP · 新增 **`is_goal_direct_owner`** · §4 谓词表 · §5.1 PATCH `owner`/`pmbp` 门禁 · 链 [M41](./目标与执行-项目管理BP迭代.md) **v0.1.0** |
| 2026-08-15 | **v0.1.14** | §5.1：角标双计数字段真源链 **v0.3.1**；钉 `projects[]` 可含取消/归档 ≠ 徽章口径 |
| 2026-08-05 | **v0.1.13** | 链 [数字员工与Actor身份共识](./数字员工与Actor身份共识.md)；缺省 Actor=人类；履职扩展不改 C0–C3 |
| 2026-08-02 | **v0.1.12** | **C0**：明示 skstudio **唯一产品入口**；Agent 与浏览器同拓扑（经 skstudio）；C3/C4/§2 图对齐 KB-AUTHZ；测试勿加 Agent 直连 GE 正路径（与 KB v0.1.6 工程纪律一致） |
| 2026-08-02 | **v0.1.11** | **M12 CLEAN**：剥 FE jwt\|bff 壳 · 删 GE BFF no-op · 废 skstudio `mint_mapped_actor_jwt`/`GOAL_EXECUTION_JWT_SECRET` · 修 `/ge/ge/` · T17～T20 扩 · 《需求》**v2.38.36** / 《实现》**v1.39.51** |
| 2026-08-02 | **v0.1.10** | **M8–M11 现网**：portfolio GE 鉴权+§3.2 头 · 单轨读 · 硬删兼容/预检 · 文档扫陈旧 · T15～T20；M9–M11 标现网；《需求》**v2.38.35** / 《实现》**v1.39.50** 收口 |
| 2026-08-02 | **v0.1.9** | **组织事实头钉死**（§3.2）：`X-Actor-Org-Portfolio-Department-Ids` / `…-Team-Ids` / `X-Target-Org-Department-Id` / `…-Team-Id`；§5.4 判定写死；M8 仅剩代码 |
| 2026-08-02 | **v0.1.8** | 续作边角已锁：C10/C11 · portfolio GE 鉴权 · 组织头下推 · 单轨读 · 硬删预检/兼容/旧路径 · M8–M11 · 修正 M3 误勾 |
| 2026-08-02 | **v0.1.7** | 收口 **M7**：OpenAPI **1.26.0** · 《需求》谓词名对齐 · GE-AUTHZ-T13/T14 · platform-docs openapi 镜像同步 |
| 2026-08-02 | **v0.1.6** | M1–M4 交付：鉴权语义现网 · 路径收束 · 浏览器单门 · 文档现网；收口 M5 e2e 双前缀 · M6 清 `/ge-api` 残留 |
| 2026-08-02 | **v0.1.5** | 逐里程碑工作包：每碑 **实现 → 测试 → 迭代文档**（§8.5）+ 碑间纪律（§8.6） |
| 2026-08-02 | **v0.1.4** | 文档迭代：消「短双读」矛盾；M1–M4 完整 DoD+触点；GE-AUTHZ-T01～T11；系列名收口 |
| 2026-08-02 | **v0.1.3** | 锁定里程碑 **M1–M4** 及切分理由 |
| 2026-08-02 | **v0.1.2** | 锁定 Phase A 边角 |
| 2026-08-02 | **v0.1.1** | 锁定 Phase A→E |
| 2026-08-02 | **v0.1.0** | 初版 |
