# Requirements: Cross-language Golden Path

> **目标**：提供非 Python（优先 Java）接入 OwlClaw API/MCP 的标准落地路径。  
> **优先级**：P1  
> **预估工作量**：3-5 天

## 1. 功能需求

### FR-1 Java 最小接入
- [ ] 触发 Agent
- [ ] 查询状态/结果
- [ ] 处理标准错误与重试

### FR-2 curl 对照路径
- [ ] 与 Java 样例保持同一场景同一语义

### FR-3 文档化与可执行化
- [ ] 接入步骤、鉴权、超时、幂等、重试策略
- [ ] 本地可执行验证脚本

## 2. DoD

- [ ] Java + curl 两条路径均可完成 3 个核心场景
- [ ] 验收脚本可复现
- [ ] 文档进入 Quick Start/Protocol 目录索引

---

**维护者**：开发者体验组  
**最后更新**：2026-02-26

