# 目标与执行 · GateItem 材料选择器 title 展示迭代

- **文档类型**：产品共识 + 实现/测试规格（本迭代真源）
- **版本**：**v0.3.2**（2026-08-21）
- **里程碑**：**GE-MAT-PICKER-TITLE**
- **状态**：**Accepted · 已发版 v29.00.02**
- **适用对象**：产品、skstudio 前端 / QA
- **代码范围**：`skstudio/frontend/src/execution/`（**不改** knowledge_base / GE 卫星）

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [目标与执行及其组织支撑(需求).md](./目标与执行及其组织支撑(需求).md) | §13.6.5.1 材料行「展示 Note **标题**」· 材料选择器 P0 · 线框 W2 |
| [目标与执行及其组织支撑(实现与测试).md](./目标与执行及其组织支撑(实现与测试).md) | §10.14a · **GE-T208～T211**（本迭代扩展示断言） |
| [组织知识库.md](../../knowledge_base/docs/组织知识库.md) | frontmatter `title` 必填 · `GET …/notes/by-id/{uuid}` 返回 `title` · stable id |
| 进展成果列 | §4.9.7 标题解析：树 + by-id；**禁** uuid；实现 `progressNoteTreeTitles`「never path slug」 |
| 实现 | `GateItemMaterialPicker.tsx` · `GateItemEvidenceField.tsx` · `projectNoteLink.ts` |

**动机**：更换材料弹窗根行 /「已选」用 **path 末段（slug）** 当标签，与材料行 by-id、进展表纪律不一致；业务 note **必然有 title**，属展示实现缺口，非缺数。

---

## 0. 共识冻结清单

| # | 共识 |
| - | ---- |
| **T1** | 业务 note **必然有 title**（KB `PUT` 创建/整页更新强制非空 `title:`；生产扫描无空 title） |
| **T2** | **逻辑真源 = id**（`project_note_id` / `content_ref=kb:{uuid}`）；path 可变，id 不变 |
| **T3** | **展示只用 title**；path **仅** `getTree` / 深链 / 机读 tooltip |
| **T4** | **禁止** `path.split("/").pop()`、slug、`titleFromPath` 作为选择器展示主路径 |
| **T5** | title **不要求中文**；任意非空展示名合法（中/英/混排均可） |
| **T6** | `MaterialPick.title` = **纯 title**（无「（项目根）」）；后缀仅展示层按 `noteId === projectNoteId` **拼一次** |
| **T7** | Loading：**方案 A** — 加载中不展示假已选（或仅「加载中…」）；拿到 title 后再显示「已选」 |
| **T8** | 打开时已选非根且不在首层树：对 `selectedNoteId` **再 by-id** 一次填展示 title |
| **T9** | 空 title / by-id 失败 → **异常态**（不可当正常「用 slug 顶」）；403 不泄 title |
| **T10** | **OUT**：清退全局 `titleFromPath` · 生产补 title · 搜标题 / 自动展开到深层 · 改 KB/GE API · 改 `content_ref` 形态 · 部门/组改名同步宪章 title |
| **T11** | 材料行布局：label「材料」与 CTA「**更换**」**同一行**（紧跟 label，小间距）；**标题链接单独下一行**；CTA 文案 **无省略号**（不用「更换…」） |

---

## 1. 问题与动机

### 1.1 现象

门控项「更换…」→「选择本项材料」：根行与「已选」显示拼音 slug（如 `si-you-hua-chang-jing-…（项目根）`），外层材料行已正确显示中文（或其它）文档 title。

### 1.2 根因

`GateItemMaterialPicker` 仅 `fetchProjectNotePath`，再用 path 末段当 `root.title`；丢掉 by-id 已返回的 `title`。子节点走 `node.title` 一般正确；**根与默认已选**走错路径。

### 1.3 为何不补数据

生产 Postgres + 活区 Git：业务 note **无**空 title。问题是 UI，不是 KB 缺 title。

---

## 2. 目标与非目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | 弹窗根行可见文本 = by-id `title`（+ 徽章「项目根」），**≠** path 末段 |
| **G2** | 底部「已选」在加载完成后为真实 title（根带至多一个「（项目根）」后缀） |
| **G3** | 确定后 `content_ref=kb:{noteId}`；`MaterialPick.title` 为纯 title；外层不出现双重「（项目根）」 |
| **G4** | 已选子页不在首层时，打开弹窗仍显示 by-id title（非「已选材料」占位） |
| **G5** | Vitest 钉死「展示 title ≠ path 末段」（不要求 title 为中文） |

非目标：T10。

---

## 3. 规范要求（Normative）

### 3.1 字段分工

| 字段 | 用途 |
| ---- | ---- |
| **id** | 身份、单选、`content_ref`、与 `projectNoteId` 比较是否根 |
| **title** | **唯一**用户可见标签 |
| **path** | `getTree(topic, parentPath)`、可选 `title` HTML 属性；**禁止**进可见文案主路径 |

### 3.2 打开加载流

```text
open
  → by-id(projectNoteId) → root.{ path, title, topic }
  → draftId = selectedNoteId ?? projectNoteId
  → 若 draft 是根：展示用 labelRoot(root.title)；纯 title 存 draftTitle 候选
  → 若 draft 非根：
        首层树 hit(note_id) → node.title
        未命中 → by-id(selectedNoteId).title
  → getTree(topic, root.path)；默认展开根
  → Loading 结束前：不展示「已选：…」假文案（T7）
```

### 3.3 根后缀（T6）

| 位置 | 规则 |
| ---- | ---- |
| 树根行 | `{title}` + 徽章「项目根」（徽章非 title 正文） |
| 「已选」/ EvidenceField | `isRoot ? \`${title}（项目根）\` : title` |
| `onConfirm` / `MaterialPick.title` | **仅** `title`，**不含**后缀 |

推荐抽取：`labelMaterialTitle(title, isRoot)`（EvidenceField 与 picker 共用）。

**实现态**：内部可只存 **纯 title + draftId**；凡可见「已选」文案用 `labelMaterialTitle` 计算。**禁止**把已带后缀的字符串写入 `MaterialPick.title`。

### 3.4 异常

| 情况 | 行为 |
| ---- | ---- |
| by-id 失败 / 无 path | 错误提示；不可确定 |
| by-id 403 | 不泄 title（与进展表一致） |
| 树节点无 `note_id` | 不可选（保持现状） |
| 节点 title 空 | 异常；**禁止** slug 回落 |

### 3.5 《需求》正文

**不强制**大改版本。可选：§13.6.5.1「材料选择器」补一句「节点与根均展示 Note title；path 仅导航」。材料行既有「展示 Note 标题」已覆盖展示纪律。

---

## 4. 实现要点

| 项 | 说明 |
| ---- | ---- |
| `GateItemMaterialPicker` | 入口改 `fetchNoteByStableId`；删除 path 末段当 title |
| 已选非首层 | T8 二次 by-id |
| `GateItemEvidenceField` | confirm 用纯 title + `labelMaterialTitle`；避免双重后缀；**header：材料 ∥ 更换**；标题下一行 |
| `projectNoteLink.titleFromPath` | **本轮不删**（T10）；picker **不得依赖** |
| 后端 | **无** |

线框（T11）：

```text
材料  更换
私有化场景：通算、智算…（项目根）
```

（「更换」紧跟 label，间距约 `0.5rem`；**不**右对齐拉满行宽）
---

## 5. 测试与验收

### 5.1 Vitest（normative）

| ID | 断言 |
| ---- | ---- |
| **MP-T01** | mock by-id：`path` 末段为拼音式 slug，`title` 为任意非 slug 串（中或英）→ 根行可见文本含 **title**，**不含** path 末段 |
| **MP-T02** | 默认已选为根：加载完成后「已选」含 title；至多一个「（项目根）」 |
| **MP-T03** | `onConfirm` 的 `pick.title` **不含**「（项目根）」；`pick.noteId` 正确 |
| **MP-T04** | 已选为非首层 id：打开后「已选」= by-id title（非「已选材料」） |
| **MP-T05** | 子节点仍显示 `node.title`；无 `kb:` / 裸 uuid |
| **MP-T06** | EvidenceField：`execution-gi-evidence-header` 含 label「材料」与「更换」；标题 **不在** header 内；CTA 文案为「更换」（无 `…`） |

命令（实现后）：

```bash
cd skstudio/frontend && npx vitest run \
  src/execution/components/GateItemMaterialPicker.test.tsx \
  src/execution/components/GateItemEvidenceField.test.tsx
```

### 5.2 实现文档 / GE-T

| ID | 动作 |
| ---- | ---- |
| **GE-T208** | 扩：选择器 title ≠ path 末段；材料行「材料 / 更换」同行 · 标题下一行（《需求》**v2.38.75** · 《实现》**v1.39.92**） |

**P0 不强制**新 Playwright；证据层 UI 以 Vitest 为门禁即可。

### 5.3 Chrome 冒烟

| ID | 步骤 | 期望 | 结果 |
| ---- | ---- | ---- | ---- |
| **MP-S01** | 拼音 path 项目「测试项目100101」（slug `ce-shi-xiang-mu-100101`）→ 更换 | 根行 title + 徽章「项目根」；「已选：测试项目100101（项目根）」；文案无 slug；「（项目根）」至多一处 | ✅ 本地 FE `:5173` · 2026-08-21 |
| **MP-S01p** | 生产「私有化场景：AI基座1.0部署」（slug `si-you-hua-chang-jing-ai-ji-zuo-1-0-bu-shu`）→ 技术设计方案 → 更换 | 根/已选 = title ≠ slug；外层与弹窗一致；「（项目根）」至多一处 | ✅ 生产 `v29.00.01` · 2026-08-21 |

---

## 6. 里程碑

| MS | 范围 | 状态 |
| ---- | ---- | ---- |
| **MP-MS1** | Picker 根/已选 by-id + 后缀只拼一次 + MP-T01～T05 | ✅ 代码+测 |
| **MP-MS2** | 《实现》GE-T208 + 《需求》§13.6.5.1 选择器澄清 | ✅ |
| **MP-MS3** | EvidenceField：材料 / 更换同行 · CTA 无省略号 · MP-T06 · 需求 W1 / GE-T208 | ✅ 代码+测+文档 |

---

## 7. 修订记录

| 日期 | 版本 | 说明 |
| ---- | ---- | ---- |
| 2026-08-21 | **v0.3.2** | 修：系统 GI 编辑态漏显示「更换」（structureLocked 误锁材料）；保存可带 `content_ref` |
| 2026-08-21 | **v0.3.1** | T11 微调：「更换」紧跟「材料」label（`gap: 0.5rem`），取消右对齐拉满 |
| 2026-08-21 | **v0.3.0** | **T11 / MP-MS3**：材料 label 与「更换」同行；标题下一行；文案去「…」；Vitest MP-T06；《需求》**v2.38.75** · 《实现》**v1.39.92** |
| 2026-08-21 | **v0.2.2** | **v29.00.01** 生产发版 + **MP-S01p** 冒烟通过 |
| 2026-08-21 | **v0.2.1** | **MP-S01** 本地 Chrome 冒烟通过（title≠slug、后缀一次） |
| 2026-08-21 | **v0.2.0** | **MP-MS2**：GE-T208 扩句；《需求》**v2.38.74** 选择器 title 澄清；状态收口 |
| 2026-08-21 | **v0.1.1** | **MP-MS1**：`materialTitleLabel` · Picker by-id / Loading A / 深层已选 · EvidenceField 后缀一次；Vitest MP-T01～T05 + EvidenceField 双重后缀 |
| 2026-08-21 | **v0.1.0** | 初稿：共识 T1–T10；加载流；后缀一次；Loading A；Vitest MP-T01～T05；OUT 列表 |
