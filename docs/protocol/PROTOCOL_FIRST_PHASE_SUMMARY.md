# Protocol-first 阶段总结

> 状态：阶段收口（2026-02-27）  
> 范围：API + MCP 协议治理、契约门禁、跨语言路径、网关运行策略

## 1. 决策

- 采用 Gateway-first：协议面优先，SDK 作为语法糖层。
- API 与 MCP 共享统一版本策略与错误域，不允许双标准。
- 契约治理采用分级门禁：warning -> blocking，并保留例外审计链路。

## 2. 结果

- 协议治理文档完成：`VERSIONING.md`、`ERROR_MODEL.md`、`COMPATIBILITY_POLICY.md`、`GOVERNANCE_GATE_POLICY.md`。
- API/MCP 契约门禁落地：OpenAPI diff 检测、MCP 核心路径回归、对齐矩阵与策略文档。
- 网关运维基线落地：canary/rollback/SLO 文档与 gate/drill 脚本。
- 跨语言 Golden Path 落地：Java 示例、curl 对照、`scripts/verify_cross_lang.ps1` 验证与报告。

## 3. 遗留与后续路线

- 发布供应链安全仍在进行中：`release-supply-chain` 当前 9/15。
- 外部依赖阻塞（仓库/发布平台配置）：
  - 2026-02-26，run `22446541468` 在 TestPyPI 上传返回 `HTTP 403 Forbidden`。
  - 2026-02-26，`branches/main/protection` 查询为 `404 Branch not protected`。
  - 2026-02-26，`rulesets` 查询结果为空数组 `[]`。
- 下一阶段聚焦：完成 Trusted Publisher 与分支保护配置后，复跑发布链路并收口剩余 6 项任务。

## 4. 维护模式说明

- 协议核心文档、契约测试、跨语言脚本进入维护模式。
- 新增协议能力需先更新契约与门禁，再进入实现层。
