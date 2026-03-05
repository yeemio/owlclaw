# Console 浏览器手工验收补充报告（codex-work）

> 日期：2026-03-05  
> Spec：`console-browser-real-e2e` Task 2.1~2.3  
> 环境：无 DB（降级路径），无 Hatchet，无 Langfuse

## 1. 执行结论

- 自动化基线：`npm run test:e2e:run` 结果 `33 passed`
- 手工项执行状态：已逐项对照 checklist，未通过项已记录复现与风险
- 放行建议：`CONDITIONAL_PASS`

## 2. 手工维度结果（补齐项）

### 2.1 已覆盖并通过

- `E-3` 页面切换无全量刷新（SPA）  
  证据：`console-flow.spec.ts` 用例 `E-3: Navigation is SPA`
- `E-6` Governance 无数据时无白屏  
  证据：`console-flow.spec.ts` 用例 `E-6: Governance with empty data shows chart/sections, no white screen`
- `API-17` 错误结构负例（422）  
  证据：`Negative: ledger 422 returns friendly error`
- `N-10` 无未捕获 JS 错误  
  证据：`No uncaught JavaScript errors across main nav`

### 2.2 未通过/待补项（Task 2.3 复现清单）

1. `N-8` WebSocket 消息类型验收未完成  
   - 现象：仅能验证连接尝试，无法验证收到 `overview/triggers/ledger` 消息。  
   - 复现：执行 `npm run test:e2e:run`，后端日志出现  
     `No supported WebSocket library detected`。  
   - 根因：运行环境缺少 websocket 依赖。  
   - 建议：安装 `uvicorn[standard]` 后复验 `N-8`。

2. `F-16` Agents 详情面板内容验收受无 DB 场景限制  
   - 现象：无真实 Agent 数据时无法验证“身份/记忆/知识库/运行历史”字段完整性。  
   - 复现：无 DB 或空 DB 启动，Agents 页面为空状态。  
   - 建议：在最小种子数据环境补一轮手工点检。

3. `F-18` Triggers 统一列表与历史细项仍为降级验证  
   - 现象：已验证页面可用与无白屏，但未覆盖“六类触发器均有真实条目”的人工验收。  
   - 复现：无 DB 场景仅返回空列表/降级文案。  
   - 建议：带真实触发器数据复验。

4. `F-20` Traces/Workflows 外链可达性未在本批次落证  
   - 现象：路由存在，但外部服务连通性未在本地验收报告中给出证据。  
   - 建议：增加外链可达性截图或 HTTP 状态证明。

5. `E-2` 响应式（1024px）与 `E-9` 全页对比度仍缺显式证据  
   - 现象：现有自动化包含 axe A/AA（Overview/Governance/Ledger），但非全页覆盖。  
   - 建议：补移动/窄屏截图与全页对比度扫描记录。

## 3. 复现场景与命令

```powershell
cd owlclaw/web/frontend
npm run test:e2e:run
```

## 4. 建议放行口径

- 当前可以作为 `CONDITIONAL_PASS` 进入审校：
  - 核心主路径、API 契约、无白屏、无未捕获错误已覆盖；
  - 剩余项集中在“真实数据场景/外部服务联通/WS 消息”。
- 若发布门禁要求 `PASS`，需先关闭上述 5 个待补项。
