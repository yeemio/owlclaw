# OwlHub CLI 命名审校与决策提案

> 时间：2026-02-25  
> 发起：codex-gpt-work 审校结论  
> 目标：统一 OwlHub 发布闸门能力的 CLI 命名，避免后续命令面失控

---

## 1. 背景

当前 OwlHub 已具备发布闸门能力：

- 代码入口：`owlclaw.owlhub.release_gate.run_release_gate`
- 脚本入口：`scripts/owlhub_release_gate.py`

但 CLI 仍无正式命令，存在两种路径：

1. 立即挂到 `owlclaw skill ...`
2. 先做架构命名决策，再统一落地

本提案选择第 2 路径。

---

## 2. 审校结论（推荐）

**推荐：新增顶层命名空间 `owlclaw release ...`，不要继续膨胀 `owlclaw skill ...`。**

推荐命令形态：

```bash
owlclaw release gate owlhub \
  --api-base-url <url> \
  --index-url <url> \
  --output <file>
```

### 理由

- `skill` 子命令语义应聚焦“技能资产操作”（search/install/publish/validate），不应混入“发布治理流程”。
- 发布闸门本质是跨模块发布控制能力，未来可能扩展到 `mcp`、`db`、`agent`，顶层 `release` 更可扩展。
- 当前已有 `db`、`skill`、`memory` 的域划分，新增 `release` 与现有架构边界一致。

---

## 3. 备选方案与取舍

### A. 放入 `owlclaw skill gate`

- 优点：实现快、改动小
- 缺点：`skill` 语义被污染；未来跨模块 gate 命名会失衡

### B. 放入 `owlclaw skill verify`

- 优点：命令短
- 缺点：与 `skill validate` 概念冲突（一个是文件规范校验，一个是发布环境闸门）

### C. 顶层 `owlclaw release gate`（推荐）

- 优点：语义清晰、可扩展、避免后续重命名成本
- 缺点：需要一次架构命名确认

---

## 4. 决策请求（给架构层）

请确认以下命名规范：

1. 是否引入顶层域 `release`
2. 发布闸门是否统一命名为 `release gate`
3. 资源对象是否采用 `release gate <target>`（如 `owlhub`、后续 `mcp`）

---

## 5. 落地计划（决策后）

1. CLI 实现：`owlclaw release gate owlhub`
2. 文档更新：
   - `docs/owlhub/cli_reference.md`
   - `docs/cli/skill-commands.md`（仅保留引用，不承载 gate 命令）
3. 测试补齐：
   - CLI dispatch 单测
   - gate 命令参数与退出码测试

---

## 6. 当前状态

- 发布闸门能力可用（代码+脚本+测试已具备）
- CLI 命名等待架构决策，不在本轮直接并入 `owlclaw skill`
