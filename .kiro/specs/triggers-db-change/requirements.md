# Requirements: 数据库变更触发器

## 文档联动

- requirements: `.kiro/specs/triggers-db-change/requirements.md`
- design: `.kiro/specs/triggers-db-change/design.md`
- tasks: `.kiro/specs/triggers-db-change/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：通过 PostgreSQL NOTIFY/LISTEN 和 CDC 机制，让数据库变更事件自动触发 Agent Run  
> **优先级**：P2  
> **预估工作量**：5-7 天

---

## 1. 背景与动机

### 1.1 当前问题

架构文档 §5.3.1 定义了六类触发入口，其中「数据库变更」是业务应用最常见的事件源之一。持仓变化、订单状态更新、库存变动等都是数据库变更事件，传统做法是触发器 + 固定逻辑，无法智能决策。

### 1.2 设计目标

- 支持 PostgreSQL NOTIFY/LISTEN 原生通道
- 支持 CDC（Change Data Capture）模式（预留接口）
- 事件触发后由 Agent 自主决策，而非执行固定 handler
- 与治理层集成，防止高频变更导致 Agent 成本失控

---

## 2. 用户故事

### 2.1 作为业务开发者

**故事 1**：监听数据库变更
```
作为业务开发者
我希望通过 @app.db_change 装饰器监听指定的 PostgreSQL 通道
这样我可以让 Agent 自动响应数据库状态变化
```

**验收标准**：
- [ ] `@app.db_change(channel="position_changes")` 注册数据库变更触发器
- [ ] 接收到 NOTIFY 时自动触发 Agent Run
- [ ] payload 作为触发上下文传递给 Agent

**故事 2**：变更聚合
```
作为业务开发者
我希望系统能聚合高频变更事件
这样我可以避免每次微小变更都触发 Agent Run 导致成本浪费
```

**验收标准**：
- [ ] 支持 `debounce_seconds` 参数（在窗口期内聚合多次变更）
- [ ] 支持 `batch_size` 参数（累积 N 条变更后统一触发）

---

## 3. 功能需求

#### FR-1：PostgreSQL NOTIFY/LISTEN 监听

**需求**：使用 asyncpg 或 psycopg 的 LISTEN 能力，监听指定 PostgreSQL 通道。

**验收标准**：
- [ ] 支持多通道同时监听
- [ ] 连接断开时自动重连
- [ ] payload 解析为结构化数据

#### FR-2：事件聚合

**需求**：支持对高频数据库变更事件进行聚合，减少不必要的 Agent Run。

**验收标准**：
- [ ] debounce：窗口期内只触发一次（取最后一条）
- [ ] batch：累积到 batch_size 条后统一触发

#### FR-3：Agent 触发与治理

**需求**：变更事件经过治理检查后触发 Agent Run。

**验收标准**：
- [ ] 与现有治理层（冷却/限流/成本）集成
- [ ] 执行记录写入 Ledger

#### FR-4：CDC 预留接口

**需求**：定义 CDC 适配器接口，为未来接入 Debezium 等 CDC 工具预留扩展点。

**验收标准**：
- [ ] 定义 `DBChangeAdapter` 抽象基类
- [ ] PostgreSQL NOTIFY 实现为第一个适配器
- [ ] 接口支持未来扩展 MySQL binlog、Debezium 等

---

## 4. 非功能需求

**NFR-1**：NOTIFY 监听延迟 < 1s  
**NFR-2**：连接断开后 30s 内自动重连  
**NFR-3**：高频变更（100+/s）场景下聚合器正常工作

---

## 5. 依赖

- `owlclaw.agent.runtime`：Agent Run 触发
- `owlclaw.governance`：治理约束和 Ledger
- `owlclaw.db`：数据库连接复用
- asyncpg 或 psycopg：PostgreSQL 异步监听

---

## 6. 参考文档

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.3.1 六类触发入口
- [Triggers Cron Spec](../triggers-cron/)
- [PostgreSQL NOTIFY/LISTEN](https://www.postgresql.org/docs/current/sql-notify.html)

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
