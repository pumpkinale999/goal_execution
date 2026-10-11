# PRA · SDA 步骤呈现 · 分槽补丁迭代

- **文档类型**：产品需求 + 实现/测试规格（本迭代真源）
- **版本**：**v0.1.3**（2026-08-22）
- **里程碑**：**PRA-SDA-SLOT**（behalf / act / transition 分槽）
- **状态**：**现网**（MS1–MS3 + SLOT-T*；[评价 · 实现闸](./PRA-SDA步骤呈现分槽评价.md)）
- **共识真源**：[PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md) **v0.1.2** §4.0–§4.2
- **评价**：[PRA-SDA步骤呈现分槽评价.md](./PRA-SDA步骤呈现分槽评价.md)
- **上位切片**：[PRA-SDA步骤呈现迭代.md](./PRA-SDA步骤呈现迭代.md) **PRA-SDA-STEP 现网**
- **适用**：active_agent · platform-docs · skstudio（FE `→` split）；**不改** goal_execution；**不**刷 `timeline_events`

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [PRA-SDA步骤呈现共识.md](./PRA-SDA步骤呈现共识.md) **v0.1.2** | 全局人槽不变量 · act 常量 · act↔CTA |
| [PRA-SDA步骤呈现分槽评价.md](./PRA-SDA步骤呈现分槽评价.md) | 开码前 + 实现闸 |
| [PRA-SDA步骤呈现迭代.md](./PRA-SDA步骤呈现迭代.md) | 上位现网；本刀为其补丁 |
| [PRA-写后重评 / WS1.1](./PRA-项目办事态机写后重评迭代.md) | CTA/办事态已现网；本刀修 **呈现分槽** |

> **一句话**：人只进 `who`；修掉 `pra代替N` / `待N写报告`；`transition` FE 可翻；act↔CTA 同源。

---

## 0. 共识冻结（摘录 · v0.1.2）

实现不得偏离共识全文；要点：

- **§4.0** 人只进 `who`（或 transition 两端）；禁嵌 `act`/`why`/`behalf`
- **mute**：`behalf=pra代替` + 独立 `who`
- **延迟 act**：仅常量；报告链人另填 `who`
- **act ↔ 主 CTA** 同一谓词
- **transition** 两端 raw id，FE 按 `→` 分翻
- **不**刷历史 timeline

---

## 1. 目标

| 编号 | 成功标准 |
| ---- | -------- |
| **G1** | `mute_skipped` detail **无** `pra代替\d` 焊死串 |
| **G2** | 报告链 act=`待写报告` + who；**无** `待\d+写报告` |
| **G3** | act ↔ 主 CTA 同源 |
| **G4** | `a→b` FE 两端 `labelOf` |
| **G5** | SLOT-T* 绿；生产冒烟无裸数字嵌句 |

---

## 2. 实现切片

| MS | 交付 | 仓 | 状态 |
| -- | ---- | -- | ---- |
| **MS1 · mute + act** | 分槽 + SLOT-T01/T02 | active_agent | ✅ |
| **MS2 · transition + CTA** | FE `→` · SLOT-T03/T05 | AA · skstudio | ✅ |
| **MS3 · 发版冒烟** | 现网 · Chrome §7 | AA · FE · docs | ✅ |

**发布**：`active_agent` + `skstudio` + docs。**不要** `./up-prod.sh all`。

---

## 3. 测试追溯（Normative）

| ID | 落点 | 状态 |
| -- | ---- | ---- |
| **SLOT-T01** | `test_sda_step_render` / discovered_problem mute | ✅ |
| **SLOT-T02** | `test_sda_role_phrases` | ✅ |
| **SLOT-T03** | `test_sda_ctas::test_act_aligns_with_cta_*` | ✅ |
| **SLOT-T04** | transition `50→46` 形（FE split） | ✅ |
| **SLOT-T05** | `sdaPersonDetail.test.ts` | ✅ |

---

## 4. DoD

- [x] **MS1** / **MS2** / **MS3**
- [x] **SLOT-T*** 绿
- [x] 生产冒烟 §7
- [x] 本文标 **现网**

---

## 5. Follow-up（不挡本迭代）

| ID | 项 |
| -- | -- |
| **SLOT-F1** | 非延迟 `awaiting_work` 全面补 act |
| **SLOT-F2** | 标题 `_problem_for` 对齐 |
| **SLOT-F3** | CTA 文案表独立文档化 |
| **SLOT-F4** | 站外 inform 正文翻名 |

---

## 6. 风险

| 风险 | 缓解 |
| ---- | ---- |
| FE 把 `pra代替` 当 person | CJK 子串拒翻 |
| 美化 act 掩盖办事态 | SLOT-T03 |

---

## 7. 冒烟锚点（生产）

| 项 | 值 |
| -- | -- |
| A · 报告链 | 无 `pra代替N` / `待N写报告`；人名可见 |
| B · 仍补救 | act 可 `待 PM 去补救`；无裸数字嵌句 |
| C · transition | `→` 两端人名 |

---

## 8. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-22 | **v0.1.0** | 初稿 |
| 2026-08-22 | **v0.1.1** | MS1 |
| 2026-08-22 | **v0.1.2** | MS2 |
| 2026-08-22 | **v0.1.3** | MS3 现网 · DoD 全勾 |
