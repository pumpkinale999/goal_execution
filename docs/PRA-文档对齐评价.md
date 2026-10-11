# PRA 文档对齐评价（分 Milestone）

对照现网 `active_agent` / 产品契约。代码问题见 [PRA-代码问题清单.md](./PRA-代码问题清单.md)。

## Milestone 1 评价

- **文档变更摘要**：`PRA产品设计.md` → **v0.2.49**。文首/§5 标 M0–M6 现网与后置边界；§4.9 由「规划·未齐」改为现网；§3.6 推进意图现网/后置分列；Mute 代行标后置。
- **对照代码抽样**：
  - `decide.INTENT_BY_TYPE`：含 `deliver_gate` / `review_*` / `notify_phase_complete`；含 `deliver.artifact` map 但 Sense 不 emit（与后置一致）；**无** `escalate_ga` / `worsened_2w`（与后置一致）。
  - `sda.TYPE_LABELS`：`deliver`/`review` 已有（§4.8.6 徽章表仍弱 → M5）。
- **通过 / 未通过**：通过（文首/§4.9/§5 与 DoD 冲突已消）。
- **新记代码问题**：无。
- **是否可进入 N+1**：是。

---

## Milestone 2 评价

- **文档变更摘要**：`PRA-实现与测试.md` 文首 → v0.2.49；上半 Panel 现网；删「实现未齐 / 切换日前 / 现网仍三 Tab」；矩阵线框标历史；能力表深链/`Panel` 对齐。
- **对照代码抽样**：与 M6 DoD C1/C2「Panel / 废三 Tab」一致；无上半否定下半。
- **通过 / 未通过**：通过。
- **新记代码问题**：无。
- **是否可进入 N+1**：是。

---

## Milestone 3 评价

- **文档变更摘要**：`SDA.md` → 产品 v0.2.49；M6.3 仅 `deliver_gate`、artifact 后置；主 CTA=`nav_submit`；深链纪律 `?event=`；徽章色含交付/评审。
- **对照代码抽样**：
  - `assess_deliver_readiness`：不 emit artifact ✓
  - `sda._ctas` deliver：仅 `nav_submit` ✓
  - `review_verify` 驳回：`cancel_forward_tickets` **无** `gate_id` → 整项目 forward 票（见 CODE-001）
- **通过 / 未通过**：文档通过；记 1 条代码问题。
- **新记代码问题**：CODE-001。
- **是否可进入 N+1**：是。

---

## Milestone 4 评价

- **文档变更摘要**：`M2-M3.md` 标 **历史笔记**；深链/意图指向 SDA + 产品；`M4-ge-mount.md` 补报告前置（空 items ≠ 就绪、保留 items、`gate_item_id` cancel）。
- **对照代码抽样**：AA `docs/` 无「现行单一 remediate / 仅 tab=sda」现行表述；SDA/M4 与 Sense 报告前置一致。
- **通过 / 未通过**：通过。
- **新记代码问题**：无。
- **是否可进入 N+1**：是。

---

## Milestone 5 终评

- **文档变更摘要**：产品 → **v0.2.50**：§4.8.6 补 **交付/评审** 徽章与 Panel/`?event=`；新增 **§5.5 后置项一览**；GE 需求 §4.9 / 壳层叠层 / 实现 §1.7 / PRA-实现 / SDA 指针对齐 v0.2.50；问题清单定稿。
- **终检清单**：

| 项 | 结论 |
| -- | ---- |
| intent / §3.6 | 现网推进 + artifact/升 GA 后置 ✓ |
| cancel 作用域 | 文档按门控；驳回路径整项目 → **CODE-001** |
| 报告前置 | §3.3.1 / M4 笔记 ✓ |
| CTA | deliver=`nav_submit` ✓ |
| 深链 | `?event=` 主路径 ✓ |
| 文首三态 | 现网 / 后置 / 废止 ✓；§5.5 集中后置 ✓ |
| 徽章 | 交付/评审与 `TYPE_LABELS` ✓ |

- **一致性结论**：**一致**；残留 = **后置（§5.5）** + 已记录代码问题 **CODE-001 / CODE-002**。
- **代码问题清单**：[PRA-代码问题清单.md](./PRA-代码问题清单.md)（2 条，本轮不修）。
- **通过 / 未通过**：通过。
- **是否启动代码修复**：**否**（另开工作项）。

---

# 代码与文档收口（续）

## 收口 Milestone 1 评价（CODE-001）

- **实现**：`review_verify` 中 `review_gate` 驳回 → `cancel_forward_tickets(..., gate_id=gate_id)`；`review_project` 仍整项目。
- **测试**：`tests/test_m6_review.py` 全绿（含新增 `test_review_reject_cancels_only_same_gate`）。
- **文档**：产品 **v0.2.51** cancel 作用域表；SDA M6.4；实现 A2；GE §4.9.6；清单 CODE-001 **已修**。
- **通过 / 未通过**：通过。
- **是否可进入收口 M2**：是。

## 收口 Milestone 2 评价（CODE-002 + 噪音）

- **实现**：无业务代码。
- **文档**：DoD A4 与 suppressed/后置对齐；§5.5 等文档卡 **已裁定不投影**；GE changelog 加历史脚注；v2.38.65 标现网。
- **闸门**：主契约无「等文档 · 现网」与 suppressed 并存 ✓。
- **通过 / 未通过**：通过。
- **是否可进入收口 M3**：是。

## 收口 Milestone 3 终评

- **测试**：`test_m6_review.py` 10 passed（含双门控隔离）。
- **终检抽样**：

| 项 | 结论 |
| -- | ---- |
| intent / 后置 | deliver_gate 现网；artifact / 升 GA 后置 ✓ |
| cancel 作用域 | `review_gate` 驳回传 `gate_id` ✓；`review_project` 整项目 ✓ |
| waiting | suppressed；A4/§5.5 后置 ✓ |
| 深链 / Panel | `?event=`；废三 Tab ✓ |
| 徽章 | 交付/评审 ✓ |

- **一致性结论**：**一致**。残留仅 **§5.5 后置能力** + 实现总账已承认软缺口（GE 延迟转段 / E2E 全量）。
- **问题清单**：无待修项（CODE-001 已修、CODE-002 已关）。
- **通过 / 未通过**：通过。
- **本轮不做**：升 GA、artifact 开票、Mute 代行、waiting 卡投影、GE 延迟转段、Playwright 全量。
