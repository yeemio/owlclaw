# audit-deep-remediation — 任务清单

> **Authority**: `docs/review/DEEP_AUDIT_REPORT.md` + `docs/review/DEEP_AUDIT_EXECUTION_CHECKLIST.md` + `.kiro/specs/audit-deep-remediation/requirements.md` + design.md

---

## codex-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 1 | **P1-1** 在 `runtime.py` 的 `_inject_skill_env_for_run` 中仅注入 key 以 `OWLCLAW_SKILL_` 开头的 env；其余忽略并打 debug 日志 | 修改后运行带 env 的 skill，非前缀 key 不进入 os.environ；有单测或集成断言 | [x] |
| 2 | **Low-3** 将 `_visible_tools_cache` 与 skills 上下文缓存改为 LRU（如 cachetools.LRUCache 或 OrderedDict 按访问） | 缓存满时逐出最近最少使用项；现有缓存相关测试通过 | [x] |
| 3 | **Low-5** 在 LLM 异常分支中不再向消息追加 `str(exc)`，改为固定文案或安全简短描述 | grep 确认无 `str(exc)` 进 assistant content；异常路径有测试 | [x] |
| 4 | **Low-4a** 在 Ledger 上暴露 `get_readonly_session_factory()`（或等价）公开 API，内部复用现有 _session_factory | 方法存在且可返回只读用 session 工厂；不暴露 _session_factory | [x] |

---

## codex-gpt-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 5 | **P1-2** 在 docs 中新增/更新「Console 多租户与 tenant_id」：当前行为、适用场景、多租户须从认证推导 | 文档存在且包含上述三点 | [x] |
| 6 | **Low-4b** 在 HeartbeatChecker 中改为使用 Ledger 的 `get_readonly_session_factory()`，移除对 `_session_factory` 的 getattr | grep 确认 heartbeat 无 _session_factory；heartbeat 相关测试通过 | [x] |
| 7 | **Low-6** 在 `db/engine.py` 的 `create_engine` 中收窄异常映射：仅连接/认证类映射为 Database*Error；其余保留或 EngineError | 非连接类异常不再被误报为连接错误；有单测或集成验证 | [x] |
| 10 | **Low-7** 在 `web/providers/capabilities.py` 的 `_collect_capability_stats` 中捕获 ConfigurationError，无 DB 时返回空 stats（与 ledger/triggers 一致，GET /capabilities 不 500） | 无 DB 时 GET /capabilities 返回 200 + items（零统计）；有单测或手验 | [x] |

---

## codex-work 负责（续）

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 11 | **Low-8** 在 `app.py` 的 `health_status()` 中避免直接读 `_states`/`_configs`：改为 manager/server 的公开 API 或只读属性，或文档明确该耦合 | 无私有属性访问或文档注明；health 相关测试通过 | [x] |
| 12 | **Low-9** 在 Ledger._background_writer 的 except Exception 分支中，将当前 batch 写入 fallback 再继续循环，避免丢失已出队记录 | 异常路径有单测或集成验证；batch 不丢 | [x] |
| 13 | **Low-10** Ledger._write_queue 设 maxsize 或实现背压（put 超时/丢弃策略），并文档化上限 | 队列有界或文档明确；压力测试可选 | [x] |
| 15 | **Low-12** 在 Console API TokenAuthMiddleware 中用 hmac.compare_digest 做 token 常量时间比较 | grep 确认无直接 !=/== 比较 token；有单测或手验 | [ ] |
| 18 | **Low-15** 在 `http_executor.py` 中收紧/明确空 `allowed_hosts` 的安全边界，避免默认允许任意公网 host 而无告警 | 有测试、配置校验或明确文档；SSRF 风险边界可审计 | [ ] |
| 19 | **Low-16** 在 `BindingTool` 写 ledger 失败记录时不再持久化原始 `str(exc)`，改为统一安全错误消息 | grep 确认无原始 `str(exc)` 写入 ledger；有测试 | [ ] |
| 24 | **Low-21** 在 `CapabilityRegistry.invoke_handler()` / `get_state()` 中避免将原始异常字符串直接包装回调用方 | 调用方只见安全文案或类型级描述；有测试 | [ ] |

---

## codex-gpt-work 负责（续）

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 14 | **Low-11** 在 webhook receive_webhook 中对 raw_body_bytes.decode("utf-8") 做 try/except UnicodeDecodeError，返回 400 及明确提示 | 非 UTF-8 body 返回 400 而非 500；有单测或手验 | [x] |
| 16 | **Low-13** 在 VisibilityFilter evaluator 路径增加 timeout 或明确文档边界，避免单个 evaluator 长时间阻塞 capability 过滤 | 有测试、手验或文档结论；不会无限等待单个 evaluator | [x] |
| 17 | **Low-14** 收敛 Hatchet Windows SIGQUIT 兼容逻辑的作用域，避免全局 `signal` 模块副作用 | 代码或文档说明明确；Windows 兼容逻辑边界清晰 | [x] |
| 20 | **Low-17** 在 API trigger 请求读取路径按实际读取体积强制 body 大小上限，不再只信任 `Content-Length` | 超限请求在省略/伪造 header 时仍被拒绝；有测试 | [ ] |
| 21 | **Low-18** 在 API trigger 写 ledger 失败记录时复用安全错误消息，不持久化原始 `str(exc)` | grep 确认失败路径无原始异常写入 ledger；有测试 | [ ] |
| 22 | **Low-19** 在 API trigger `AuthProvider` 中用 `hmac.compare_digest` 做 key/token 常量时间比较 | grep 确认无直接 token 比较；有测试或手验 | [ ] |
| 23 | **Low-20** 在 cron `get_execution_history` 中避免向调用方返回未脱敏的 ledger 错误信息 | 输出已 redacted 或由上游写入统一脱敏；有测试 | [ ] |

---

## 可选（同一 spec 内可后做）

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 8 | P1-1 扩展：支持运行时 `skill_env_allowlist` 配置，允许无前缀的 key | 配置项生效且文档或注释说明 | [ ] |
| 9 | P1-2 实现：deps.get_tenant_id 从请求上下文/认证读取 tenant（若已有 auth 中间件） | 有则实现并测试；无则跳过 | [ ] |

---

## 执行顺序建议

1. codex-work：首批 Task 1/2/3/4/11/12/13 已完成并合入 `main`；下一批执行 Task 15/18/19/24（Low-12/15/16/21）。
2. codex-gpt-work：Task 5（P1-2 文档）可随时做；Task 6（Low-4b）在 Task 4 已合入 `main` 后可启动；Task 7、10、14、16、17、20、21、22、23 可并行。
3. 审校：两个分支分别 Review，通过后合并 review-work → main。
