# PRA · SDA 步骤呈现共识

- **文档类型**：产品/实现共识（切片真源）
- **版本**：**v0.1.2**（2026-08-22）
- **状态**：**现网**（迭代见 [PRA-SDA步骤呈现迭代.md](./PRA-SDA步骤呈现迭代.md)；分槽补丁见 [分槽迭代](./PRA-SDA步骤呈现分槽迭代.md)；评价见 [PRA-SDA步骤呈现评价.md](./PRA-SDA步骤呈现评价.md)）
- **上位**：[PRA产品设计.md](./PRA产品设计.md) §4.8.6 · [PRA-实现与测试.md](./PRA-实现与测试.md) § SDA
- **动机**：履历括号缺人/缺因（催促、升不动等）→ 卡面无意义；`_step_dict` if 丛林难维护

> **一句话**：SDA 卡呈现分四层；履历用**槽位 + 步骤模板**渲染；本刀先落地模板与 chase/escalate 写契约；不刷历史 timeline。

---

## 1. 问题共识（已确认）

| # | 共识 |
| - | ---- |
| **P1** | 「催促 / 已升级」括号无人，不是 FE 丢名，是写库 payload 与投影规则不齐。 |
| **P2** | 全生命周期多 intent **共用**同一套步骤词表；不是每 intent 一套话术。 |
| **P3** | 用户可见字还有标题 / CTA / inform / 非延迟 act 等旁路；**本刀只收履历步骤模板**（+ chase/escalate 写路径）。 |
| **P4** | 禁止用 Action 现状字段「猜」完整履历当主路径；legacy 仅投影显式回退。 |

---

## 2. 四层呈现（Normative）

| 层 | 内容 | 本刀 |
| -- | ---- | ---- |
| **① 身份** | 进程/类型徽章 · 标题 · role_hint · **进度摘要行** | 进度行 = 末步 `label` + `detail`（与 timeline 同文；可截断） |
| **② 履历** | `steps[]` 通用步骤 + 括号 | **主力：槽位 + 模板** |
| **③ 行动** | 末步 CTA | **不动**（仍 `_ctas`） |
| **④ 角色叙事** | 延迟票末条 `awaiting_work` 的 act 短语 | 仍 `_remediate_awaiting_role_phrase` → 填 `act` 槽 |

句式：`{步骤名}（{槽…}，{时间}）`。步骤名通用稳定；人/时/事(因)只进括号。

---

## 3. 履历五段与步骤词表（Normative）

事理段：发现 → 开票前闸 → 派遣做事 → 催促升级 → 收口。

| step_key | 展示名 | 模板槽（顺序） |
| -------- | ------ | -------------- |
| `discovered` | 发现问题 | `what` · `when` |
| `awaiting_approval` | 待确认 | `who` · `when` |
| `mute_skipped` | mute模式下跳过人类审批 | `behalf` · `who` · `when` |
| `notified` | 已通知 | `who` · `when` |
| `awaiting_work` | 待执行 | 延迟末步：`act` ·（可选 `who`）· `when`；其它：`who` · `when` |
| `reassigned` | 已改派执行人 | `transition` · `when`（两端 raw id，FE 翻名） |
| `chased` | 催促 | `nth` · `who` · `when` |
| `owner_escalated` | 已升级负责人 | 升成：`transition` · `when`；升不动：`why` · `who` · `when` |
| `rejected` | 驳回 | `why` · `who` · `when` |
| `completed` | 完成 | `who` · `when` |
| `cancelled` | 已取消 | `why` · `when` |

---

## 4. 槽位（Normative）

| 槽 | 含义 | 实现 |
| -- | ---- | ---- |
| `when` | 时间 | 每步；`mm-dd HH:MM` |
| `who` | 人（可多人 `、`） | raw user id；FE `labelOf` |
| `what` | 事态 / 问题 | 与 `why` **共用** `slot_clause` |
| `why` | 因果 | 同上 |
| `act` | 待办动作短语 | 延迟角色叙事等 |
| `transition` | `旧→新` | 升级成功、改派 |
| `nth` | `第N次` | 催促 |
| `behalf` | 常量前缀 **`pra代替`**（**不含** id） | mute；**人走独立 `who`** |
| `transition` | 两端各为 raw id | 升级成功、改派；FE 对 `→` 两侧分别 `labelOf`（或投影拆成两 who） |

规则：多数步骤 `what` / `why` **二选一**；催促 **不**硬塞 why。`system` actor **不得**单独充当 `who`。

### 4.0 全局不变量（Normative · v0.1.2）

凡用户可见履历括号里出现「人」，**只许**进独立 `who`（或 `transition` 两端 id）。**禁止**把 user id 嵌进 `act` / `why` / `behalf` 整句。

| 违规（禁止） | 正确 |
| ------------ | ---- |
| `pra代替4` | `pra代替` + who=`4` |
| `待4写报告` | act=`待写报告` + who=`4` |
| `升不动，仍为50`（id 进 why） | why=`升不动，仍为` + who=`50`（已钉 · v0.1.1） |

### 4.1 钉死文案常量

| 场景 | 常量 |
| ---- | ---- |
| escalate `stopped` 的 `why` | **`升不动，仍为`**（**不含** id；owner 走独立 `who`） |
| mute `behalf` | **`pra代替`**（**不含** id；被代人走独立 `who`） |
| 延迟报告链 `act` | **`待写报告`**（executor/owner 走独立 `who`） |
| 延迟仍补救 `act` | **`待 PM 去补救`**（无 id；**项目 PM** 走独立 `who`） |
| 延迟 PM 核对 `act` | **`待 PM 核对`**（无 id；**项目 PM** 走独立 `who`） |
| 包络调窗 `act` | **`待 PM 去调整阶段窗口`**（无 id；**项目 PM** 走独立 `who`） |
| 步骤名 `owner_escalated` | **保持**「已升级负责人」 |

### 4.2 延迟 `act` ↔ 主 CTA（Normative）

末步 `act` 与主 CTA **同一谓词**（`remediate_report_ready` / 办事态）：

- 报告链 → act=`待写报告`（+ who）；主 CTA ∈ 报告链（非「去补救」）
- 仍需补救 → act=`待 PM 去补救` + who=项目 PM；主 CTA=「去补救」

**禁止**用美化 act 掩盖仍应「去补救」的态；亦禁止报告链仍写「待 PM 去补救」。

---

## 5. 写路径 payload 契约（本刀 · Normative）

| step | 新写入必填 |
| ---- | ---------- |
| `chased` | `n` + `user_ids`（= inform 对象：executor 或 owner） |
| `owner_escalated` 升成 | `from` + `to`（可带 `executor`） |
| `owner_escalated` 升不动 | `stopped: true` + `owner` |
| `reassigned` | `from` + `executor`（投影用 transition；本刀若触达则对齐） |
| `rejected` / `cancelled` | `reason` → 投影为 `why`（原样字符串即可） |

**禁止**生产刷改历史 `timeline_events`。

### 5.1 Legacy 投影回退（显式 · 可测）

| 旧 payload | 回退 |
| ---------- | ---- |
| `chased` 仅有 `n` | `who` ← Action `executor_user_id` 或 `owner_user_id`（收在 `legacy_*`，禁止散落） |
| `owner_escalated` 有 `stopped` 无 why 文案 | 投影拼 why=`升不动，仍为` + who=`owner` |

---

## 6. 覆盖边界（已确认）

| 覆盖 | 不覆盖（Follow-up） |
| ---- | ------------------- |
| 全 intent 共用的 **steps 呈现系统** | 标题 `_problem_for` 句库重构 |
| chase / escalate **新写入**可读 | CTA 文案表整表重构 |
| 卡头进度行与末步同文 | 非延迟 `awaiting_work` 全面补 `act` |
| **mute / 延迟 act / transition 分槽（§4.0）** | 站外 inform 正文 |
| | 改步骤中文名 / 新 step_key |
| | 刷历史 `timeline_events` |

---

## 7. 实现落点（已拍板）

| 项 | 决定 |
| -- | ---- |
| 模块 | `active_agent/app/services/sda_step_render.py`（slots · templates · render）；`sda.py` 调用 |
| 延迟 act | `_remediate_awaiting_role_phrase` **只返回常量**；人另填 `who` |
| mute | 投影：`behalf=pra代替` + `who`；**禁止** `f"pra代替{id}"` |
| FE | **不**复制模板；**不**为焊死串加正则抢救；只 `resolveSdaStepDetail` 翻独立 person token |
| 发版 | 本补丁以 **AA** 为主；FE 仅当 detail 形态破坏现有 split 时才发 |
| 文档 | 产品 §4.8.6 与本文对齐；分槽切片见 [分槽迭代](./PRA-SDA步骤呈现分槽迭代.md) |

---

## 8. 修订记录

| 日期 | 版本 | 变更 |
| ---- | ---- | ---- |
| 2026-08-21 | **v0.1.0** | 初稿：四层 · 槽位 · 模板 · chase/escalate 契约 · legacy · 边界 |
| 2026-08-21 | **v0.1.1** | 升不动：`why`=`升不动，仍为` + 独立 `who`（禁止把 id 嵌进 why 字符串） |
| 2026-08-22 | **v0.1.2** | **全局人槽不变量**；mute/延迟 act 分槽；act↔CTA；transition 两端 id；挂 [分槽迭代](./PRA-SDA步骤呈现分槽迭代.md) |
