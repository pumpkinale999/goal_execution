# PRA 一致性合约迭代

- **文档类型**：切片迭代（产品合约 + 实现/测试出口）
- **状态**：**M1–M5 已齐**（2026-08-20）；**INV-3 修订 · PRA-WS1 现网**（2026-08-21）
- **上位**：[PRA产品设计.md](./PRA产品设计.md) · [PRA-实现与测试.md](./PRA-实现与测试.md)
- **办事态修订**：[PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) · [PRA-项目办事态机迭代.md](./PRA-项目办事态机迭代.md)
- **代码**：`active_agent/app/services/reconcile.py`

## 0. 一句话

GE 真源变了，AA 开放票必须收敛。用可判定 INV + 幂等 `reconcile_project`（写前 / 读时 / 审计）消除「图绿票红」、软删僵尸票、空 gaps 僵死定义票；**延迟票**另以 **项目办事态** 判定，禁止半截偏差误杀。

## 1. 拍板（已定）

| 项 | 决定 |
|----|------|
| 改期后延迟票 | 已离开延迟办事态 → **自动 cancel**（废止「改期不关票」；**≠** 仅看日历 overdue） |
| gaps=`[]` | 开放 `fix_definition` → **自动 cancel** |
| 终态 | completed / cancelled / archived / 软删（图不可达）→ **零开放票** |
| 读路径 | 同步 reconcile；失败不挡读 |
| 可见性 | 静默修 + timeline `actor=system` |
| 半截偏差 | open/active 无 rem-task ∈ **DELAY_NEEDS_REMEDIATE** → **保留** `remediate_*`（PRA-WS1） |
| 非目标 | **不**放宽 `missing_deadline` / 本切片不改 GE `is_overdue` |

## 2. Invariants

| ID | 规则 |
|----|------|
| **INV-1** | 终态或项目不可达 → 无开放 Action |
| **INV-2** | `definition-gaps=[]` → 无开放 `fix_definition` |
| **INV-3** | **分轨**：（1）`remediate_stage`：仅当项目已离开 `{DELAY_NEEDS_REMEDIATE, DELAY_NEEDS_REPORT}`（或该 stage 已无「逾期∪半截」热项）才可清；（2）`remediate_envelope`：**仍只认包络窗口不逾期** → 清，**不**因门控半截保留。**废止**「仅无 live overdue 即清全部 remediate」。真源：[PRA-项目办事态机共识.md](./PRA-项目办事态机共识.md) §3.3 |
| **INV-4** | 开放 `fix_definition` ⇒ 无开放 deliver / remediate / review / notify |

> **历史口径（M4）**：曾写「无 live overdue → 清 remediate」。该口径与产品 §3.3.1 冲突，导致半截偏差空窗；**以本表 INV-3 为准**，代码以 PRA-WS1 落地为准。

## 3. 里程碑出口

### M1 · 内核 ✅

- [x] `reconcile_project` + CLI `scripts/reconcile_project.py`
- [x] INV 金样 `tests/test_reconcile_project.py`
- [x] 本文档骨架；产品设计指针

### M2 · 终态 / 软删 ✅

- [x] GE `soft_delete` → `notify_graph_write(project_soft_delete)`（`ge-observation-mount.md`）
- [x] AA observation INV-1；`scan_project` 前 reconcile；终态/不可达清票
- [x] 测：`tests/ge/test_observation_mount.py::test_soft_delete_*` · `tests/test_pra_consistency_hooks.py`

### M3 · 空 gaps ✅

- [x] scan 前强制 reconcile（INV-2）
- [x] `collapse_notify_phase_tickets.py` 调 `reconcile_project`
- [x] 空 gaps 不要求人点核销才清票（系统 cancel）

### M4 · 改期收敛 ✅

- [x] INV-3（初版：无 live overdue → cancel）；废产品/实现「改期不关票」；changelog **v0.2.82**
- [x] `test_overdue_cleared.py` 期望 cancel；产品注册支持时序测
- [x] 包络窗口清 → list_events 后票 cancelled（非 verify CTA）
- [x] **PRA-WS1**：INV-3 升格办事态谓词；半截偏差不杀（见 [迭代](./PRA-项目办事态机迭代.md)）

### M5 · 读路径 + 审计 ✅

- [x] `list_events` 触发 reconcile（fixture 未知 id 不误杀；GE 失败仍 200）
- [x] `scripts/pra_invariant_audit.py`
- [x] DoD / 冒烟见下

## 4. DoD / 冒烟清单

| 项 | 期望 |
|----|------|
| INV 金样 | `tests/test_reconcile_project.py` 绿（含 WS-T02/T03） |
| 写路径 | soft_delete / 改期 / 空 gaps → 开放票收敛；半截偏差 **保留** remediate |
| 读路径 | 打开曾脏项目 Panel → 票与 Canvas 一致（第二次 list 无额外 cancel） |
| 审计 | 生产 `pra_invariant_audit.py` dry-run 违规可解释；止血可 `--apply` |
| 非目标 | fix_definition **数量下降**不属于本切片 |

## 5. 非目标

- 降低全库 `fix_definition` 数量（定义门禁政策另开）
- 新外部告警系统
- 本切片改 GE `is_overdue` / 禁「只 open」
