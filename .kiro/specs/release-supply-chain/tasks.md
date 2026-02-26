# Tasks: Release Supply Chain

> **状态**：进行中  
> **预估工作量**：3-4 天  
> **最后更新**：2026-02-26

## 进度概览

- **总任务数**：15
- **已完成**：9
- **进行中**：0
- **未开始**：6

## 1. OIDC 发布

- [ ] 1.1 配置 TestPyPI Trusted Publisher
  - 状态补充（2026-02-26）：在 `codex-gpt-work` 触发 run `22449095206`，`pypa/gh-action-pypi-publish@release/v1` 返回 `invalid-publisher`，说明 TestPyPI 尚未配置与当前 claim 匹配的 Trusted Publisher（`workflow_ref=.github/workflows/release.yml@refs/heads/codex-gpt-work`）。
  - 状态补充（2026-02-26）：已在 workflow 增加固定 `environment: pypi-release` 并验证 run `22449361552`；当前 claim 为 `sub=repo:yeemio/owlclaw:environment:pypi-release`、`environment=pypi-release`，仍返回 `invalid-publisher`，说明 TestPyPI 侧尚未建立该发布者映射。
- [ ] 1.2 配置 PyPI Trusted Publisher
  - 状态补充（2026-02-26）：与 1.1 同源，需在 PyPI 侧补齐 Trusted Publisher 映射后复跑正式链路。
- [x] 1.3 调整 workflow 使用 OIDC

## 2. 验证与证明

- [x] 2.1 发布后执行 `pip install` smoke
- [x] 2.2 生成并上传 provenance/attestation
- [x] 2.3 归档发布报告（version/commit/run）

## 3. 门禁与保护

- [ ] 3.1 校准 required checks
  - 当前状态（2026-02-26）：`gh api repos/yeemio/owlclaw/branches/main/protection` 返回 `404 Branch not protected`，required checks 尚未启用（外部仓库设置项）
- [ ] 3.2 校准 release 分支保护
  - 当前状态（2026-02-26）：`gh api repos/yeemio/owlclaw/rulesets` 返回空数组 `[]`，未发现规则集保护（外部仓库设置项）
- [x] 3.3 校准失败回滚策略

说明（2026-02-26）：已新增供应链就绪审计脚本 `scripts/ops/release_supply_chain_audit.py` 并生成 `docs/release/release-supply-chain-audit.json`，用于持续追踪 required checks / branch protection / environment / secrets 状态。

## 4. 演练与收口

- [ ] 4.1 TestPyPI 全链路演练
  - 演练记录（2026-02-26）：`gh workflow run release.yml -f target=testpypi` 已执行；run `22446541468` 在 `Publish to TestPyPI` 返回 `HTTP 403 Forbidden`，阻塞点为 Trusted Publisher 绑定未完成（对应 Task 1.1）
  - 状态补充（2026-02-26）：新增演练 runs `22447692518`、`22447700064`，两次均在 `Publish to TestPyPI` 失败（`HTTP 403`，`TWINE_PASSWORD` 为空），Trusted Publisher/发布凭据阻塞未解除。
  - 状态补充（2026-02-26）：在 `codex-gpt-work` 的 OIDC 链路 run `22449095206` 失败于 `invalid-publisher`（token 有效但未找到匹配发布者），根因已收敛到 Trusted Publisher claim 映射。
  - 状态补充（2026-02-26）：run `22449361552`（已绑定 `environment: pypi-release`）仍在 `Publish to TestPyPI` 报 `invalid-publisher`；说明 workflow 侧 claim 规范化已完成，剩余阻塞仅在 PyPI/TestPyPI 发布者配置。
- [ ] 4.2 PyPI 正式链路演练
  - 当前状态（2026-02-26）：前置 TestPyPI OIDC 未打通，正式链路演练顺延（依赖 Task 1.2/3.1/3.2）
- [x] 4.3 更新 `SPEC_TASKS_SCAN` checkpoint

## 5. 阈值与剧本固化

- [x] 5.1 固化成功率与时延阈值
- [x] 5.2 新增验收矩阵并绑定发布证据
- [x] 5.3 完成 T+0~T+15 处置剧本演练

---

**维护者**：Release 工程组  
**最后更新**：2026-02-26
