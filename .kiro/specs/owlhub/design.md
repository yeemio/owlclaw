# Design Document: Skills 注册中心（OwlHub）

## 文档联动

- requirements: `.kiro/specs/owlhub/requirements.md`
- design: `.kiro/specs/owlhub/design.md`
- tasks: `.kiro/specs/owlhub/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**: 建立 Skills 注册、发布与发现机制，支持 OwlHub 生态  
> **状态**: 设计中  
> **最后更新**: 2025-02-22

---

## Overview

OwlHub 是 OwlClaw Skills 的注册、发现与分发中心，负责维护技能索引、版本管理、发布流程与审核策略，并为 CLI 提供搜索、安装、更新与统计能力。OwlHub 采用渐进式架构演进策略，从轻量级的 GitHub 索引模式开始，逐步演进到静态站点，最终发展为完整的服务化 API。

核心能力：
- 技能发布与语义化版本管理
- 技能索引与多维度搜索（name/keyword/tag）
- CLI 安装、更新与版本锁定
- 元数据与规范自动校验
- 发布者身份验证与签名机制
- 下载统计与活跃度追踪
- 审核流程与生态治理
- 渐进式架构演进（GitHub → 静态站点 → 服务 API）

设计原则：
- 早期阶段避免复杂服务依赖
- 遵循 Agent Skills 规范
- 保持阶段间向后兼容
- 优先支持自动化校验与审核
- 提供清晰的迁移路径

## 架构例外声明（实现阶段需固化）

为保证设计与实现的一致性，以下例外在本 spec 中显式声明，并要求在 Alembic 迁移与实现注释中同步固化：

1. `skill_statistics` 使用 `date DATE NOT NULL` 作为日粒度统计键，不使用 `TIMESTAMPTZ`。
   - 原因：该表承载按天聚合结果，`DATE` 可避免时区换算导致的重复/遗漏统计窗口问题。
   - 约束：事件明细若需追踪时间线，必须写入 `TIMESTAMPTZ` 字段的明细表，不得复用聚合表代替审计日志。
2. Phase 1/2 可使用静态索引文件（`index.json`）作为发布介质，Phase 3 才引入服务化 API 与数据库。
   - 原因：遵循架构的渐进式演进策略，优先降低早期运行复杂度。
   - 约束：阶段迁移必须保持向后兼容，并在任务中提供迁移与回滚步骤。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表的 `tenant_id/UUID` 约束。

除上述显式例外外，进入数据库阶段（Phase 3）的业务表仍严格遵循数据库五条铁律（`tenant_id`、`TIMESTAMPTZ`、索引前缀、Alembic 管理）。

---

## Architecture

### 整体架构

OwlHub 采用三阶段渐进式架构：

```
Phase 1: GitHub 索引模式
┌─────────────────────────────────────────────────────────────┐
│                    Publisher Repositories                    │
│  (GitHub repos with SKILL.md + skill files)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Index Builder                            │
│  (Crawls repos, validates, generates index.json)             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Static Index (index.json)                   │
│  (Hosted on GitHub Pages or CDN)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI Client                              │
│  (Reads index.json, installs skills)                         │
└─────────────────────────────────────────────────────────────┘


Phase 2: 静态站点模式
┌─────────────────────────────────────────────────────────────┐
│                    Publisher Repositories                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Index Builder                            │
│  (Enhanced with statistics, search index)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Static Site Generator                      │
│  (Generates HTML pages, search index, RSS feed)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Static Site (GitHub Pages)                  │
│  (Browse UI, search, skill details, statistics)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI Client                              │
│  (Compatible with Phase 1 index format)                      │
└─────────────────────────────────────────────────────────────┘

Phase 3: 服务化 API 模式
┌─────────────────────────────────────────────────────────────┐
│                    Publisher Repositories                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     OwlHub API Service                       │
│  ┌──────────────┬──────────────┬──────────────────────────┐ │
│  │ Registry API │ Statistics   │ Authentication           │ │
│  │              │ Tracker      │ & Authorization          │ │
│  └──────────────┴──────────────┴──────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Database (PostgreSQL)                    │   │
│  │  - Skills metadata                                    │   │
│  │  - Versions & history                                 │   │
│  │  - Download statistics                                │   │
│  │  - Review records                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLI Client                              │
│  (Uses API endpoints, backward compatible)                   │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 组件 1: Index Builder（索引构建器）

**职责**: 抓取技能仓库，校验规范，生成标准索引。

**阶段演进**:
- Phase 1: 基础索引生成（JSON 格式）
- Phase 2: 增强统计信息、搜索索引
- Phase 3: 实时索引更新、webhook 触发

**主要功能**:
- 从配置的仓库列表抓取技能
- 解析 SKILL.md frontmatter
- 校验目录结构与必要文件
- 生成统一的索引格式
- 计算哈希值用于完整性验证

#### 组件 2: Validator（校验器）

**职责**: 校验技能包的规范性与完整性。

**校验规则**:
- SKILL.md frontmatter 必填字段
- 语义化版本号格式
- 目录结构完整性
- 依赖声明有效性
- 文件大小限制

#### 组件 3: Registry API（注册 API）

**职责**: 提供技能搜索、详情、版本管理接口。

**阶段演进**:
- Phase 1: 无（直接读取 index.json）
- Phase 2: 静态 JSON API
- Phase 3: 动态 REST API

**主要端点**:
- `GET /skills` - 搜索技能
- `GET /skills/{name}` - 获取技能详情
- `GET /skills/{name}/versions` - 获取版本列表
- `POST /skills` - 发布新技能（Phase 3）
- `PUT /skills/{name}/versions/{version}` - 更新版本状态（Phase 3）

#### 组件 4: CLI Client（CLI 客户端）

**职责**: 提供命令行工具用于搜索、安装、更新技能。

**主要命令**:
- `owlclaw skill search <query>` - 搜索技能
- `owlclaw skill install <name>[@version]` - 安装技能
- `owlclaw skill update [name]` - 更新技能
- `owlclaw skill list` - 列出已安装技能
- `owlclaw skill validate <path>` - 本地校验技能包

#### 组件 5: Statistics Tracker（统计追踪器）

**职责**: 记录下载量、安装量、活跃度等指标。

**阶段演进**:
- Phase 1: 无统计
- Phase 2: 基于 GitHub API 的下载统计
- Phase 3: 完整的统计数据库

#### 组件 6: Review System（审核系统）

**职责**: 管理技能审核流程。

**阶段演进**:
- Phase 1: 手动审核（PR review）
- Phase 2: 自动化校验 + 手动审核
- Phase 3: 完整的审核工作流（提交、审核、申诉）

---

## Components and Interfaces


### Component 1: Index Builder

**职责**: 抓取技能仓库，校验规范，生成标准索引。

**接口定义**:
```python
@dataclass
class SkillManifest:
    name: str
    version: str
    publisher: str
    description: str
    tags: List[str]
    dependencies: Dict[str, str]  # skill_name -> version_constraint
    repository: str
    homepage: Optional[str]
    license: str
    authors: List[str]
    
@dataclass
class IndexEntry:
    manifest: SkillManifest
    download_url: str
    checksum: str  # SHA256
    published_at: datetime
    updated_at: datetime
    version_state: VersionState  # DRAFT, RELEASED, DEPRECATED
    
class IndexBuilder:
    def __init__(self, config: IndexConfig):
        self.config = config
        self.validator = Validator()
        
    def build_index(self, repo_list: List[str]) -> Index:
        """构建完整索引"""
        
    def crawl_repository(self, repo_url: str) -> List[SkillManifest]:
        """抓取单个仓库的技能"""
        
    def validate_skill(self, skill_path: Path) -> ValidationResult:
        """校验技能包"""
        
    def calculate_checksum(self, skill_path: Path) -> str:
        """计算技能包哈希值"""
```

**实现细节**:
- 使用 GitHub API 抓取仓库内容
- 解析 SKILL.md 的 YAML frontmatter
- 使用 `hashlib.sha256()` 计算文件哈希
- 生成 JSON 格式的索引文件
- 支持增量更新（仅处理变更的仓库）

### Component 2: Validator

**职责**: 校验技能包的规范性与完整性。

**接口定义**:
```python
@dataclass
class ValidationError:
    field: str
    message: str
    severity: Severity  # ERROR, WARNING
    
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    
class Validator:
    def validate_manifest(self, manifest: SkillManifest) -> ValidationResult:
        """校验技能清单"""
        
    def validate_version(self, version: str) -> bool:
        """校验语义化版本号"""
        
    def validate_structure(self, skill_path: Path) -> ValidationResult:
        """校验目录结构"""
        
    def validate_dependencies(self, dependencies: Dict[str, str]) -> ValidationResult:
        """校验依赖声明"""
```

**校验规则**:

必填字段校验：
- `name`: 必填，格式 `^[a-z0-9-]+$`
- `version`: 必填，符合语义化版本号（semver）
- `publisher`: 必填，格式 `^[a-z0-9-]+$`
- `description`: 必填，长度 10-500 字符
- `license`: 必填，有效的 SPDX 标识符

版本号校验：
- 格式: `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`
- 示例: `1.0.0`, `1.0.0-alpha.1`, `1.0.0+20250222`

目录结构校验：
```
skill-name/
├── SKILL.md          # 必需
├── README.md         # 可选
├── scripts/          # 可选
│   └── *.py
├── configs/          # 可选
│   └── *.yaml
└── tests/            # 推荐
    └── test_*.py
```

依赖校验：
- 依赖的技能必须存在于索引中
- 版本约束格式: `^1.0.0`, `>=1.0.0,<2.0.0`, `~1.2.3`

### Component 3: Registry API

**职责**: 提供技能搜索、详情、版本管理接口。

**Phase 1 接口（静态 JSON）**:
```json
// GET /index.json
{
  "version": "1.0",
  "generated_at": "2025-02-22T10:00:00Z",
  "skills": [
    {
      "name": "entry-monitor",
      "publisher": "acme",
      "latest_version": "1.2.0",
      "description": "Monitor trading entries",
      "tags": ["trading", "monitor"],
      "repository": "https://github.com/acme/entry-monitor",
      "versions": [
        {
          "version": "1.2.0",
          "download_url": "https://github.com/acme/entry-monitor/archive/v1.2.0.tar.gz",
          "checksum": "sha256:abc123...",
          "published_at": "2025-02-20T10:00:00Z",
          "state": "released"
        }
      ]
    }
  ]
}
```

**Phase 3 接口（REST API）**:
```python
class RegistryAPI:
    @app.get("/api/v1/skills")
    async def search_skills(
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: SortBy = SortBy.DOWNLOADS,
        page: int = 1,
        page_size: int = 20
    ) -> SkillSearchResponse:
        """搜索技能"""
        
    @app.get("/api/v1/skills/{publisher}/{name}")
    async def get_skill_detail(
        publisher: str,
        name: str
    ) -> SkillDetail:
        """获取技能详情"""
        
    @app.get("/api/v1/skills/{publisher}/{name}/versions")
    async def list_versions(
        publisher: str,
        name: str
    ) -> List[VersionInfo]:
        """列出所有版本"""
        
    @app.post("/api/v1/skills")
    async def publish_skill(
        skill: SkillManifest,
        auth: AuthToken
    ) -> PublishResponse:
        """发布新技能"""
        
    @app.put("/api/v1/skills/{publisher}/{name}/versions/{version}/state")
    async def update_version_state(
        publisher: str,
        name: str,
        version: str,
        state: VersionState,
        auth: AuthToken
    ) -> UpdateResponse:
        """更新版本状态"""
```

### Component 4: CLI Client

**职责**: 提供命令行工具用于搜索、安装、更新技能。

**接口定义**:
```python
class CLIClient:
    def __init__(self, config: CLIConfig):
        self.config = config
        self.index_url = config.index_url
        self.install_dir = config.install_dir
        
    def search(self, query: str, tags: List[str] = None) -> List[SkillSummary]:
        """搜索技能"""
        
    def install(self, name: str, version: Optional[str] = None) -> InstallResult:
        """安装技能"""
        
    def update(self, name: Optional[str] = None) -> UpdateResult:
        """更新技能（不指定 name 则更新全部）"""
        
    def list_installed(self) -> List[InstalledSkill]:
        """列出已安装技能"""
        
    def validate_local(self, path: Path) -> ValidationResult:
        """本地校验技能包"""
```

**命令行接口**:
```bash
# 搜索技能
owlclaw skill search "trading monitor"
owlclaw skill search --tag trading --tag monitor

# 安装技能
owlclaw skill install entry-monitor
owlclaw skill install entry-monitor@1.2.0
owlclaw skill install entry-monitor@^1.0.0

# 更新技能
owlclaw skill update entry-monitor
owlclaw skill update  # 更新所有

# 列出已安装
owlclaw skill list
owlclaw skill list --outdated

# 本地校验
owlclaw skill validate ./my-skill/

# 生成 lock 文件
owlclaw skill lock
```

**安装流程**:
1. 从索引查找技能和版本
2. 下载技能包（tar.gz）
3. 验证 checksum
4. 解压到安装目录
5. 校验技能包结构
6. 更新 lock 文件
7. 注册到本地索引

### Component 5: Statistics Tracker

**职责**: 记录下载量、安装量、活跃度等指标。

**接口定义**:
```python
@dataclass
class SkillStatistics:
    skill_name: str
    publisher: str
    total_downloads: int
    downloads_last_30d: int
    total_installs: int
    active_installs: int  # 最近 30 天有使用
    last_updated: datetime
    
class StatisticsTracker:
    def record_download(self, skill_name: str, version: str):
        """记录下载事件"""
        
    def record_install(self, skill_name: str, version: str, user_id: str):
        """记录安装事件"""
        
    def get_statistics(self, skill_name: str) -> SkillStatistics:
        """获取统计数据"""
        
    def export_statistics(self, format: ExportFormat) -> bytes:
        """导出统计数据"""
```

**阶段实现**:
- Phase 1: 无统计
- Phase 2: 基于 GitHub Release 下载数统计
- Phase 3: 完整的事件追踪与数据库存储

### Component 6: Review System

**职责**: 管理技能审核流程。

**接口定义**:
```python
@dataclass
class ReviewRecord:
    skill_name: str
    version: str
    reviewer: str
    status: ReviewStatus  # PENDING, APPROVED, REJECTED
    comments: str
    reviewed_at: datetime
    
class ReviewSystem:
    def submit_for_review(self, skill: SkillManifest) -> ReviewRecord:
        """提交审核"""
        
    def approve(self, skill_name: str, version: str, reviewer: str) -> ReviewRecord:
        """批准发布"""
        
    def reject(self, skill_name: str, version: str, reviewer: str, reason: str) -> ReviewRecord:
        """拒绝发布"""
        
    def appeal(self, skill_name: str, version: str, reason: str) -> AppealRecord:
        """提交申诉"""
```

**审核流程**:
1. 自动校验（Validator）
2. 安全扫描（可选）
3. 人工审核（Phase 2+）
4. 批准/拒绝
5. 申诉处理（如果被拒绝）

---

## Data Models


### Index Schema

索引文件格式（index.json）：

```json
{
  "version": "1.0",
  "generated_at": "2025-02-22T10:00:00Z",
  "total_skills": 42,
  "skills": [
    {
      "name": "entry-monitor",
      "publisher": "acme",
      "latest_version": "1.2.0",
      "description": "Monitor trading entries and alert on conditions",
      "tags": ["trading", "monitor", "alert"],
      "repository": "https://github.com/acme/entry-monitor",
      "homepage": "https://acme.com/skills/entry-monitor",
      "license": "MIT",
      "authors": ["Alice <alice@acme.com>"],
      "versions": [
        {
          "version": "1.2.0",
          "download_url": "https://github.com/acme/entry-monitor/archive/v1.2.0.tar.gz",
          "checksum": "sha256:abc123def456...",
          "published_at": "2025-02-20T10:00:00Z",
          "updated_at": "2025-02-20T10:00:00Z",
          "state": "released",
          "dependencies": {
            "market-data": "^2.0.0"
          }
        },
        {
          "version": "1.1.0",
          "download_url": "https://github.com/acme/entry-monitor/archive/v1.1.0.tar.gz",
          "checksum": "sha256:def456abc789...",
          "published_at": "2025-01-15T10:00:00Z",
          "updated_at": "2025-01-15T10:00:00Z",
          "state": "released",
          "dependencies": {
            "market-data": "^1.0.0"
          }
        }
      ],
      "statistics": {
        "total_downloads": 1250,
        "downloads_last_30d": 320,
        "last_updated": "2025-02-20T10:00:00Z"
      }
    }
  ]
}
```

### SKILL.md Frontmatter Schema

技能清单格式（SKILL.md frontmatter）：

```yaml
---
name: entry-monitor
version: 1.2.0
publisher: acme
description: Monitor trading entries and alert on conditions
tags:
  - trading
  - monitor
  - alert
repository: https://github.com/acme/entry-monitor
homepage: https://acme.com/skills/entry-monitor
license: MIT
authors:
  - Alice <alice@acme.com>
dependencies:
  market-data: ^2.0.0
---

# Entry Monitor Skill

详细的技能说明文档...
```

### Lock File Schema

版本锁定文件（skill-lock.json）：

```json
{
  "version": "1.0",
  "generated_at": "2025-02-22T10:00:00Z",
  "skills": {
    "entry-monitor": {
      "version": "1.2.0",
      "resolved": "https://github.com/acme/entry-monitor/archive/v1.2.0.tar.gz",
      "checksum": "sha256:abc123def456...",
      "dependencies": {
        "market-data": {
          "version": "2.1.0",
          "resolved": "https://github.com/acme/market-data/archive/v2.1.0.tar.gz",
          "checksum": "sha256:xyz789..."
        }
      }
    }
  }
}
```

### Database Schema (Phase 3)

```sql
-- 技能表
CREATE TABLE skills (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    name VARCHAR(255) NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    repository VARCHAR(500) NOT NULL,
    homepage VARCHAR(500),
    license VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, publisher, name)
);

-- 版本表
CREATE TABLE skill_versions (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    skill_id UUID NOT NULL REFERENCES skills(id),
    version VARCHAR(50) NOT NULL,
    download_url VARCHAR(500) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'draft',
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, skill_id, version)
);

-- 统计表
CREATE TABLE skill_statistics (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    skill_id UUID NOT NULL REFERENCES skills(id),
    date DATE NOT NULL,
    downloads INTEGER NOT NULL DEFAULT 0,
    installs INTEGER NOT NULL DEFAULT 0,
    UNIQUE(tenant_id, skill_id, date)
);

-- 审核记录表
CREATE TABLE review_records (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    skill_id UUID NOT NULL REFERENCES skills(id),
    version_id UUID NOT NULL REFERENCES skill_versions(id),
    reviewer VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    comments TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_skills_tenant_publisher_name ON skills (tenant_id, publisher, name);
CREATE INDEX idx_skill_versions_tenant_skill_version ON skill_versions (tenant_id, skill_id, version);
CREATE INDEX idx_skill_statistics_tenant_skill_date ON skill_statistics (tenant_id, skill_id, date);
CREATE INDEX idx_review_records_tenant_skill_version ON review_records (tenant_id, skill_id, version_id);
```

---
## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

经过对所有验收标准的分析，我识别出以下冗余区域并进行了合并：

1. **版本管理属性**: 需求 1.1-1.4 都涉及版本管理，可以合并为综合的版本管理属性
2. **搜索功能**: 需求 2.1 和 2.2 可以合并为一个综合的搜索属性
3. **安装功能**: 需求 3.1 和 3.2 都是关于安装，可以合并
4. **校验功能**: 需求 4.1-4.4 都涉及校验，可以合并为综合的校验属性
5. **统计功能**: 需求 6.1-6.3 都涉及统计，可以合并

以下属性代表唯一的、非冗余的验证需求：

### Property 1: 版本发布与检索

*对于任何*有效的技能版本，发布后应该能够从索引中检索到该版本的完整信息。

**Validates: Requirements 1.1**

### Property 2: 语义化版本号验证

*对于任何*版本号字符串，系统应该正确识别有效的语义化版本号（MAJOR.MINOR.PATCH 格式）并拒绝无效格式。

**Validates: Requirements 1.2**

### Property 3: 版本历史不变性

*对于任何*技能，发布多个版本后，所有历史版本应该保持可访问且不被修改或删除。

**Validates: Requirements 1.3**

### Property 4: 版本状态管理

*对于任何*技能版本，设置状态（draft/released/deprecated）后，查询该版本应该返回正确的状态。

**Validates: Requirements 1.4**

### Property 5: 必填字段验证

*对于任何*缺少必填字段（name, version, publisher, description, license）的技能清单，系统应该拒绝发布并返回明确的错误信息。

**Validates: Requirements 1.5**

### Property 6: 多维度搜索

*对于任何*搜索查询（按 name/keyword/tag），搜索结果应该只包含匹配查询条件的技能，并按指定方式排序（下载量/更新时间）。

**Validates: Requirements 2.1, 2.2**

### Property 7: 技能详情完整性

*对于任何*技能，获取详情时应该包含所有必要信息（名称、版本、描述、依赖、统计数据）。

**Validates: Requirements 2.3**

### Property 8: 分页一致性

*对于任何*搜索结果集，使用不同的分页参数（page, page_size）遍历所有页面，应该得到完整且不重复的结果集。

**Validates: Requirements 2.4**

### Property 9: 技能安装正确性

*对于任何*有效的技能名称和版本号，安装后应该在安装目录中创建正确的文件结构，且文件内容与源仓库一致（通过 checksum 验证）。

**Validates: Requirements 3.1, 3.2**

### Property 10: 版本更新检测

*对于任何*已安装的技能，如果索引中存在更新版本，更新命令应该检测到并安装最新版本。

**Validates: Requirements 3.3**

### Property 11: Lock 文件一致性

*对于任何*安装的技能集合，生成的 lock 文件应该准确记录所有已安装技能的版本和 checksum，重新安装应该得到完全相同的版本。

**Validates: Requirements 3.4**

### Property 12: 校验失败拒绝

*对于任何*校验失败的技能包（无效的 frontmatter、缺失文件、无效依赖），安装命令应该拒绝安装并保持系统状态不变。

**Validates: Requirements 3.5**

### Property 13: 规范校验完整性

*对于任何*技能包，校验器应该检查所有规范要求（frontmatter 格式、必填字段、目录结构、依赖有效性），并生成包含所有错误和警告的报告。

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 14: 身份验证保护

*对于任何*未经身份验证的发布请求（Phase 3），系统应该拒绝并返回 401 Unauthorized 错误。

**Validates: Requirements 5.1**

### Property 15: 发布审计日志

*对于任何*成功的技能发布操作，系统应该记录发布者身份、时间戳和变更内容到审计日志。

**Validates: Requirements 5.2**

### Property 16: Checksum 完整性验证

*对于任何*技能包，计算 checksum → 下载 → 重新计算 checksum 应该得到相同的哈希值，验证文件完整性。

**Validates: Requirements 5.3**

### Property 17: 黑名单过滤

*对于任何*被加入黑名单的技能，搜索结果和安装命令都不应该返回或允许安装该技能。

**Validates: Requirements 5.4**

### Property 18: 统计计数准确性

*对于任何*技能，执行 N 次下载/安装操作后，统计 API 返回的计数应该准确反映操作次数（允许短暂延迟）。

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 19: 统计数据导出完整性

*对于任何*导出的统计数据，应该包含所有技能的完整统计信息，且格式符合指定的 schema。

**Validates: Requirements 6.4**

### Property 20: 审核状态转换

*对于任何*提交审核的技能，审核流程应该正确记录状态转换（pending → approved/rejected），且每次转换都有审核记录。

**Validates: Requirements 7.1, 7.4**

### Property 21: 标签分类检索

*对于任何*设置了标签的技能，应该能够通过标签进行检索和过滤。

**Validates: Requirements 7.2**

### Property 22: 下架技能隐藏

*对于任何*被下架或冻结的技能，公开索引和搜索结果中不应该显示该技能，但已安装的用户仍可继续使用。

**Validates: Requirements 7.3**

### Property 23: 申诉记录保存

*对于任何*提交的申诉，系统应该保存申诉内容、时间戳和处理结果。

**Validates: Requirements 7.5**

### Property 24: GitHub 索引格式正确性

*对于任何*生成的 GitHub 索引文件（index.json），应该符合定义的 JSON schema 且包含所有必要字段。

**Validates: Requirements 8.1**

### Property 25: 静态站点索引可访问性

*对于任何*发布到静态站点的索引，CLI 客户端应该能够成功下载并解析索引文件。

**Validates: Requirements 8.2**

### Property 26: 阶段间向后兼容性

*对于任何*使用 Phase 1 索引格式的 CLI 客户端，应该能够成功读取 Phase 2 和 Phase 3 提供的索引数据（通过兼容层）。

**Validates: Requirements 8.4**

---
## Error Handling

### Error Categories

#### 1. 网络错误

**场景**:
- 无法连接到索引服务器
- 下载超时
- DNS 解析失败

**处理策略**:
```python
try:
    response = requests.get(index_url, timeout=30)
    response.raise_for_status()
except requests.ConnectionError:
    logger.error(f"Cannot connect to {index_url}")
    raise IndexUnavailableError("Index server is unreachable")
except requests.Timeout:
    logger.error(f"Timeout connecting to {index_url}")
    raise IndexUnavailableError("Index server timeout")
```

#### 2. 校验错误

**场景**:
- 无效的版本号格式
- 缺失必填字段
- 目录结构不完整
- 依赖不存在

**处理策略**:
```python
validation_result = validator.validate_manifest(manifest)
if not validation_result.is_valid:
    error_messages = [e.message for e in validation_result.errors]
    raise ValidationError(
        f"Skill validation failed: {', '.join(error_messages)}"
    )
```

#### 3. 完整性错误

**场景**:
- Checksum 不匹配
- 下载的文件损坏
- 签名验证失败

**处理策略**:
```python
calculated_checksum = calculate_checksum(downloaded_file)
if calculated_checksum != expected_checksum:
    logger.error(
        f"Checksum mismatch: expected {expected_checksum}, "
        f"got {calculated_checksum}"
    )
    os.remove(downloaded_file)
    raise IntegrityError("Downloaded file is corrupted")
```

#### 4. 权限错误

**场景**:
- 无法写入安装目录
- 无法创建配置文件
- 无权限访问仓库

**处理策略**:
```python
try:
    os.makedirs(install_dir, exist_ok=True)
except PermissionError:
    logger.error(f"No permission to create {install_dir}")
    raise InstallError(
        f"Cannot create install directory: {install_dir}. "
        "Try running with sudo or change install location."
    )
```

#### 5. 依赖冲突

**场景**:
- 依赖版本冲突
- 循环依赖
- 依赖不存在

**处理策略**:
```python
def resolve_dependencies(skill: SkillManifest) -> List[SkillManifest]:
    """解析依赖关系"""
    resolved = []
    visited = set()
    
    def visit(s: SkillManifest):
        if s.name in visited:
            raise DependencyError(f"Circular dependency detected: {s.name}")
        visited.add(s.name)
        
        for dep_name, version_constraint in s.dependencies.items():
            dep_skill = find_skill(dep_name, version_constraint)
            if not dep_skill:
                raise DependencyError(
                    f"Dependency not found: {dep_name} {version_constraint}"
                )
            visit(dep_skill)
            resolved.append(dep_skill)
    
    visit(skill)
    return resolved
```

### Error Recovery Strategy

1. **网络错误**: 重试 3 次，使用指数退避
2. **校验错误**: 立即失败，提供详细错误信息
3. **完整性错误**: 删除损坏文件，重新下载
4. **权限错误**: 提供明确的解决建议
5. **依赖冲突**: 提供冲突详情和可能的解决方案

### Error Messages

错误消息应该包含：
- 清晰的错误描述
- 错误发生的上下文
- 可能的原因
- 建议的解决方案

示例：
```
Error: Failed to install skill 'entry-monitor@1.2.0'

Reason: Checksum verification failed
Expected: sha256:abc123def456...
Got:      sha256:xyz789abc123...

Possible causes:
  - File was corrupted during download
  - Index file contains incorrect checksum
  - Network connection is unstable

Suggested actions:
  1. Try installing again: owlclaw skill install entry-monitor@1.2.0
  2. Clear cache: owlclaw skill cache clear
  3. Report issue: https://github.com/owlclaw/owlhub/issues
```

---

## Testing Strategy

### Dual Testing Approach

测试策略结合单元测试和基于属性的测试，以实现全面覆盖：

**单元测试**: 专注于特定示例、集成点和边界情况
**属性测试**: 通过随机化输入验证通用属性

### Unit Testing

单元测试验证特定场景和边界情况：

**Index Builder Tests**:
- 构建空仓库列表的索引（预期：空索引）
- 构建包含单个技能的索引
- 构建包含多个版本的技能索引
- 处理无效的 SKILL.md frontmatter
- 处理缺失的必要文件

**Validator Tests**:
- 验证有效的语义化版本号（1.0.0, 1.2.3-alpha.1）
- 拒绝无效的版本号（1.0, v1.0.0, 1.0.0.0）
- 验证必填字段存在性
- 验证字段格式（name 只能包含小写字母、数字、连字符）
- 验证依赖版本约束格式

**CLI Client Tests**:
- 搜索不存在的技能（预期：空结果）
- 安装已存在的技能（预期：提示已安装）
- 安装不存在的版本（预期：错误）
- 更新无可用更新的技能（预期：提示已是最新）
- 生成 lock 文件并验证格式

**Statistics Tracker Tests**:
- 记录下载事件并验证计数增加
- 记录多个事件并验证累计计数
- 导出统计数据并验证 JSON 格式
- 处理并发下载事件

**Review System Tests**:
- 提交审核并验证状态为 PENDING
- 批准审核并验证状态变为 APPROVED
- 拒绝审核并验证状态变为 REJECTED
- 提交申诉并验证记录保存

### Property-Based Testing

属性测试通过随机化输入验证通用正确性属性。每个测试应运行最少 100 次迭代。

**测试库**: 使用 Python 的 `hypothesis` 库进行基于属性的测试

**测试配置**:
```python
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(max_examples=100)
@given(st.text())
def test_property(input_data):
    # Feature: owlhub, Property 1: 版本发布与检索
    ...
```

**Property Test Cases**:

1. **版本发布与检索** (Property 1)
   - 生成随机的有效技能清单
   - 发布到索引
   - 验证可以从索引检索到完整信息

2. **语义化版本号验证** (Property 2)
   - 生成各种版本号字符串（有效和无效）
   - 验证校验器正确识别

3. **版本历史不变性** (Property 3)
   - 生成随机技能并发布多个版本
   - 验证所有历史版本可访问

4. **版本状态管理** (Property 4)
   - 生成随机版本并设置随机状态
   - 验证查询返回正确状态

5. **必填字段验证** (Property 5)
   - 生成缺少随机必填字段的清单
   - 验证发布被拒绝

6. **多维度搜索** (Property 6)
   - 生成随机技能集合和搜索查询
   - 验证搜索结果匹配且正确排序

7. **技能详情完整性** (Property 7)
   - 生成随机技能
   - 验证详情包含所有必要字段

8. **分页一致性** (Property 8)
   - 生成大量技能
   - 使用不同分页参数遍历
   - 验证结果完整且不重复

9. **技能安装正确性** (Property 9)
   - 生成随机技能包
   - 安装并验证文件结构和 checksum

10. **版本更新检测** (Property 10)
    - 安装旧版本
    - 发布新版本
    - 验证更新命令检测到新版本

11. **Lock 文件一致性** (Property 11)
    - 安装随机技能集合
    - 生成 lock 文件
    - 使用 lock 文件重新安装
    - 验证版本完全一致

12. **校验失败拒绝** (Property 12)
    - 生成无效技能包
    - 验证安装被拒绝且系统状态不变

13. **规范校验完整性** (Property 13)
    - 生成包含多种错误的技能包
    - 验证校验报告包含所有错误

14. **身份验证保护** (Property 14)
    - 发送未认证的发布请求
    - 验证返回 401 错误

15. **发布审计日志** (Property 15)
    - 执行发布操作
    - 验证审计日志包含完整信息

16. **Checksum 完整性验证** (Property 16)
    - 生成随机文件
    - 计算 checksum → 传输 → 重新计算
    - 验证哈希值一致

17. **黑名单过滤** (Property 17)
    - 将随机技能加入黑名单
    - 验证搜索和安装都被阻止

18. **统计计数准确性** (Property 18)
    - 执行随机次数的下载/安装
    - 验证统计计数准确

19. **统计数据导出完整性** (Property 19)
    - 导出统计数据
    - 验证格式和完整性

20. **审核状态转换** (Property 20)
    - 提交审核并执行批准/拒绝
    - 验证状态转换和记录

21. **标签分类检索** (Property 21)
    - 为技能设置随机标签
    - 验证可以通过标签检索

22. **下架技能隐藏** (Property 22)
    - 下架随机技能
    - 验证不出现在公开索引中

23. **申诉记录保存** (Property 23)
    - 提交随机申诉
    - 验证记录被保存

24. **GitHub 索引格式正确性** (Property 24)
    - 生成随机索引
    - 验证符合 JSON schema

25. **静态站点索引可访问性** (Property 25)
    - 发布索引到静态站点
    - 验证 CLI 可以下载和解析

26. **阶段间向后兼容性** (Property 26)
    - 使用 Phase 1 客户端
    - 访问 Phase 2/3 服务
    - 验证兼容性

**Property Test Tags**:
每个属性测试必须包含注释标签：
```python
# Feature: owlhub, Property 16: Checksum 完整性验证
```

### Integration Testing

集成测试验证端到端工作流：

- 完整的发布流程（创建技能 → 校验 → 发布 → 索引更新）
- 完整的安装流程（搜索 → 下载 → 校验 → 安装 → lock 文件）
- 完整的更新流程（检查更新 → 下载 → 安装 → 更新 lock）
- 依赖解析流程（安装带依赖的技能 → 自动安装依赖）
- 审核流程（提交 → 自动校验 → 人工审核 → 批准/拒绝）
- 统计流程（下载 → 记录 → 聚合 → 导出）

### Testing Configuration

**测试覆盖率目标**:
- 整体覆盖率 ≥ 75%
- 核心模块（Validator, IndexBuilder, CLIClient）≥ 85%
- 关键路径（安装、发布）≥ 90%

**测试环境**:
- 使用 pytest 作为测试框架
- 使用 pytest-asyncio 测试异步代码
- 使用 hypothesis 进行属性测试
- 使用 pytest-cov 测量覆盖率
- 使用 pytest-mock 进行 mock

**CI/CD 集成**:
- 每次 PR 自动运行全部测试
- 测试失败阻止合并
- 覆盖率报告自动生成
- 属性测试使用固定种子保证可重现性

---
## Implementation Details

### Phase 1: GitHub 索引模式（2-3 天）

**目标**: 建立最小可用的技能注册中心

**实现步骤**:

1. **Index Builder 实现**
   - 创建 `owlhub/indexer/builder.py`
   - 实现仓库抓取逻辑（使用 GitHub API）
   - 实现 SKILL.md 解析（使用 PyYAML）
   - 实现 checksum 计算（使用 hashlib）
   - 生成 index.json 文件

2. **Validator 实现**
   - 创建 `owlhub/validator/validator.py`
   - 实现版本号校验（正则表达式）
   - 实现必填字段校验
   - 实现目录结构校验
   - 生成校验报告

3. **CLI Client 实现**
   - 创建 `owlclaw/cli/skill.py`
   - 实现 `search` 命令
   - 实现 `install` 命令
   - 实现 `list` 命令
   - 实现 `validate` 命令

4. **索引发布**
   - 设置 GitHub Actions workflow
   - 定期运行 Index Builder
   - 发布 index.json 到 GitHub Pages

**文件结构**:
```
owlhub/
├── indexer/
│   ├── __init__.py
│   ├── builder.py
│   └── crawler.py
├── validator/
│   ├── __init__.py
│   └── validator.py
└── schema/
    ├── __init__.py
    ├── manifest.py
    └── index.py

owlclaw/cli/
└── skill.py
```

**配置文件**:
```yaml
# .owlhub/config.yaml
index_url: https://owlclaw.github.io/owlhub/index.json
repositories:
  - https://github.com/owlclaw-skills/entry-monitor
  - https://github.com/owlclaw-skills/market-data
update_interval: 3600  # seconds
```

### Phase 2: 静态站点模式（3-5 天）

**目标**: 提供 Web UI 和增强的搜索体验

**实现步骤**:

1. **Static Site Generator**
   - 创建 `owlhub/site/generator.py`
   - 使用 Jinja2 生成 HTML 页面
   - 生成搜索索引（使用 lunr.js）
   - 生成 RSS feed

2. **Web UI**
   - 技能列表页面
   - 技能详情页面
   - 搜索页面
   - 统计仪表板

3. **Enhanced Statistics**
   - 从 GitHub API 获取下载统计
   - 计算活跃度指标
   - 生成趋势图表

4. **部署**
   - 使用 GitHub Pages 托管
   - 配置自定义域名
   - 设置 CDN 加速

**技术栈**:
- 静态站点生成: Python + Jinja2
- 前端: HTML + CSS + JavaScript
- 搜索: lunr.js
- 图表: Chart.js

### Phase 3: 服务化 API 模式（5-7 天）

**目标**: 提供完整的服务化能力

**实现步骤**:

1. **API Service**
   - 使用 FastAPI 构建 REST API
   - 实现所有 API 端点
   - 添加 OpenAPI 文档

2. **Database**
   - 使用 PostgreSQL 存储数据
   - 设计数据库 schema
   - 实现 Alembic 迁移

3. **Authentication**
   - 实现 OAuth2 认证
   - 支持 GitHub OAuth
   - 实现 API Key 管理

4. **Statistics Service**
   - 实时统计追踪
   - 数据聚合与分析
   - 统计 API 端点

5. **Review System**
   - 审核工作流实现
   - 审核仪表板
   - 申诉处理

6. **部署**
   - 容器化（Docker）
   - Kubernetes 部署
   - 监控与告警

**技术栈**:
- API 框架: FastAPI
- 数据库: PostgreSQL
- ORM: SQLAlchemy
- 认证: OAuth2 + JWT
- 部署: Docker + Kubernetes

### Migration Path

**Phase 1 → Phase 2**:
- 保持 index.json 格式不变
- 添加统计字段（可选）
- CLI 客户端无需修改

**Phase 2 → Phase 3**:
- 提供 API 兼容层
- 支持静态索引回退
- 逐步迁移客户端到 API

**兼容性保证**:
- 所有阶段支持相同的 index.json 格式
- CLI 客户端自动检测可用的服务类型
- 提供配置选项强制使用特定阶段

---

## Configuration

### Index Builder Configuration

```yaml
# .owlhub/builder-config.yaml
repositories:
  - url: https://github.com/owlclaw-skills/entry-monitor
    branch: main
  - url: https://github.com/owlclaw-skills/market-data
    branch: main

output:
  path: ./dist/index.json
  pretty: true

validation:
  strict: true
  fail_on_warning: false

github:
  token: ${GITHUB_TOKEN}
  api_url: https://api.github.com
```

### CLI Client Configuration

```yaml
# ~/.owlclaw/config.yaml
skill:
  index_url: https://owlclaw.github.io/owlhub/index.json
  install_dir: ~/.owlclaw/skills
  cache_dir: ~/.owlclaw/cache
  lock_file: ./skill-lock.json
  
  # 网络配置
  timeout: 30
  retries: 3
  
  # 校验配置
  verify_checksum: true
  strict_validation: true
```

### Environment Variables

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OWLHUB_INDEX_URL` | 索引地址 | https://owlclaw.github.io/owlhub/index.json |
| `OWLHUB_INSTALL_DIR` | 安装目录 | ~/.owlclaw/skills |
| `OWLHUB_CACHE_DIR` | 缓存目录 | ~/.owlclaw/cache |
| `GITHUB_TOKEN` | GitHub API Token | 无 |
| `OWLHUB_API_URL` | API 服务地址（Phase 3） | 无 |
| `OWLHUB_API_KEY` | API Key（Phase 3） | 无 |

---

## Security Considerations

### 1. 供应链安全

**威胁**: 恶意技能包注入

**缓解措施**:
- 强制 checksum 验证
- 代码签名（Phase 3）
- 自动化安全扫描
- 人工审核流程

### 2. 身份验证

**威胁**: 未授权发布

**缓解措施**:
- GitHub OAuth 认证
- API Key 管理
- 发布者白名单（早期阶段）

### 3. 完整性保护

**威胁**: 中间人攻击、文件篡改

**缓解措施**:
- HTTPS 强制
- SHA256 checksum 验证
- 签名验证（Phase 3）

### 4. 隐私保护

**威胁**: 用户数据泄露

**缓解措施**:
- 最小化数据收集
- 匿名化统计数据
- 遵守 GDPR 要求

### 5. 拒绝服务

**威胁**: 大量请求导致服务不可用

**缓解措施**:
- Rate limiting
- CDN 缓存
- 请求队列

---

## Performance Considerations

### 1. 索引大小

**问题**: 随着技能数量增长，index.json 文件变大

**优化**:
- 分片索引（按分类）
- 增量更新
- 压缩传输（gzip）

### 2. 搜索性能

**问题**: 大量技能时搜索变慢

**优化**:
- 客户端缓存索引
- 服务端搜索索引（Phase 2+）
- 全文搜索引擎（Phase 3）

### 3. 下载速度

**问题**: 大型技能包下载慢

**优化**:
- CDN 加速
- 并行下载
- 断点续传

### 4. 统计性能

**问题**: 实时统计影响性能

**优化**:
- 异步统计记录
- 批量写入
- 定期聚合

---

## Monitoring and Observability

### Metrics

**Index Builder**:
- 索引构建时间
- 处理的仓库数量
- 校验失败数量
- 错误率

**CLI Client**:
- 安装成功率
- 平均安装时间
- 校验失败率
- 网络错误率

**API Service (Phase 3)**:
- 请求 QPS
- 响应时间 P50/P95/P99
- 错误率
- 数据库连接池使用率

### Logging

**日志级别**:
- ERROR: 系统错误、校验失败
- WARNING: 网络重试、降级
- INFO: 操作成功、状态变更
- DEBUG: 详细调试信息

**日志格式**:
```json
{
  "timestamp": "2025-02-22T10:00:00Z",
  "level": "INFO",
  "component": "cli.install",
  "message": "Skill installed successfully",
  "skill_name": "entry-monitor",
  "version": "1.2.0",
  "duration_ms": 1234
}
```

### Alerting

**告警规则**:
- 索引构建失败
- API 错误率 > 5%
- 响应时间 P95 > 1s
- 数据库连接失败

---

## Documentation

### User Documentation

1. **快速开始指南**
   - 安装 CLI
   - 搜索技能
   - 安装第一个技能

2. **CLI 命令参考**
   - 所有命令的详细说明
   - 参数和选项
   - 使用示例

3. **技能开发指南**
   - 创建技能包
   - 编写 SKILL.md
   - 本地测试
   - 发布流程

4. **故障排查**
   - 常见问题
   - 错误消息解释
   - 解决方案

### Developer Documentation

1. **架构文档**
   - 系统架构图
   - 组件交互
   - 数据流

2. **API 文档**
   - OpenAPI 规范
   - 端点说明
   - 认证方式

3. **贡献指南**
   - 开发环境设置
   - 代码规范
   - 提交流程

---

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Agent Skills Specification](../capabilities-skills/requirements.md)
- [OwlClaw Architecture](../../docs/ARCHITECTURE_ANALYSIS.md)
- [Python Packaging User Guide](https://packaging.python.org/)
- [npm Registry API](https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md)

---

**维护者**: 平台研发  
**最后更新**: 2025-02-22
