# audit-deep-remediation — 任务清单

> **Authority**: `docs/review/DEEP_AUDIT_REPORT.md` + `docs/review/DEEP_AUDIT_EXECUTION_CHECKLIST.md` + `.kiro/specs/audit-deep-remediation/requirements.md` + design.md

---

## codex-work 负责

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 1 | **P1-1** 在 `runtime.py` 的 `_inject_skill_env_for_run` 中仅注入 key 以 `OWLCLAW_SKILL_` 开头的 env；其余忽略并打 debug 日志 | 修改后运行带 env 的 skill，非前缀 key 不进入 os.environ；有单测或集成断言 | [ ] |
| 2 | **Low-3** 将 `_visible_tools_cache` 与 skills 上下文缓存改为 LRU（如 cachetools.LRUCache 或 OrderedDict 按访问） | 缓存满时逐出最近最少使用项；现有缓存相关测试通过 | [ ] |
| 3 | **Low-5** 在 LLM 异常分支中不再向消息追加 `str(exc)`，改为固定文案或安全简短描述 | grep 确认无 `str(exc)` 进 assistant content；异常路径有测试 | [ ] |
| 4 | **Low-4a** 在 Ledger 上暴露 `get_readonly_session_factory()`（或等价）公开 API，内部复用现有 _session_factory | 方法存在且可返回只读用 session 工厂；不暴露 _session_factory | [ ] |

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
| 11 | **Low-8** 在 `app.py` 的 `health_status()` 中避免直接读 `_states`/`_configs`：改为 manager/server 的公开 API 或只读属性，或文档明确该耦合 | 无私有属性访问或文档注明；health 相关测试通过 | [ ] |
| 12 | **Low-9** 在 Ledger._background_writer 的 except Exception 分支中，将当前 batch 写入 fallback 再继续循环，避免丢失已出队记录 | 异常路径有单测或集成验证；batch 不丢 | [ ] |
| 13 | **Low-10** Ledger._write_queue 设 maxsize 或实现背压（put 超时/丢弃策略），并文档化上限 | 队列有界或文档明确；压力测试可选 | [ ] |
| 15 | **Low-12** 在 Console API TokenAuthMiddleware 中用 hmac.compare_digest 做 token 常量时间比较 | grep 确认无直接 !=/== 比较 token；有单测或手验 | [ ] |

---

## codex-gpt-work 负责（续）

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 14 | **Low-11** 在 webhook receive_webhook 中对 raw_body_bytes.decode("utf-8") 做 try/except UnicodeDecodeError，返回 400 及明确提示 | 非 UTF-8 body 返回 400 而非 500；有单测或手验 | [x] |

---

## 可选（同一 spec 内可后做）

| # | Task | 验收 | 状态 |
|---|------|------|------|
| 8 | P1-1 扩展：支持运行时 `skill_env_allowlist` 配置，允许无前缀的 key | 配置项生效且文档或注释说明 | [ ] |
| 9 | P1-2 实现：deps.get_tenant_id 从请求上下文/认证读取 tenant（若已有 auth 中间件） | 有则实现并测试；无则跳过 | [ ] |

---

## 执行顺序建议

1. codex-work：Task 1（P1-1）→ Task 2（Low-3）→ Task 3（Low-5）→ Task 4（Low-4a）→ Task 11（Low-8）→ Task 12（Low-9）→ Task 13（Low-10）→ Task 15（Low-12）；提交后合并到 main。
2. codex-gpt-work：Task 5（P1-2 文档）可随时做；Task 6（Low-4b）需等 Task 4 合并后执行；Task 7、10、14（Low-6/7/11）可并行。
3. 审校：两个分支分别 Review，通过后合并 review-work → main。
