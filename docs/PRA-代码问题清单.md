# PRA 代码问题清单

文档对齐与收口过程中的代码/契约偏差跟踪。严重度：P0 阻断闭环 · P1 作用域/语义偏 · P2 体验/表达。

| ID | 严重度 | 现象 | 代码位置 | 文档期望 | 状态 |
| -- | ------ | ---- | -------- | -------- | ---- |
| CODE-001 | P1 | `review_gate` 驳回时 `cancel_forward_tickets` 未传 `gate_id` | [`action.py`](../active_agent/app/services/action.py) `review_verify` | 驳回按该门控 cancel；`review_project` 整项目 | **已修（v0.2.51）**：传 `gate_id=`；测 `test_review_reject_cancels_only_same_gate` |
| CODE-002 | P2 | waiting 无 Panel 卡 vs DoD「卡上可表达等文档」 | `sense` suppressed waiting | 明确载体或改预期 | **已关（文档裁定 · v0.2.51）**：v1 不投影；A4/§5.5 后置 |
| CODE-003 | P1 | GI 提交成功后弹窗翻成签收 / 再弹且按钮点不动 | `ProjectCanvasPage` 深链 effect + `runWorkflowAction` | submit/sign 成功关窗 + success 条；不因滞留 `?gate-item=` 回弹 | **已修（GE v1.39.78）**：dismiss 抑制 + 先 close 再 refresh；测 GE-T62b |
| CODE-004 | P1 | 写挂载 401 + FE 同步 sense/decide 卡顿；评审双扫 | GE observation 订阅 token；FE `syncPraAfterGraphWrite`；Sense 串行 GE 读 | 写推送异步；关键路径不硬等；单次 Sense | **已修（v0.2.53）**：M1 token 拒空；M2 评审去 FE syncPra / 提交签收非阻塞；M3 write 本地 gaps + cron 并行 GE 读；M4 `decided` 消费态；评价见 PRA-实现 |

> CODE-001～004 已关。升 GA、`deliver_artifact`、Mute 代行等属产品 **§5.5 后置**，不记缺陷。
