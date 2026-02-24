# OwlHub Phase 3 服务化模式说明

## 1. Phase 3 目标与边界

Phase 3 将 OwlHub 从静态索引扩展为 API 服务，提供发布、审核、治理、统计导出与鉴权能力。

当前实现边界（与仓库代码对齐）：
- API 服务：已实现（FastAPI）
- 鉴权/授权：已实现（Bearer JWT + API Key + 角色门禁）
- 审核/统计/黑名单存储：当前为文件存储（JSON/JSONL）
- `alembic` 迁移流程：已接入部署流水线（用于平台数据库迁移步骤）

## 2. 架构图（Phase 3）

```
CLI / API Clients
        |
        v
FastAPI (owlclaw.owlhub.api.app)
  |- /api/v1/skills
  |- /api/v1/reviews
  |- /api/v1/statistics
  |- /api/v1/admin/blacklist
  |- /api/v1/auth
  |- /api/v1/audit
        |
        +--> Index Storage (index.json)
        +--> Review Storage (review records/*.json)
        +--> Statistics Storage (skill_statistics.json)
        +--> Blacklist Storage (blacklist.json)
        +--> Audit Storage (audit.log.jsonl)
```

## 3. API 端点与示例（OpenAPI/Swagger）

OpenAPI 文档入口：
- Swagger UI: `/docs`
- ReDoc: `/redoc`

核心端点：
- 健康与指标
  - `GET /health`
  - `GET /metrics`
- 鉴权
  - `POST /api/v1/auth/token`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/auth/api-keys`
- 技能查询与发布
  - `GET /api/v1/skills`
  - `GET /api/v1/skills/{publisher}/{name}`
  - `GET /api/v1/skills/{publisher}/{name}/versions`
  - `GET /api/v1/skills/{publisher}/{name}/statistics`
  - `POST /api/v1/skills`
  - `PUT /api/v1/skills/{publisher}/{name}/versions/{version}/state`
  - `POST /api/v1/skills/{publisher}/{name}/takedown`
- 审核
  - `GET /api/v1/reviews/pending`
  - `POST /api/v1/reviews/{review_id}/approve`
  - `POST /api/v1/reviews/{review_id}/reject`
  - `POST /api/v1/reviews/{review_id}/appeal`
- 治理与审计
  - `GET /api/v1/admin/blacklist`
  - `POST /api/v1/admin/blacklist`
  - `DELETE /api/v1/admin/blacklist`
  - `GET /api/v1/statistics/export?format=json|csv`
  - `GET /api/v1/audit`

发布示例：

```bash
curl -X POST http://localhost:8000/api/v1/skills \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "publisher": "acme1111",
    "skill_name": "entry-monitor",
    "version": "1.0.0",
    "metadata": {
      "description": "entry monitor skill",
      "license": "MIT",
      "tags": ["monitor"],
      "dependencies": {},
      "download_url": "https://example.com/entry-monitor-1.0.0.tar.gz",
      "checksum": "sha256:..."
    }
  }'
```

## 4. 鉴权与授权流程

支持两种凭证：
- Bearer Token（`POST /api/v1/auth/token` 获取）
- API Key（`POST /api/v1/auth/api-keys` 创建）

角色约束：
- `publisher`: 可发布/更新自己名下技能
- `reviewer`: 可审核待审记录
- `admin`: 可执行黑名单、统计导出、下架、审计查询

中间件策略：
- 写操作（`POST|PUT|PATCH|DELETE`）默认要求凭证
- `/api/v1/auth/*` 与 `/health` 允许匿名
- `/api/v1/admin/*` 强制 `admin` 角色

## 5. 部署流程（Docker 与 Kubernetes）

Docker 本地开发：
- 镜像: `deploy/Dockerfile.owlhub-api`
- 编排: `deploy/docker-compose.owlhub-api.yml`
- 依赖服务: `postgres`, `redis`（可选 profile）

```bash
docker compose -f deploy/docker-compose.owlhub-api.yml up -d --build
```

Kubernetes 清单：
- `deploy/k8s/owlhub-api-deployment.yaml`
- `deploy/k8s/owlhub-api-service.yaml`
- `deploy/k8s/owlhub-api-configmap.yaml`
- `deploy/k8s/owlhub-api-secret.yaml`
- `deploy/k8s/owlhub-api-ingress.yaml`

```bash
kubectl apply -f deploy/k8s/owlhub-api-configmap.yaml
kubectl apply -f deploy/k8s/owlhub-api-secret.yaml
kubectl apply -f deploy/k8s/owlhub-api-deployment.yaml
kubectl apply -f deploy/k8s/owlhub-api-service.yaml
kubectl apply -f deploy/k8s/owlhub-api-ingress.yaml
```

CI/CD（GitHub Actions）：
- 工作流：`.github/workflows/owlhub-api-deploy.yml`
- 支持 `staging`/`production` 环境
- 部署后自动执行：
  - 数据库迁移：`alembic -c alembic.ini upgrade head`
  - smoke tests：`/health`、`/metrics`

## 6. 数据模式与迁移

当前 OwlHub 域对象持久化：
- 索引：`OWLHUB_INDEX_PATH`（`index.json`）
- 审核：`OWLHUB_REVIEW_DIR`（review records）
- 统计：`OWLHUB_STATISTICS_DB`（统计 JSON）
- 黑名单：`OWLHUB_BLACKLIST_DB`（黑名单 JSON）
- 审计：`OWLHUB_AUDIT_LOG`（JSONL）

数据库迁移基础设施：
- Alembic 配置：`alembic.ini`
- 迁移目录：`migrations/versions/`
- 迁移命令：

```bash
poetry run alembic -c alembic.ini upgrade head
```

说明：
- 目前仓库内 OwlHub 业务数据仍以文件持久化为主；
- 迁移步骤已纳入部署流程，便于后续将 OwlHub 业务表平滑迁移到数据库。

## 7. 监控与故障排查

监控入口：
- `GET /health`: 返回索引/存储路径健康状态
- `GET /metrics`: Prometheus 指标（请求量、时延、错误率、技能统计）

常见排查项：
1. `/health` 中 `index` 为 `warn`：检查 `OWLHUB_INDEX_PATH` 与文件挂载。
2. 发布返回 `422`：检查 manifest 字段（`name/version/publisher/description/license`）。
3. 发布返回 `403`：检查 publisher 与 token 身份映射或黑名单状态。
4. 统计导出返回 `403`：确认调用者角色为 `admin`。
5. 部署后服务不可用：检查 k8s rollout 状态与 workflow smoke test 输出。

## 8. 安全最佳实践

已实现安全能力：
- 写接口鉴权强制（Bearer/API Key）
- 角色级授权（admin/reviewer/publisher）
- 发布/状态变更/下架/黑名单操作写入审计日志
- 黑名单与下架对检索/安装可见性生效

建议在生产环境额外启用：
1. 将 `OWLHUB_AUTH_SECRET`、数据库/Redis 凭证托管到 Secret 管理系统。
2. 在 Ingress/API Gateway 层增加 WAF 与全局限流策略。
3. 为 `api/v1/auth/*` 与管理端点增加更严格的 IP/来源访问控制。
4. 审计日志接入集中式日志系统并配置不可篡改归档策略。

## 9. Python API Client 示例

### 9.1 通过 CLI 统一客户端搜索与发布

```python
from pathlib import Path

from owlclaw.cli.api_client import SkillHubApiClient
from owlclaw.owlhub import OwlHubClient

index_client = OwlHubClient(
    index_url="./index.json",
    install_dir=Path("./.owlhub/skills"),
    lock_file=Path("./skill-lock.json"),
)

client = SkillHubApiClient(
    index_client=index_client,
    api_base_url="http://localhost:8000",
    api_token="<bearer-token>",
    mode="api",
)

results = client.search(query="monitor")
print([(item.name, item.version) for item in results])

resp = client.publish(skill_path=Path("./my-skill"))
print(resp)
```

### 9.2 使用原生 HTTP 调用查询接口

```python
import requests

base = "http://localhost:8000"
token = "<bearer-token>"

search = requests.get(f"{base}/api/v1/skills", params={"query": "monitor"}, timeout=10)
print(search.json())

headers = {"Authorization": f"Bearer {token}"}
pending = requests.get(f"{base}/api/v1/reviews/pending", headers=headers, timeout=10)
print(pending.status_code, pending.json())
```
