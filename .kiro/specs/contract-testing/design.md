# Design: Contract Testing

> **目标**：将协议回归从“人工检查”升级为“自动化可信门禁”。  
> **状态**：设计中  
> **最后更新**：2026-02-26

## 1. 架构

```text
Contract Sources -> Diff Engine -> Classifier -> CI Gate
                 -> Replay Runner -> Reports -> Artifacts
```

## 2. 实现细节

- `tests/contracts/api/`
- `tests/contracts/mcp/`
- `scripts/contract_diff/`
- `docs/protocol/API_MCP_ALIGNMENT_MATRIX.md`

### 集成点

- PR 阶段：最小契约集 + diff 分级
- main/nightly：全量契约回归 + 报告归档

## 3. 错误处理

- diff 工具失败：默认阻断合并
- 回归超时：保留失败工件并阻断

## 4. 测试策略

- 单元：分类器和规则解析
- 集成：真实契约 diff + gate 决策
- 回归：API/MCP 端到端契约场景

## 5. 红军视角

- 攻击：只改行为不改 schema 规避 diff。  
  防御：加入 replay 行为回归，不仅看 schema。

---

## 6. 故障处置剧本（T+0 ~ T+15）

- `T+0`：契约门禁失败并阻断合并。
- `T+3`：导出 diff + replay 失败样本。
- `T+6`：定位规则问题或真实 breaking 变更。
- `T+10`：修复并重跑最小契约集。
- `T+15`：恢复流水线并留档复盘。

---

**维护者**：测试架构组  
**最后更新**：2026-02-26
