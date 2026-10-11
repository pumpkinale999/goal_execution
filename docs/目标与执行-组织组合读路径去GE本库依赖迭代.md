# 目标与执行 · 组织组合读路径去 GE 本库依赖（ORG-DEPT-GE-VAL-F1 / F2）

- **文档类型**：产品共识 + 实现/测试规格（本迭代真源）
- **版本**：**v1.0.1**（2026-08-29）
- **里程碑**：**ORG-DEPT-GE-VAL-F1** → **ORG-DEPT-GE-VAL-F2**
- **状态**：**Accepted · 现网（`v29.01.03`）**（MS1–MS7 全勾；生产闸见评价 v1.0.0；维护债见 MAINT）
- **适用对象**：产品、skstudio / goal_execution 研发、QA、运维
- **代码范围**：`goal_execution` · `skstudio` · `platform-docs`
- **上位写路径**：[目标与执行-主责部门去GE本库校验迭代.md](./目标与执行-主责部门去GE本库校验迭代.md)（现网 `v29.01.02`）

**上位 / 关联**

| 文档 | 关系 |
| ---- | ---- |
| [平台控制面与Postgres迁移共识.md](../../platform_docs/平台控制面与Postgres迁移共识.md) | D2 / M3 |
| [目标与执行-主责部门去GE本库校验迭代.md](./目标与执行-主责部门去GE本库校验迭代.md) | 写路径现网；本刀 = 其 F1/F2 |
| [目标与执行-组织组合读路径去GE本库依赖评价.md](./目标与执行-组织组合读路径去GE本库依赖评价.md) | 四闸评价 |

> **一句话（现网）**：部门/团队目标组合与 migrate 由 BFF 注入 `member_user_ids`；GE 零读 org_*；生产已 DROP 四表（033）。

---

## 0. 共识冻结清单

（C1–C15 同 v0.1.1，不重复；现网已落实。）

---

## 4. 实现切片与 DoD

| 切片 | 状态 |
| ---- | ---- |
| **MS0** 文档 | ✅ |
| **MS1** GE portfolio/migrate + GE-T250～254 | ✅ |
| **MS2** BFF C14 注入 + SK-T250～252 | ✅ |
| **MS3** C9 测重写 · 死代码 · `routes_org` 删除 | ✅ |
| **MS4** F1 发版 `v29.01.03` + 冒烟 | ✅ |
| **MS5** Alembic `033_drop_ge_org_tables` | ✅ |
| **MS6** F2 生产 upgrade DROP（纠偏 stamp→真 upgrade） | ✅ |
| **MS7** 文档 Accepted · 现网 | ✅ |

### 4.1 生产签收（2026-08-29）

| 项 | 值 |
| -- | -- |
| Tag | `v29.01.03` |
| F1 冒烟 | GE `GET …/portfolios/departments/{人力资源}` → **200** · primary 含既有子目标 |
| migrate | 同部门 → **400** `same_department` |
| F2 | `alembic` head=`033_drop_ge_org_tables`；`org_*` / `user_org_*` 表 **0** |
| 禁镜像 | 未灌 org |
| 注 | 首次 publish 曾 stamp 到 033 未 DROP；已 stamp 回 032 再 `upgrade` 真 DROP |

**DoD**：F1/F2 全勾。

### 4.2 Follow-up（维护债 · 另刀）

写/读主线已现网；下列 **不**回退本刀 Accepted，见 [GE 组织遗留维护迭代](./目标与执行-GE组织遗留维护迭代.md) **v0.1.0**：

| 项 | 里程碑切片 |
| -- | ---------- |
| 偏差上报链 → callback 展开 | MS1 REPORT-CHAIN |
| GE 死 org 代码清仓 + CI ban | MS2 PURGE |
| `ensure_dev_schema` 禁假 stamp | MS3 STAMP |
| Portfolio UI tab 接线 | MS4 UI-PORTFOLIO |

---

## 8. 修订记录

| 日期 | 版本 | 说明 |
| ---- | ---- | ---- |
| 2026-08-29 | **v1.0.1** | 挂链 Follow-up → ORG-DEPT-GE-MAINT（上报链/清仓/stamp/UI） |
| 2026-08-29 | **v1.0.0** | Accepted · 现网：MS1–MS7 · `v29.01.03` · 033 DROP |
| 2026-08-29 | **v0.1.1** | 实现锁定 C4/C14/C15 |
| 2026-08-29 | **v0.1.0** | 初版 |
