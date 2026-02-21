# Requirements: Langfuse Integration

> **目标**：为 OwlClaw Agent 提供 LLM 调用追踪和可观测性能力  
> **优先级**：P1  
> **预估工作量**：2-3 天

---

## 1. 背景与动机

### 1.1 当前问题

在 Agent 自主决策的场景中，LLM 调用是核心环节，但缺乏可观测性：
- **无法追踪决策过程**：不知道 Agent 为什么做出某个决策
- **无法分析成本**：不知道每次 run 花费了多少 token 和成本
- **无法优化性能**：不知道哪些 prompt 效率低、哪些模型更适合
- **无法调试错误**：LLM 调用失败时难以定位问题
- **无法评估质量**：无法量化 Agent 决策的质量

### 1.2 设计目标

1. **完整追踪**：记录每次 Agent Run 的完整 LLM 调用链
2. **成本分析**：精确统计 token 使用量和成本
3. **性能监控**：监控 LLM 调用延迟和成功率
4. **质量评估**：支持人工标注和自动评分
5. **易于集成**：与 Agent Runtime 无缝集成，最小化侵入性

---

## 2. 用户故事

### 2.1 作为开发者

**故事 1**：追踪 Agent 决策过程
```
作为开发者
我希望查看 Agent 每次 run 的完整决策过程
这样我可以理解 Agent 为什么做出某个决策
```

**验收标准**：
- [ ] 可以在 Langfuse UI 中查看每次 Agent Run 的 trace
- [ ] Trace 包含所有 LLM 调用的 prompt 和 response
- [ ] Trace 包含所有工具调用的输入和输出
- [ ] Trace 显示决策的时间线和层级关系

**故事 2**：分析 LLM 成本
```
作为开发者
我希望查看每次 Agent Run 的 token 使用量和成本
这样我可以优化 prompt 降低成本
```

**验收标准**：
- [ ] 可以查看每次 LLM 调用的 token 使用量（prompt + completion）
- [ ] 可以查看每次 Agent Run 的总成本（USD）
- [ ] 可以按时间范围统计总成本
- [ ] 可以按 Agent、模型、任务类型分组统计成本

**故事 3**：监控 LLM 性能
```
作为开发者
我希望监控 LLM 调用的延迟和成功率
这样我可以发现性能瓶颈和稳定性问题
```

**验收标准**：
- [ ] 可以查看 LLM 调用的平均延迟（P50/P95/P99）
- [ ] 可以查看 LLM 调用的成功率
- [ ] 可以查看不同模型的性能对比
- [ ] 可以设置告警规则（延迟过高、成功率过低）

### 2.2 作为系统管理员

**故事 4**：评估 Agent 决策质量
```
作为系统管理员
我希望对 Agent 的决策进行人工标注和评分
这样我可以量化 Agent 的决策质量
```

**验收标准**：
- [ ] 可以在 Langfuse UI 中对 trace 进行标注（好/坏/需改进）
- [ ] 可以添加评论说明标注原因
- [ ] 可以查看标注统计（好评率、差评率）
- [ ] 可以导出标注数据用于模型微调

---

## 3. 功能需求

### 3.1 Trace 创建

#### FR-1：Agent Run Trace

**需求**：为每次 Agent Run 创建一个 Langfuse trace。

**Trace 结构**：
```
Trace: agent_run_{run_id}
├─ Span: identity_loading
├─ Span: memory_recall
├─ Span: skills_selection
├─ Span: llm_call_1
│  ├─ Metadata: model, prompt_tokens, completion_tokens, cost
│  └─ Input/Output: prompt, response
├─ Span: tool_call_1
│  ├─ Metadata: tool_name, duration
│  └─ Input/Output: arguments, result
├─ Span: llm_call_2
└─ Span: tool_call_2
```

**验收标准**：
- [ ] THE System SHALL 为每次 Agent Run 创建一个 Langfuse trace
- [ ] THE System SHALL 在 trace 中包含 Agent 身份信息（agent_id、run_id）
- [ ] THE System SHALL 在 trace 中包含触发信息（trigger_type、focus）
- [ ] THE System SHALL 在 trace 中包含时间戳（start_time、end_time）
- [ ] THE System SHALL 支持 trace 的嵌套结构（span 层级）

#### FR-2：LLM Call Span

**需求**：为每次 LLM 调用创建一个 span。

**Span 内容**：
- **Input**：完整的 prompt（system + user messages）
- **Output**：LLM 的 response（text 或 function call）
- **Metadata**：
  - model: 使用的模型（如 "gpt-4"）
  - prompt_tokens: prompt token 数量
  - completion_tokens: completion token 数量
  - total_tokens: 总 token 数量
  - cost_usd: 成本（USD）
  - latency_ms: 延迟（毫秒）
  - status: 状态（success/error）
  - error_message: 错误信息（如果失败）

**验收标准**：
- [ ] THE System SHALL 为每次 LLM 调用创建一个 span
- [ ] THE System SHALL 在 span 中包含完整的 prompt 和 response
- [ ] THE System SHALL 在 span 中包含 token 使用量和成本
- [ ] THE System SHALL 在 span 中包含延迟和状态
- [ ] WHEN LLM 调用失败时，THE System SHALL 记录错误信息

#### FR-3：Tool Call Span

**需求**：为每次工具调用创建一个 span。

**Span 内容**：
- **Input**：工具名称和参数
- **Output**：工具执行结果
- **Metadata**：
  - tool_name: 工具名称
  - duration_ms: 执行时长（毫秒）
  - status: 状态（success/error）
  - error_message: 错误信息（如果失败）

**验收标准**：
- [ ] THE System SHALL 为每次工具调用创建一个 span
- [ ] THE System SHALL 在 span 中包含工具名称和参数
- [ ] THE System SHALL 在 span 中包含执行结果
- [ ] THE System SHALL 在 span 中包含执行时长和状态
- [ ] WHEN 工具执行失败时，THE System SHALL 记录错误信息

### 3.2 与 Agent Runtime 集成

#### FR-4：自动追踪

**需求**：Agent Runtime 自动创建和管理 Langfuse trace，无需手动调用。

**集成方式**：
```python
# Agent Runtime 内部实现
class AgentRuntime:
    async def run(self, context: AgentRunContext):
        # 自动创建 trace
        trace = self.langfuse.trace(
            name=f"agent_run_{context.run_id}",
            metadata={
                "agent_id": context.agent_id,
                "trigger": context.trigger,
                "focus": context.focus,
            }
        )
        
        try:
            # 执行决策循环
            result = await self._decision_loop(context, trace)
            return result
        finally:
            # 自动结束 trace
            trace.end()
```

**验收标准**：
- [ ] THE System SHALL 在 Agent Run 开始时自动创建 trace
- [ ] THE System SHALL 在 Agent Run 结束时自动结束 trace
- [ ] THE System SHALL 在 LLM 调用时自动创建 span
- [ ] THE System SHALL 在工具调用时自动创建 span
- [ ] THE System SHALL 支持异步上报（不阻塞 Agent Run）

#### FR-5：Context 传递

**需求**：在 Agent Run 的整个生命周期中传递 trace context。

**实现方式**：
- 使用 contextvars 或参数传递 trace 对象
- 确保所有 LLM 调用和工具调用都能访问 trace

**验收标准**：
- [ ] THE System SHALL 在决策循环中传递 trace context
- [ ] THE System SHALL 在 LLM 客户端中访问 trace context
- [ ] THE System SHALL 在工具执行中访问 trace context
- [ ] THE System SHALL 支持嵌套的 span 创建

### 3.3 Token 和成本统计

#### FR-6：Token 使用量记录

**需求**：精确记录每次 LLM 调用的 token 使用量。

**Token 类型**：
- **Prompt tokens**：输入 token 数量
- **Completion tokens**：输出 token 数量
- **Total tokens**：总 token 数量

**验收标准**：
- [ ] THE System SHALL 从 LLM 响应中提取 token 使用量
- [ ] THE System SHALL 记录 prompt_tokens、completion_tokens、total_tokens
- [ ] THE System SHALL 支持不同模型的 token 计数方式
- [ ] THE System SHALL 在 Langfuse span 中记录 token 使用量

#### FR-7：成本计算

**需求**：根据 token 使用量和模型定价计算成本。

**定价表**：
```python
MODEL_PRICING = {
    "gpt-4": {
        "prompt": 0.03 / 1000,      # $0.03 per 1K prompt tokens
        "completion": 0.06 / 1000,  # $0.06 per 1K completion tokens
    },
    "gpt-3.5-turbo": {
        "prompt": 0.0015 / 1000,
        "completion": 0.002 / 1000,
    },
    "claude-3-opus": {
        "prompt": 0.015 / 1000,
        "completion": 0.075 / 1000,
    },
    # ... 更多模型
}
```

**验收标准**：
- [ ] THE System SHALL 维护模型定价表
- [ ] THE System SHALL 根据 token 使用量和定价计算成本
- [ ] THE System SHALL 在 Langfuse span 中记录成本（USD）
- [ ] THE System SHALL 支持自定义定价（企业版）
- [ ] THE System SHALL 定期更新定价表（跟随模型定价变化）

#### FR-8：成本聚合

**需求**：聚合统计 Agent Run 的总成本。

**聚合维度**：
- 单次 Agent Run 的总成本
- 按时间范围统计（日/周/月）
- 按 Agent 统计
- 按模型统计
- 按任务类型统计

**验收标准**：
- [ ] THE System SHALL 在 trace 级别聚合总成本
- [ ] THE System SHALL 支持按时间范围查询成本
- [ ] THE System SHALL 支持按 Agent 分组统计成本
- [ ] THE System SHALL 支持按模型分组统计成本
- [ ] THE System SHALL 支持导出成本报告（CSV/JSON）

### 3.4 性能监控

#### FR-9：延迟监控

**需求**：监控 LLM 调用的延迟。

**延迟指标**：
- **P50**：中位数延迟
- **P95**：95 分位延迟
- **P99**：99 分位延迟
- **Max**：最大延迟

**验收标准**：
- [ ] THE System SHALL 记录每次 LLM 调用的延迟
- [ ] THE System SHALL 在 Langfuse 中查询延迟统计（P50/P95/P99）
- [ ] THE System SHALL 支持按模型分组查询延迟
- [ ] THE System SHALL 支持按时间范围查询延迟趋势

#### FR-10：成功率监控

**需求**：监控 LLM 调用的成功率。

**成功率定义**：
- 成功：LLM 返回有效响应
- 失败：LLM 调用超时、返回错误、或抛出异常

**验收标准**：
- [ ] THE System SHALL 记录每次 LLM 调用的状态（success/error）
- [ ] THE System SHALL 在 Langfuse 中查询成功率统计
- [ ] THE System SHALL 支持按模型分组查询成功率
- [ ] THE System SHALL 支持按时间范围查询成功率趋势

### 3.5 质量评估

#### FR-11：人工标注

**需求**：支持在 Langfuse UI 中对 trace 进行人工标注。

**标注类型**：
- **评分**：1-5 星评分
- **标签**：好/坏/需改进
- **评论**：文字说明

**验收标准**：
- [ ] THE System SHALL 支持在 Langfuse UI 中对 trace 进行评分
- [ ] THE System SHALL 支持添加标签和评论
- [ ] THE System SHALL 支持查询标注统计（平均分、好评率）
- [ ] THE System SHALL 支持导出标注数据

#### FR-12：自动评分

**需求**：支持通过 API 自动对 trace 进行评分。

**评分维度**：
- **准确性**：决策是否正确
- **效率**：是否用最少的步骤完成任务
- **成本**：是否控制在预算内
- **安全性**：是否遵守约束和规则

**验收标准**：
- [ ] THE System SHALL 提供 API 对 trace 进行自动评分
- [ ] THE System SHALL 支持自定义评分逻辑
- [ ] THE System SHALL 在 Langfuse 中记录评分结果
- [ ] THE System SHALL 支持查询评分统计

### 3.6 配置和管理

#### FR-13：Langfuse 配置

**需求**：支持通过配置文件配置 Langfuse 连接。

**配置项**：
```yaml
langfuse:
  enabled: true
  public_key: "pk-lf-..."
  secret_key: "sk-lf-..."
  host: "https://cloud.langfuse.com"  # 或自托管地址
  
  # 采样配置
  sampling_rate: 1.0  # 1.0 = 100% 采样
  
  # 异步上报配置
  async_upload: true
  batch_size: 10
  flush_interval_seconds: 5
  
  # 隐私配置
  mask_inputs: false  # 是否脱敏输入
  mask_outputs: false  # 是否脱敏输出
```

**验收标准**：
- [ ] THE System SHALL 支持通过配置文件配置 Langfuse
- [ ] THE System SHALL 验证配置的合法性（启动时检查）
- [ ] THE System SHALL 支持禁用 Langfuse（enabled: false）
- [ ] THE System SHALL 支持采样配置（降低上报量）
- [ ] THE System SHALL 支持异步上报配置

#### FR-14：隐私保护

**需求**：支持脱敏敏感信息。

**脱敏策略**：
- **PII 脱敏**：邮箱、电话、身份证号等
- **密钥脱敏**：API keys、密码等
- **自定义脱敏**：通过正则表达式配置

**验收标准**：
- [ ] THE System SHALL 支持配置是否脱敏输入和输出
- [ ] THE System SHALL 自动检测和脱敏常见 PII（邮箱、电话）
- [ ] THE System SHALL 自动检测和脱敏密钥（API keys）
- [ ] THE System SHALL 支持自定义脱敏规则（正则表达式）
- [ ] THE System SHALL 在脱敏后保留数据结构（便于调试）

---

## 4. 非功能需求

### 4.1 性能需求

#### NFR-1：低延迟

**需求**：Langfuse 集成不应显著增加 Agent Run 的延迟。

**验收标准**：
- [ ] THE System SHALL 使用异步上报（不阻塞 Agent Run）
- [ ] THE System SHALL 在 Agent Run 延迟中增加 < 10ms（P95）
- [ ] THE System SHALL 支持批量上报（减少网络请求）

#### NFR-2：高吞吐

**需求**：支持高频率的 trace 上报。

**验收标准**：
- [ ] THE System SHALL 支持每秒 100+ 次 trace 创建
- [ ] THE System SHALL 支持每秒 1000+ 次 span 创建
- [ ] THE System SHALL 使用连接池（复用 HTTP 连接）

### 4.2 可靠性需求

#### NFR-3：容错

**需求**：Langfuse 不可用时不应影响 Agent Run。

**验收标准**：
- [ ] WHEN Langfuse 不可用时，THE System SHALL 降级（不上报）
- [ ] WHEN Langfuse 不可用时，THE System SHALL 记录警告日志
- [ ] WHEN Langfuse 不可用时，THE System SHALL 不抛出异常
- [ ] THE System SHALL 支持重试（可配置重试次数和延迟）

#### NFR-4：数据完整性

**需求**：确保 trace 数据的完整性。

**验收标准**：
- [ ] THE System SHALL 在 Agent Run 结束时确保 trace 已上报
- [ ] THE System SHALL 在进程退出时 flush 所有待上报的 trace
- [ ] THE System SHALL 支持本地缓存（网络故障时）
- [ ] THE System SHALL 支持重新上报（缓存恢复后）

### 4.3 安全需求

#### NFR-5：认证

**需求**：使用安全的方式认证 Langfuse。

**验收标准**：
- [ ] THE System SHALL 使用 API key 认证（public_key + secret_key）
- [ ] THE System SHALL 从环境变量或配置文件读取 API key
- [ ] THE System SHALL 不在日志中打印 API key
- [ ] THE System SHALL 支持 API key 轮换（无需重启）

#### NFR-6：数据传输

**需求**：使用安全的方式传输数据。

**验收标准**：
- [ ] THE System SHALL 使用 HTTPS 传输数据
- [ ] THE System SHALL 验证 SSL 证书
- [ ] THE System SHALL 支持自签名证书（自托管场景）

---

## 5. 验收标准总览

### 5.1 核心功能验收

- [ ] 为每次 Agent Run 创建 Langfuse trace
- [ ] 为每次 LLM 调用创建 span（包含 prompt、response、token、成本）
- [ ] 为每次工具调用创建 span（包含输入、输出、时长）
- [ ] 与 Agent Runtime 无缝集成（自动追踪）
- [ ] 精确记录 token 使用量和成本
- [ ] 监控 LLM 调用延迟和成功率
- [ ] 支持人工标注和自动评分

### 5.2 配置和管理验收

- [ ] 支持通过配置文件配置 Langfuse
- [ ] 支持禁用 Langfuse
- [ ] 支持采样配置
- [ ] 支持隐私保护（脱敏）

### 5.3 非功能验收

- [ ] 异步上报，不阻塞 Agent Run
- [ ] Langfuse 不可用时降级（不影响 Agent Run）
- [ ] 使用 HTTPS 和 API key 认证
- [ ] 进程退出时 flush 所有待上报的 trace

---

## 6. 约束与假设

### 6.1 约束

1. **Langfuse 依赖**：完全依赖 Langfuse Python SDK
2. **网络依赖**：需要网络连接到 Langfuse Server（云端或自托管）
3. **异步上报**：使用异步上报，可能有短暂延迟（秒级）
4. **数据保留**：Langfuse 的数据保留策略由 Langfuse 配置决定

### 6.2 假设

1. **Langfuse 可用性**：假设 Langfuse Server 大部分时间可用
2. **网络稳定性**：假设网络连接稳定
3. **SDK 兼容性**：假设 Langfuse Python SDK 向后兼容

---

## 7. 依赖

### 7.1 内部依赖

- **owlclaw.agent.runtime**：Agent 运行时（创建 trace）
- **owlclaw.integrations.llm**：LLM 客户端（创建 LLM span）
- **owlclaw.agent.tools**：工具系统（创建 tool span）

### 7.2 外部依赖

- **langfuse**：Langfuse Python SDK
- **Langfuse Server**：云端服务或自托管实例

---

## 8. 风险与缓解

### 8.1 风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Langfuse Server 不可用 | 无法追踪 LLM 调用 | 低 | 降级处理，不影响 Agent Run |
| 网络延迟高 | 上报延迟增加 | 中 | 异步上报 + 批量上报 |
| Token 计数不准确 | 成本统计错误 | 低 | 使用 LLM 返回的 token 数量 |
| 隐私泄露 | 敏感信息泄露 | 中 | 脱敏配置 + 访问控制 |
| 成本过高 | Langfuse 费用过高 | 低 | 采样配置 + 自托管 |

### 8.2 缓解措施

1. **降级处理**：Langfuse 不可用时自动降级
2. **异步上报**：使用异步上报 + 批量上报
3. **精确计数**：使用 LLM 返回的 token 数量
4. **隐私保护**：提供脱敏配置
5. **成本控制**：提供采样配置 + 支持自托管

---

## 9. Definition of Done

### 9.1 功能完成标准

- [ ] 所有功能需求（FR-1 到 FR-14）的验收标准通过
- [ ] 所有非功能需求（NFR-1 到 NFR-6）的验收标准通过
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 集成测试覆盖所有核心场景
- [ ] 端到端测试验证完整流程

### 9.2 文档完成标准

- [ ] API 文档完整（所有公开接口有文档字符串）
- [ ] 用户指南完整（包含快速开始、配置、隐私保护）
- [ ] 架构文档完整（设计决策、数据流、错误处理）
- [ ] 示例代码完整（至少 2 个典型场景）

### 9.3 质量完成标准

- [ ] 代码通过 mypy 类型检查
- [ ] 代码通过 ruff 格式检查
- [ ] 无已知的 P0/P1 bug
- [ ] 性能测试通过（延迟、吞吐量）

---

## 10. 参考文档

- **Langfuse 文档**：https://langfuse.com/docs
- **Langfuse Python SDK**：https://github.com/langfuse/langfuse-python
- **Agent Runtime**：.kiro/specs/agent-runtime/requirements.md
- **LLM 集成**：.kiro/specs/integrations-llm/requirements.md
- **架构分析**：docs/ARCHITECTURE_ANALYSIS.md §5.5 可观测性
