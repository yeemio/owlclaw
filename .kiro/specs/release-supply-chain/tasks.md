# Tasks: Release Supply Chain

> **状态**：进行中  
> **预估工作量**：3-4 天  
> **最后更新**：2026-02-26

## 进度概览

- **总任务数**：15
- **已完成**：10
- **进行中**：0
- **未开始**：5

## 1. OIDC 发布

- [ ] 1.1 配置 TestPyPI Trusted Publisher
  - 状态补充（2026-02-26）：在 `codex-gpt-work` 触发 run `22449095206`，`pypa/gh-action-pypi-publish@release/v1` 返回 `invalid-publisher`，说明 TestPyPI 尚未配置与当前 claim 匹配的 Trusted Publisher（`workflow_ref=.github/workflows/release.yml@refs/heads/codex-gpt-work`）。
  - 状态补充（2026-02-26）：已在 workflow 增加固定 `environment: pypi-release` 并验证 run `22449361552`；当前 claim 为 `sub=repo:yeemio/owlclaw:environment:pypi-release`、`environment=pypi-release`，仍返回 `invalid-publisher`，说明 TestPyPI 侧尚未建立该发布者映射。
- [ ] 1.2 配置 PyPI Trusted Publisher
  - 状态补充（2026-02-26）：与 1.1 同源，需在 PyPI 侧补齐 Trusted Publisher 映射后复跑正式链路。
- [x] 1.3 调整 workflow 使用 OIDC

## 2. 验证与证明

- [ ] 2.1 发布后执行 `pip install` smoke
- [x] 2.2 生成并上传 provenance/attestation
- [x] 2.3 归档发布报告（version/commit/run）

## 3. 门禁与保护

- [x] 3.1 校准 required checks
  - 状态补充（2026-02-26）：已产出 baseline（Lint/Test/Build）与审计报告 `docs/release/release-policy-audit.json`。
  - 状态补充（2026-02-26）：新增供应链就绪审计脚本 `scripts/ops/release_supply_chain_audit.py`，最新报告 `docs/release/release-supply-chain-audit.json`（包含 release runs / environments / secrets / branch protection）。
- [x] 3.2 校准 release 分支保护
  - 状态补充（2026-02-26）：审计显示 `main` 当前未开启保护（HTTP 404 Branch not protected），已固化建议基线 `docs/release/release-policy-baseline.md`，待维护者应用。
- [x] 3.3 校准失败回滚策略

## 4. 演练与收口

- [ ] 4.1 TestPyPI 全链路演练
  - 状态补充（2026-02-26）：run `22446541468` 已执行演练但在 TestPyPI 上传阶段失败（`HTTP 403`，`TWINE_PASSWORD` 为空），主分支仍为旧 token 链路。
  - 状态补充（2026-02-26）：新增演练 runs `22447692518`、`22447700064`，两次均在 `Publish to TestPyPI` 失败（`HTTP 403`，`TWINE_PASSWORD` 为空），Trusted Publisher/发布凭据阻塞未解除。
  - 状态补充（2026-02-26）：在 `codex-gpt-work` 的 OIDC 链路 run `22449095206` 失败于 `invalid-publisher`（token 有效但未找到匹配发布者），根因已收敛到 Trusted Publisher claim 映射。
  - 状态补充（2026-02-26）：run `22449361552`（已绑定 `environment: pypi-release`）仍在 `Publish to TestPyPI` 报 `invalid-publisher`；说明 workflow 侧 claim 规范化已完成，剩余阻塞仅在 PyPI/TestPyPI 发布者配置。
- [ ] 4.2 PyPI 正式链路演练
- [x] 4.3 更新 `SPEC_TASKS_SCAN` checkpoint

## 5. 阈值与剧本固化

- [x] 5.1 固化成功率与时延阈值
- [x] 5.2 新增验收矩阵并绑定发布证据
- [x] 5.3 完成 T+0~T+15 处置剧本演练

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26
