# Design: AST 扫描器

> **目标**：提供 CLI AST 扫描能力，用于分析项目代码结构与能力点  
> **状态**：设计中  
> **最后更新**：2026-02-22

---

## 1. 架构设计

### 1.1 整体架构

`
┌───────────────┐    ┌────────────────────┐
│ Capability    │───▶│ AST 扫描器 模块     │
└───────────────┘    └─────────┬──────────┘
                               ▼
                      ┌───────────────────┐
                      │ 外部依赖/适配层   │
                      └───────────────────┘
`

### 1.2 核心组件

#### 组件 1：能力适配层

**职责**：对接外部依赖并转换为 OwlClaw 能力接口。

**接口定义**：
`	ypescript
export interface Adapter {
  register(): Promise<void>;
  execute(input: unknown): Promise<unknown>;
}
`

---

## 2. 实现细节

### 2.1 文件结构

`
cli-scan/
├── __init__.py
└── adapter.py
`

### 2.2 适配层实现

**当前问题**：缺少统一的适配层导致接入分散。

**解决方案**：提供标准 Adapter 接口并集中注册。

**实现**：
`	ypescript
export class DefaultAdapter implements Adapter {
  async register(): Promise<void> {}
  async execute(input: unknown): Promise<unknown> { return input; }
}
`

**关键点**：
- 统一能力注册入口
- 明确输入输出契约

---

## 3. 数据流

### 3.1 触发到执行流程

`
Trigger/Event
   │
   ▼
Adapter.register
   │
   ▼
Adapter.execute
`

**关键点**：
- 触发器负责启动
- 适配层负责编排

---

## 4. 错误处理

### 4.1 适配失败

**场景**：外部依赖不可用或响应异常。

**处理**：
`	ypescript
try { /* ... */ } catch (err) { throw err; }
`

---

## 5. 配置

### 5.1 配置文件

`yaml
cli-scan:
  enabled: true
`

### 5.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| OWLCLAW__ENABLED | 是否启用 | 	rue |

---

## 6. 测试策略

### 6.1 单元测试

`	ypescript
// validate adapter behavior
`

### 6.2 集成测试

`	ypescript
// validate end-to-end path
`

---

## 7. 迁移计划

### 7.1 Phase 1：基础能力（2 天）

- [ ] 适配层与接口定义
- [ ] 最小可运行链路

---

## 8. 风险与缓解

### 8.1 风险：外部依赖变更

**影响**：适配失效或行为不一致。

**缓解**：
- 引入契约与 Mock
- 在 CI 中验证关键路径

---

## 9. 契约与 Mock（依赖外部服务/Platform 时必写）

### 9.1 API 契约
- 记录外部依赖的接口与响应结构
- 明确错误码与语义

### 9.2 Mock 策略
- 本地/CI 提供 mock 开关
- 无外部依赖时可完成最小验收

---

## 10. 参考文档

- docs/ARCHITECTURE_ANALYSIS.md

---

**维护者**：平台研发  
**最后更新**：2026-02-22
