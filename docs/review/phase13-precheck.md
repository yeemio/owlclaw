# Phase 13 Precheck Template (review-work)

> 目的：为 `phase13-low-findings` 的 #11/#12 提供一键预审清单。  
> 适用分支：`review-work`  
> 最后更新：2026-03-05

---

## 0. 基础信息

- 审校人：
- 审校时间：
- 目标分支：`codex-work`
- 对照 spec：`.kiro/specs/phase13-low-findings/`
- 对照总表：`.kiro/specs/SPEC_TASKS_SCAN.md`

---

## 0.5 一键执行（建议复制整段）

```powershell
# 1) 同步基线（在 review-work）
git merge main

# 2) 拉取待审分支差异（按需）
git log --oneline main..codex-work
git diff --stat main..codex-work

# 3) 运行 #11/#12 定向测试
poetry run pytest tests/unit/integrations/test_langfuse.py tests/unit/capabilities/test_bindings_sql_executor.py

# 4) 快速定位关键实现
rg -n "to_safe_dict|_safe_error_message|_is_select_query|read_only|multi" owlclaw/integrations/langfuse.py owlclaw/capabilities/bindings/sql_executor.py
```

通过门槛：
- pytest 退出码 `0`
- 差异中能定位 #11/#12 对应实现与测试
- 无新增阻断回归

---

## 1. Spec 对齐检查

- [ ] `tasks.md` 勾选状态与 `SPEC_TASKS_SCAN.md` 的 L1/L2 一致
- [ ] `requirements.md` 中 FR-L1/FR-L2 验收项已与实现状态一致
- [ ] `design.md` 中实现路径均为真实路径（特别是 `sql_executor.py`）
- [ ] `SPEC_TASKS_SCAN.md` Checkpoint 的“当前批次/批次状态/下一待执行”与事实一致

记录：
- 结论：
- 证据（文件+行）：

---

## 2. 代码检查（#11/#12）

### 2.1 Finding #11（Langfuse Secret）

- [ ] `LangfuseConfig` 的敏感字段 `public_key/secret_key` 不会在 `repr` 中暴露
- [ ] 存在安全导出方法（如 `to_safe_dict()`）并对密钥统一掩码
- [ ] 错误日志路径不会输出原始密钥文本

文件：
- `owlclaw/integrations/langfuse.py`

### 2.2 Finding #12（SQL Read-Only Guard）

- [ ] SQL 判定前有注释/空白规范化
- [ ] 多语句（`;`）场景 fail-close（只读模式拒绝）
- [ ] 仅允许 `SELECT/WITH` 起始；命中写操作关键字拒绝
- [ ] 误判风险有对应测试覆盖（注释绕过/大小写混淆/CTE 副作用）

文件：
- `owlclaw/capabilities/bindings/sql_executor.py`

记录：
- 结论：
- 风险点：
- 建议：

---

## 2.3 阻断判定矩阵（快速给 Verdict）

| 触发条件 | 结论 | 说明 |
|---|---|---|
| 密钥明文出现在 `repr/log/error` 任一路径 | `REJECT` | 安全阻断，禁止合并 |
| 只读 SQL 可被注释/多语句绕过 | `REJECT` | 违反只读承诺，禁止合并 |
| 关键测试失败或新增回归 | `FIX_NEEDED` | 先修复再审 |
| 代码通过但 spec/checkpoint 未对齐 | `FIX_NEEDED` | 先补文档一致性 |
| 代码 + 测试 + spec 全通过 | `APPROVE` | 允许进入 merge 步骤 |

---

## 3. 测试检查

执行命令：

```powershell
poetry run pytest tests/unit/integrations/test_langfuse.py
poetry run pytest tests/unit/capabilities/test_bindings_sql_executor.py
```

- [ ] 上述两条命令通过
- [ ] 新增用例覆盖点可在测试名称中定位
- [ ] 无额外回归失败

输出摘要：
- `test_langfuse.py`：
- `test_bindings_sql_executor.py`：

---

## 4. 结论模板（必须三选一）

### 4.1 APPROVE

```text
review(phase13-low-findings): APPROVE — #11/#12 与 spec 对齐，测试通过
检查项：代码质量 ✅ | Spec 一致性 ✅ | 测试覆盖 ✅ | 架构合规 ✅
问题：无
```

### 4.2 FIX_NEEDED

```text
review(phase13-low-findings): FIX_NEEDED — <一句话结论>
检查项：代码质量 ⚠️ | Spec 一致性 ✅ | 测试覆盖 ⚠️ | 架构合规 ✅
问题：
1. <文件:行> <风险> <修复建议>
2. <文件:行> <风险> <修复建议>
```

### 4.3 REJECT

```text
review(phase13-low-findings): REJECT — <严重问题结论>
检查项：代码质量 ❌ | Spec 一致性 ⚠️ | 测试覆盖 ⚠️ | 架构合规 ❌
问题：
1. <文件:行> <阻断级风险> <裁决建议>
```

---

## 5. 归档

- 审校 commit：
- 是否合并到 `review-work`：
- 是否更新 `SPEC_TASKS_SCAN` Checkpoint：

证据归档（建议）：
- 审校报告：`.kiro/reviews/YYYY-MM-DD-incremental-review-roundXX.md`
- 关键 diff：`git diff --name-only main..codex-work`
- 测试摘要：pytest 末尾通过行（总用例数 + 耗时）
