# Tasks: Contract Testing

> **状态**：已完成  
> **预估工作量**：4-6 天  
> **最后更新**：2026-02-26

## 进度概览

- **总任务数**：19
- **已完成**：19
- **进行中**：0
- **未开始**：0

## 1. 目录与基线

- [x] 1.1 建立 `tests/contracts/api`
- [x] 1.2 建立 `tests/contracts/mcp`
- [x] 1.3 建立 `scripts/contract_diff`

## 2. API 契约检测

- [x] 2.1 接入 OpenAPI diff
- [x] 2.2 定义 breaking 规则映射
- [x] 2.3 CI 接入 PR 阶段门禁

## 3. MCP 契约回归

- [x] 3.1 initialize 回归用例
- [x] 3.2 tools/list/call 回归用例
- [x] 3.3 resources/list/read 回归用例
- [x] 3.4 错误语义回归用例

## 4. 对齐矩阵

- [x] 4.1 新建 `API_MCP_ALIGNMENT_MATRIX.md`
- [x] 4.2 填充能力与错误域映射
- [x] 4.3 将矩阵变更纳入评审要求

## 5. 报告与演练

- [x] 5.1 生成标准差异报告模板
- [x] 5.2 执行一次 breaking 注入演练
- [x] 5.3 更新 `SPEC_TASKS_SCAN` checkpoint

## 6. 阈值与剧本固化

- [x] 6.1 固化运行时阈值（PR/nightly）并纳入文档
- [x] 6.2 新增验收矩阵并绑定 artifact 位置
- [x] 6.3 完成 T+0~T+15 处置剧本演练

---

**维护者**：测试架构组  
**最后更新**：2026-02-26
