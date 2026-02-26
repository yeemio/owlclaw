# scripts/ 说明

本目录存放仓库级辅助脚本。脚本分为两类：

- `CI 使用`：被 GitHub Actions 或发布流程直接调用
- `本地开发使用`：开发者本地验证、诊断或模板生成

| 脚本 | 用途 | 典型命令 | 分类 |
|---|---|---|---|
| `release_preflight.py` | 发布前门禁检查（版本/变更/工件前置条件） | `poetry run python scripts/release_preflight.py` | CI 使用 |
| `owlhub_release_gate.py` | OwlHub 发布闸门验证 | `poetry run python scripts/owlhub_release_gate.py --help` | CI 使用 |
| `owlhub_build_index.py` | 生成 OwlHub index 数据 | `poetry run python scripts/owlhub_build_index.py --help` | CI 使用 |
| `owlhub_generate_site.py` | 生成 OwlHub 静态站点内容 | `poetry run python scripts/owlhub_generate_site.py --help` | CI 使用 |
| `validate_examples.py` | 批量验证 `examples/` 可运行性 | `poetry run python scripts/validate_examples.py` | CI 使用 |
| `contract_diff.py` | 协议契约差异分级与门禁决策（warning/blocking） | `poetry run python scripts/contract_diff.py --help` | CI 使用 |
| `contract_diff/run_contract_diff.py` | 契约门禁包装入口（用于 PR/nightly 统一调用） | `poetry run python scripts/contract_diff/run_contract_diff.py --help` | CI 使用 |
| `contract_diff/contract_testing_drill.py` | 执行 contract-testing breaking 注入演练并产出报告 | `poetry run python scripts/contract_diff/contract_testing_drill.py` | CI 使用 |
| `protocol_governance_drill.py` | 执行 breaking 注入/豁免审计演练并产出证据报告 | `poetry run python scripts/protocol_governance_drill.py` | CI 使用 |
| `gateway_ops_gate.py` | 网关发布门禁决策与回滚执行辅助 | `poetry run python scripts/gateway_ops_gate.py` | CI 使用 |
| `gateway_ops_drill.py` | 执行 canary 回滚/全量成功演练并产出报告 | `poetry run python scripts/gateway_ops_drill.py` | CI 使用 |
| `test_queue_trigger.py` | 队列触发链路本地回归脚本 | `poetry run python scripts/test_queue_trigger.py` | 本地开发使用 |
| `review_template.py` | 生成/检查审校模板 | `poetry run python scripts/review_template.py --help` | 本地开发使用 |
| `test_template.py` | 测试模板脚手架检查 | `poetry run python scripts/test_template.py --help` | 本地开发使用 |
| `completions/` | CLI 自动补全生成物 | 按 shell 类型加载 | 本地开发使用 |

## 约定

1. 所有脚本应支持 `--help`（或在文件头部给出使用说明）。
2. CI 关键脚本改动必须附带对应单元测试或集成验证。
3. 脚本内禁止硬编码密钥；凭证统一走环境变量。
