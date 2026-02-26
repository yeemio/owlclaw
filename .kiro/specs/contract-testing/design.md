# Design: Contract Testing

> **目标**：把“协议正确性”变成持续自动化保障。  
> **状态**：设计中  
> **最后更新**：2026-02-26

## 1. 架构

```text
Contracts -> Diff Analyzer -> Policy -> CI Gate
          -> Replay Tests  -> Report -> Artifact
```

## 2. 实现

- `tests/contracts/api/*`
- `tests/contracts/mcp/*`
- `scripts/contract_diff/*`
- `docs/protocol/API_MCP_ALIGNMENT_MATRIX.md`

## 3. 集成点

- PR: 运行 diff + 回归
- main: 运行完整回归并发布报告

## 4. 风险与缓解

- 风险：回归慢 -> 分层执行（PR 最小、nightly 全量）
- 风险：误报多 -> 规则白名单 + 人工复核入口

## 5. 红军视角

- 通过“隐藏 breaking change”绕过检测。  
  对策：双重检测（schema diff + 行为回放）。

---

**维护者**：测试架构组  
**最后更新**：2026-02-26

