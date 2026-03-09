# OwlClaw 深度审计报告 — 2026-03-07（独立轮）

> **审计范围**: API Trigger 请求路径 + Runtime 工具执行与观察路径（I/O 边界 + 核心逻辑）
> **方法**: 深度审计 SKILL — 文件清单、三遍读法、五透镜（Correctness / Failure / Adversary / Drift / Omission）
> **代码规模**: server.py 378 行、handler.py 54 行、runtime.py 2195 行（本次重点约 400 行）

---

## Executive Summary

**Total Findings (本轮独立审计)**: 4  
- P0: 0  
- P1: 0  
- Low: 4  

**Overall Assessment**: **SHIP WITH CONDITIONS** — 无 P0/P1，均为 Low；与既有 DEEP_AUDIT_REPORT 部分重合，本轮为独立读码验证。

**本轮主要结论**:
1. 最终汇总失败时仍将 `str(exc)` 写入 assistant content（与既有报告 #47 一致，未修复）。
2. `_finish_observation` 在第一次异常后即 return，不再尝试 `update`，可能使部分观测后端未正确收尾。
3. API Trigger 将完整 `request.url`（含 query）写入 ledger，存在敏感信息入审计轨迹风险。
4. `_get_run_result` 的 `run_id` 来自 path，无长度/字符校验，存在日志膨胀或边缘 DoS 风险。

---

## 文件清单（本轮实际读过）

| 文件 | 行数 | 阅读方式 |
|------|------|----------|
| owlclaw/triggers/api/handler.py | 54 | 全量三遍 |
| owlclaw/triggers/api/server.py | 378 | 全量三遍（重点 endpoint、_handle_sync、_handle_async、_record_execution、_get_run_result） |
| owlclaw/agent/runtime/runtime.py | 2195 | 选读：_finish_observation、_sanitize_tool_result、_execute_tool（builtin 分支）、max iterations 异常分支 |

---

## Findings（本轮独立发现）

### Low — 改进项

| # | Category | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 1 | C.Robustness / B.Security | 达到 max iterations 且最终 summarization 抛异常时，将 `str(exc)` 写入 assistant message content，可能把内部异常信息泄露到对话或下一轮 LLM。 | `owlclaw/agent/runtime/runtime.py:915-919` | 使用固定文案，例如 `"Final summarization failed due to an internal error."`，不拼接 `exc`；完整异常仅打日志。 |
| 2 | C.Robustness | `_finish_observation` 在 `method(**kwargs)` 或 `method()` 抛异常后直接 `return`，不再尝试下一个 `method_name`（`"update"`）。若观测后端仅实现 `update` 而未实现 `end`，或 `end` 签名不符导致抛错，则观测可能从未被正确结束。 | `owlclaw/agent/runtime/runtime.py:334-351` | 在每次 `method_name` 的 `except Exception` 中不 `return`，改为 `continue`，尝试下一个 method；仅当所有 method 均不可用或均失败后再退出。 |
| 3 | E.Observability / B.Security | `_record_execution` 的 `input_params` 包含 `payload`，其中 `payload["url"] = str(request.url)`。完整 URL 可能含 query 中的 token 或敏感参数，会原样写入 ledger，造成敏感信息进入审计存储。 | `owlclaw/triggers/api/server.py:217-224` | 写入 ledger 前对 `url` 做脱敏（例如只保留 path，或 strip query），或从 payload 中移除 `url` 仅保留 path；若需 URL 用于排查，可仅记录 path。 |
| 4 | C.Robustness | `_get_run_result` 中 `run_id = str(request.path_params.get("run_id", "")).strip()` 未做长度或字符集限制，极端 path 可能造成大字符串入内存/日志。 | `owlclaw/triggers/api/server.py:391` | 对 `run_id` 做长度上限（例如 128）及字符集校验（例如仅允许 [a-zA-Z0-9_-]）；超限或非法则 400。 |

---

## 数据流核查（本轮追踪）

| # | 流 | Source | Validation | Sink | Verdict |
|---|-----|--------|------------|------|---------|
| 1 | API 请求体 → runtime payload | Request body | `parse_request_payload_with_limit` 按字节上限读取；`BodyTooLargeError` / `InvalidJSONPayloadError` 处理 | payload["body"] | ✅ 有上限与错误处理 |
| 2 | payload → ledger | server 构造 payload | 无 URL/query 脱敏 | ledger.record_execution(input_params=payload) | ⚠️ Finding #3 |
| 3 | 工具异常 → LLM 内容 | Built-in tool except | `return {"error": str(exc)}` | tool role message | ⚠️ 与既有报告 #124 一致 |
| 4 | 最终 summarization 异常 → assistant content | Exception in max-iter path | 无 | messages.append content=f"... {exc}" | ❌ Finding #1 |

---

## 与既有报告交叉对照

| 本报告 # | 对应 DEEP_AUDIT_REPORT | 说明 |
|----------|------------------------|------|
| 1 | #47 | 同一问题：最终 summarization 失败时 content 含 str(exc)。 |
| 2 | — | 新增：_finish_observation 提前 return 导致未尝试 update。 |
| 3 | #48（observation 敏感参数）部分相关 | 不同点：此处为 URL 入 ledger，非 observation。 |
| 4 | — | 新增：run_id path 参数无校验。 |

---

## 建议修复顺序

1. **Finding #1** — 替换最终 summarization 异常分支中的 `{exc}` 为固定文案并打日志（高优先级，防信息泄露）。
2. **Finding #2** — 调整 _finish_observation 异常处理为 continue 尝试下一 method（稳健性）。
3. **Finding #3** — ledger 写入前对 payload 的 url 脱敏或只存 path。
4. **Finding #4** — 对 run_id path 参数做长度与字符集校验。

---

## Audit Completeness Checklist（本轮）

- [x] 选定范围内文件按三遍读法读过
- [x] 关键数据流（body→payload→ledger；异常→content）已追踪
- [x] 错误路径（BodyTooLarge、InvalidJSON、tool exception、max-iter exception）已检查
- [x] 每个发现均有具体位置与修复建议
- [ ] 与既有 124 条发现去重与合并（建议由维护者在 DEEP_AUDIT_REPORT 中合并）
