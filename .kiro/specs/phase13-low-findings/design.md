# phase13-low-findings — 设计文档

> **目标**: 将 v4 审计 #11~#14 变为可实施、可回归、可审校的收口批次  
> **状态**: 设计完成  
> **最后更新**: 2026-03-05

---

## 1. 架构设计

### 1.1 整体架构

```text
┌───────────────────────────────┐
│ phase13-low-findings          │
│ (#11 #12 #13 #14)             │
└───────────────┬───────────────┘
                │
     ┌──────────┼──────────┬──────────┐
     ▼          ▼          ▼          ▼
Langfuse   SQL Guard   Shadow Mode  Heartbeat
Masking    Hardening   Redaction    I/O Tune
```

### 1.2 核心组件

#### 组件 1：Langfuse Secret Masking（#11）
- **职责**: 避免 secret 在配置导出、日志或 API 响应中明文出现。
- **接口**: 复用现有配置序列化与输出链路，新增统一掩码逻辑。

#### 组件 2：SQL Read-Only Guard（#12）
- **职责**: 强化 `_is_select_query` 判定，减少启发式误判。
- **接口**: 在 `bindings` SQL 执行入口统一校验。

#### 组件 3：Shadow Data Redaction（#13）
- **职责**: shadow mode 仅保留最小必要信息，避免查询泄露。
- **接口**: shadow 结果写入/回传链路增加脱敏层。

#### 组件 4：Heartbeat I/O Control（#14）
- **职责**: 控制 heartbeat DB 查询频率，降低不必要 I/O。
- **接口**: 在 heartbeat 读取路径加入轻量节流参数。

---

## 2. 实现细节

### 2.1 文件结构

```text
owlclaw/
├── integrations/langfuse.py                 # #11
├── capabilities/bindings/sql_executor.py    # #12, #13
├── agent/runtime/heartbeat.py               # #14
└── config/ (如需统一敏感字段掩码入口)
```

### 2.2 关键实现点

#### D-L1：Langfuse secret 掩码（#11）
- `LangfuseConfig` 增加安全导出 `to_safe_dict()`，对 `public_key/secret_key` 统一输出 `***`。
- `LangfuseConfig` 的 `public_key/secret_key` 字段使用 `repr=False`，避免对象打印泄露。
- 错误日志链路继续复用 `_safe_error_message()`，禁止原始 key 出现在 warning/error 文本。

#### D-L2：SQL 只读判定加固（#12）
- 规范化 SQL 文本（去块注释/行注释、空白折叠）后再判定。
- 对多语句场景（`;`）默认拒绝（fail-close）。
- 仅允许 `SELECT/WITH` 起始，命中写操作关键字时默认拒绝。

#### D-L3：shadow mode 可见性收敛（#13）
- shadow 结果仅保留摘要字段（执行状态、耗时、结构信息）。
- 数据内容字段默认不进入主决策上下文。

#### D-L4：heartbeat 查询节流（#14）
- 增加最小查询间隔（可配置）。
- 在间隔窗口内复用最近结果或跳过 DB 查询。

---

## 3. 数据流

### 3.1 Low finding 修复流程

```text
Spec Task -> Code Change -> Targeted Tests -> Review Loop -> Merge
```

### 3.2 运行时流程（Heartbeat）

```text
tick -> check interval -> (skip or query db) -> update cache/state
```

---

## 4. 错误处理

### 4.1 掩码/脱敏失败
- 失败时默认返回保守值（隐藏字段），避免回退到明文输出。

### 4.2 SQL 判定不确定
- 判定不确定时按非只读处理（fail-close）。

### 4.3 Heartbeat 缓存异常
- 缓存读取失败时降级到一次 DB 查询并记录告警日志。

---

## 5. 配置

### 5.1 配置项建议

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OWLCLAW_HEARTBEAT_MIN_DB_INTERVAL_MS` | Heartbeat 最小 DB 查询间隔 | `500` |

---

## 6. 测试策略

### 6.1 单元测试
- #11: secret 掩码断言（配置/日志路径）`tests/unit/integrations/test_langfuse.py`。
- #12: SQL 判定样例集（合法只读、绕过样例、混淆大小写）`tests/unit/capabilities/test_bindings_sql_executor.py`。
- #14: Heartbeat 节流行为测试（连续 tick 不重复查 DB）。

### 6.2 集成测试
- #13: shadow mode 端到端验证不泄露敏感查询数据。

---

## 7. 迁移计划

### 7.1 Phase A：文档与任务建立（0.5 天）
- 完成三层 spec + 扫描表对齐。

### 7.2 Phase B：分模块实现（1-2 天）
- 先 #11/#12，再 #13/#14，减少交叉冲突。

### 7.3 Phase C：回归与审校（0.5 天）
- 定向测试 + 审校结论 + 合并。

---

## 8. 风险与缓解

### 8.1 风险：SQL 规则收紧引发兼容性问题
- **缓解**: 将高风险规则放入测试样例并提供清晰错误信息。

### 8.2 风险：heartbeat 节流导致延迟波动
- **缓解**: 配置可调并补充阈值测试。

---

## 9. 契约与 Mock

### 9.1 API 契约
- 本 spec 不新增外部 API 契约，属于内部行为加固。

### 9.2 Mock 策略
- heartbeat 使用假时钟或时间注入方式做节流测试。
- shadow mode 使用测试数据集验证字段可见性。

---

## 10. 参考文档

- `.kiro/specs/phase13-low-findings/requirements.md`
- `.kiro/specs/SPEC_TASKS_SCAN.md`

---

**维护者**: multi-worktree orchestrator  
**最后更新**: 2026-03-05
