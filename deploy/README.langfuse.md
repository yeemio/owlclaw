# 本地启动 Langfuse（用于集成测试与开发）

Task 9.2 的 Langfuse 集成测试需要本地运行 Langfuse 并在 `.env` 中配置 API 密钥。

## 1. 启动 Langfuse 服务

### 方式 A：使用官方 Docker Compose（推荐）

```bash
# 在任意目录克隆 Langfuse 仓库
git clone https://github.com/langfuse/langfuse.git
cd langfuse

# 可选：修改 docker-compose.yml 中的 # CHANGEME 密码（生产建议修改）
# 若本机 5432 已被占用（如 OwlClaw 的 postgres），可把 postgres ports 改为 "127.0.0.1:5433:5432"

docker compose up -d

# 等待约 2–3 分钟，直到 langfuse-web 日志出现 "Ready"
docker compose logs -f langfuse-web
```

访问 **http://localhost:3000**，首次使用需在 UI 中注册/登录并创建项目。

### 方式 B：使用脚本（克隆并启动）

在项目根目录执行：

```bash
# Linux/macOS
./deploy/start-langfuse.sh

# 或手动执行脚本内命令
```

## 2. 获取 API 密钥

1. 打开 http://localhost:3000
2. 登录后进入项目（或新建项目）
3. 进入 **Settings → API Keys**，创建新的 API Key
4. 复制 **Public Key** 和 **Secret Key**

## 3. 配置 .env（API 密钥位置）

在 **OwlClaw 项目根目录** 创建或编辑 `.env`（与 `tests/conftest.py` 加载路径一致）。若不知道放哪，就在项目根目录新建 `.env` 文件：

```env
# Langfuse（自建时 host 为本地）
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

# 真实 API 测试（Task 9.1）可选
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## 4. 运行集成测试

```bash
# 运行 LLM 集成测试（含 9.1 真实 API、9.2 Langfuse）
poetry run pytest tests/integration/test_llm_integration.py -v

# 仅运行 Langfuse 相关
poetry run pytest tests/integration/test_llm_integration.py -k langfuse -v
```

未设置对应环境变量时，相关用例会自动 `pytest.skip`。

## 5. 若拉取镜像失败（cgr.dev / 网络超时）

官方 compose 使用 `cgr.dev/chainguard/minio`，在国内或受限网络下可能拉不到。项目已在 `.langfuse` 下放了 **docker-compose.override.yml**，把 MinIO 换成 Docker Hub 的 `minio/minio`，compose 会自动合并。

在 `.langfuse` 目录直接执行即可：

```bash
cd D:\AI\owlclaw\.langfuse
docker compose up -d
```

若仍有镜像拉取失败，可重试 `docker compose pull` 或检查代理/DNS（Docker Desktop → Settings → Resources / Docker Engine）。

**若错误里出现 `dockerhub.icu` 或其它镜像站且报 EOF/context canceled**：说明 Docker 在用镜像加速，该源不可用。可临时关掉镜像加速，改直连 Docker Hub 再拉：

1. 打开 **Docker Desktop** → **Settings** → **Docker Engine**。
2. 在 JSON 里找到 `"registry-mirrors": ["https://dockerhub.icu", ...]`（或类似项），删掉整行或改为 `[]`。
3. 点 **Apply & restart**，再在 `.langfuse` 下执行 `docker compose pull`、`docker compose up -d`。

**若去掉镜像后直连 `registry-1.docker.io` 超时**（dial tcp ... connectex: connection failed / did not properly respond）：说明本机网络访问 Docker Hub 受限，需要改回**可用的镜像加速**。在 Docker Engine 的 JSON 里配置一个当前可用的镜像，例如：

- `https://docker.m.daocloud.io`
- `https://docker.xuanyuan.me`

例如：`"registry-mirrors": ["https://docker.m.daocloud.io"]`，保存后 Apply & restart，再重试 `docker compose pull`。镜像站可能随政策变化，若失效可搜索「Docker Hub 镜像加速 当前可用」换用其它地址。

## 6. 端口与冲突

- Langfuse 默认占用：**3000**（Web）、**5432**（Postgres）、6379（Redis）、8123/9000（Clickhouse）、9090（MinIO）。
- 若已使用 `deploy/docker-compose.lite.yml` 占用 5432，可修改 Langfuse 的 `postgres.ports` 为 `127.0.0.1:5433:5432`，其它服务仅绑定 127.0.0.1，一般无冲突。
