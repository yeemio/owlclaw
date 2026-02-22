# Design Document: cli-migrate

## 文档联动

- requirements: `.kiro/specs/cli-migrate/requirements.md`
- design: `.kiro/specs/cli-migrate/design.md`
- tasks: `.kiro/specs/cli-migrate/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**: 提供 AI 辅助迁移 CLI，帮助旧项目接入 OwlClaw  
> **状态**: 设计中  
> **最后更新**: 2025-02-22

---

## Overview

cli-migrate 是 OwlClaw 的 AI 辅助迁移工具，旨在帮助已有业务系统（Brownfield）快速接入 OwlClaw 的 AI 自主能力。该工具通过扫描已有项目代码，识别可接入的业务函数和 API，自动生成 OwlClaw 接入代码（@handler 注册）和对应的 SKILL.md 文档（遵循 Agent Skills 规范），从而实现零改造或最小改造接入。

根据 OwlClaw 的核心定位，cli-migrate 是实现"让已有业务系统获得 AI 自主能力"愿景的关键工具，降低业务开发者的接入门槛，使其无需深入学习 AI 框架即可让业务系统"活"起来。

核心能力：
- Python 项目扫描与函数识别（复用 cli-scan）
- OpenAPI 规范解析与 REST API 迁移
- 数据库操作函数识别与事务管理代码生成
- 定时任务（Cron/APScheduler/Celery）迁移
- @handler 注册代码自动生成
- SKILL.md 文档自动生成（遵循 Agent Skills 规范）
- 迁移报告生成（风险评估、优先级建议、工作量预估）
- Dry-run 预览模式
- 交互式迁移向导
- 配置文件支持

---

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLI Layer                                        │
│  (ArgumentParser, Command Handlers, Interactive Wizard)                  │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Migration Engine                                      │
│  (Orchestrates scan → analyze → generate → report)                       │
└────┬────────────┬────────────┬────────────┬────────────┬────────────────┘
     │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Scanner  │ │ Analyzer │ │Generator │ │ Reporter │ │ Config   │
│ Module   │ │ Module   │ │ Module   │ │ Module   │ │ Manager  │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │            │            │
     │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Integration Layer                                   │
│  - cli-scan (AST parsing, function extraction)                           │
│  - OpenAPI parsers (prance, openapi-spec-validator)                      │
│  - Template engine (Jinja2)                                              │
│  - Code formatters (black, autopep8)                                     │
│  - Type checkers (mypy)                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. Scanner Module (扫描器模块)

负责发现和解析项目中的可迁移资源。

主要类：
- `ProjectScanner`: 主扫描器，协调各类资源扫描
- `PythonFunctionScanner`: Python 函数扫描器（复用 cli-scan）
- `OpenAPIScanner`: OpenAPI 规范扫描器
- `CronScanner`: 定时任务扫描器（crontab/APScheduler/Celery）
- `ORMScanner`: ORM 操作扫描器（SQLAlchemy/Django ORM）

#### 2. Analyzer Module (分析器模块)

负责分析扫描结果，评估迁移可行性和风险。

主要类：
- `MigrationAnalyzer`: 主分析器
- `ComplexityAnalyzer`: 复杂度分析器（复用 cli-scan）
- `RiskAssessor`: 风险评估器
- `PriorityRanker`: 优先级排序器
- `DependencyAnalyzer`: 依赖关系分析器（复用 cli-scan）

#### 3. Generator Module (生成器模块)

负责生成 OwlClaw 接入代码和文档。

主要类：
- `CodeGenerator`: 代码生成器基类
- `HandlerGenerator`: @handler 注册代码生成器
- `TriggerGenerator`: Trigger 配置生成器
- `SKILLGenerator`: SKILL.md 文档生成器
- `TemplateSelector`: 模板选择器

#### 4. Reporter Module (报告器模块)

负责生成迁移报告。

主要类：
- `MigrationReporter`: 报告生成器
- `StatisticsCalculator`: 统计计算器
- `RecommendationEngine`: 建议引擎
- `ReportFormatter`: 报告格式化器（Markdown/JSON/PDF）

#### 5. Config Manager (配置管理器)

负责配置文件加载和验证。

主要类：
- `ConfigLoader`: 配置加载器
- `ConfigValidator`: 配置验证器
- `DefaultConfigProvider`: 默认配置提供器

---

## Components and Interfaces

### Component 1: ProjectScanner

**职责**: 协调整个项目扫描流程，发现所有可迁移资源。

**接口定义**:
```python
@dataclass
class ScanConfig:
    project_path: Path
    include_patterns: List[str]
    exclude_patterns: List[str]
    scan_python: bool = True
    scan_openapi: bool = True
    scan_cron: bool = True
    scan_orm: bool = True

@dataclass
class ScanResult:
    python_functions: List[FunctionInfo]  # 来自 cli-scan
    openapi_endpoints: List[APIEndpoint]
    cron_tasks: List[CronTask]
    orm_operations: List[ORMOperation]
    scan_metadata: ScanMetadata
    errors: List[ScanError]

class ProjectScanner:
    def __init__(self, config: ScanConfig):
        self.config = config
        self.python_scanner = PythonFunctionScanner()
        self.openapi_scanner = OpenAPIScanner()
        self.cron_scanner = CronScanner()
        self.orm_scanner = ORMScanner()
    
    def scan(self) -> ScanResult:
        """执行完整项目扫描"""
        
    def scan_incremental(self, previous_result: ScanResult) -> ScanResult:
        """增量扫描（仅扫描变更部分）"""
```

**实现细节**:
- 复用 cli-scan 的 ProjectScanner 进行 Python 函数扫描
- 使用 `prance` 库解析 OpenAPI 规范文件
- 使用正则表达式和 AST 分析识别 cron 任务
- 使用 AST 分析识别 ORM 调用模式

### Component 2: PythonFunctionScanner

**职责**: 扫描 Python 项目中的函数，识别可迁移函数。

**接口定义**:
```python
@dataclass
class MigratableFunction:
    function_info: FunctionInfo  # 来自 cli-scan
    is_migratable: bool
    migration_type: MigrationType  # SIMPLE, NEEDS_REVIEW, COMPLEX
    blocking_issues: List[str]
    recommendations: List[str]

class PythonFunctionScanner:
    def __init__(self, cli_scan_scanner: CliScanProjectScanner):
        self.cli_scan_scanner = cli_scan_scanner
    
    def scan_functions(self, project_path: Path) -> List[MigratableFunction]:
        """扫描项目中的所有函数并评估可迁移性"""
        
    def is_migratable(self, func_info: FunctionInfo) -> bool:
        """判断函数是否可迁移"""
        # 检查：公开函数、有明确输入输出、副作用可控
```

**可迁移性判断规则**:
- ✅ 公开函数（不以 `_` 开头）
- ✅ 有明确的输入输出（参数和返回值）
- ✅ 无副作用或副作用可控（数据库操作、文件 I/O 等）
- ✅ 不依赖全局状态（除配置外）
- ❌ 私有函数（以 `_` 或 `__` 开头）
- ❌ 生成器函数（需要特殊处理）
- ❌ 装饰器函数（元编程）
- ❌ 抽象方法（需要实现）

### Component 3: OpenAPIScanner

**职责**: 扫描和解析 OpenAPI 规范文件。

**接口定义**:
```python
@dataclass
class APIEndpoint:
    path: str
    method: str  # GET, POST, PUT, DELETE, etc.
    operation_id: str
    summary: str
    description: str
    parameters: List[APIParameter]
    request_body: Optional[APIRequestBody]
    responses: Dict[str, APIResponse]
    security: List[SecurityRequirement]
    tags: List[str]

@dataclass
class APIParameter:
    name: str
    location: str  # path, query, header, cookie
    required: bool
    schema: Dict  # JSON Schema
    description: str

class OpenAPIScanner:
    def scan_spec(self, spec_path: Path) -> List[APIEndpoint]:
        """解析 OpenAPI 规范文件"""
        
    def validate_spec(self, spec_path: Path) -> List[ValidationError]:
        """验证 OpenAPI 规范文件"""
```

**实现细节**:
- 使用 `prance` 解析 OpenAPI 3.0+ 规范（YAML/JSON）
- 使用 `openapi-spec-validator` 验证规范合规性
- 提取所有端点的完整元数据
- 解析 security schemes（OAuth2, API Key, Bearer Token）

### Component 4: CronScanner

**职责**: 扫描项目中的定时任务配置。

**接口定义**:
```python
@dataclass
class CronTask:
    name: str
    schedule: str  # cron expression
    handler: str  # function name or module path
    description: str
    source_type: CronSourceType  # CRONTAB, APSCHEDULER, CELERY_BEAT
    source_location: str  # file path or config location
    dependencies: List[str]

class CronScanner:
    def scan_crontab(self, project_path: Path) -> List[CronTask]:
        """扫描 crontab 文件"""
        
    def scan_apscheduler(self, project_path: Path) -> List[CronTask]:
        """扫描 APScheduler 配置"""
        
    def scan_celery_beat(self, project_path: Path) -> List[CronTask]:
        """扫描 Celery Beat 配置"""
```

**实现细节**:
- 解析 crontab 文件（`/etc/crontab`, `crontab -l` 输出）
- 使用 AST 分析识别 APScheduler 的 `add_job()` 调用
- 解析 Celery Beat 配置文件（`celerybeat-schedule.py`）
- 提取 cron 表达式和关联的 handler 函数

### Component 5: ORMScanner

**职责**: 识别数据库操作函数。

**接口定义**:
```python
@dataclass
class ORMOperation:
    function_info: FunctionInfo
    orm_type: ORMType  # SQLALCHEMY, DJANGO_ORM
    operation_type: OperationType  # SELECT, INSERT, UPDATE, DELETE
    models: List[str]  # 涉及的模型类
    has_transaction: bool
    is_bulk_operation: bool
    involves_sensitive_data: bool

class ORMScanner:
    def scan_orm_operations(self, functions: List[FunctionInfo]) -> List[ORMOperation]:
        """识别 ORM 操作函数"""
        
    def detect_orm_type(self, func_info: FunctionInfo) -> Optional[ORMType]:
        """检测使用的 ORM 类型"""
        
    def analyze_operation(self, func_info: FunctionInfo) -> OperationType:
        """分析操作类型（CRUD）"""
```

**实现细节**:
- 使用 AST 分析识别 SQLAlchemy 的 `session.query()`, `session.add()` 等调用
- 识别 Django ORM 的 `Model.objects.filter()`, `Model.objects.create()` 等调用
- 检测事务管理（`@transaction.atomic`, `session.begin()`）
- 识别敏感数据模式（用户、密码、支付信息等字段名）

---

### Component 6: HandlerGenerator

**职责**: 生成 @handler 注册代码。

**接口定义**:
```python
@dataclass
class GenerationConfig:
    output_dir: Path
    code_style: CodeStyle  # PEP8, BLACK, CUSTOM
    include_logging: bool = True
    include_error_handling: bool = True
    include_type_hints: bool = True
    formatter: str = "black"  # black, autopep8

@dataclass
class GeneratedCode:
    file_path: Path
    content: str
    imports: List[str]
    manual_reviews: List[str]
    warnings: List[str]

class HandlerGenerator:
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.template_selector = TemplateSelector()
    
    def generate_handler(self, func: MigratableFunction) -> GeneratedCode:
        """为可迁移函数生成 @handler 注册代码"""
        
    def generate_trigger(self, cron_task: CronTask) -> GeneratedCode:
        """为定时任务生成 @cron 触发器代码"""
```

**实现细节**:
- 使用 Jinja2 模板引擎生成代码
- 每个生成的代码文件包含 `MANUAL_REVIEW` 注释（需要人工确认的部分）
- 生成的代码通过 black 格式化

### Component 7: SKILLGenerator

**职责**: 生成 SKILL.md 文档。

**接口定义**:
```python
class SKILLGenerator:
    def generate_skill(self, func: MigratableFunction) -> str:
        """为可迁移函数生成 SKILL.md 文档"""
        
    def generate_skill_from_api(self, endpoint: APIEndpoint) -> str:
        """为 API 端点生成 SKILL.md 文档"""
```

**实现细节**:
- 遵循 Agent Skills 规范（agentskills.io）
- 从函数签名和 docstring 提取 name、description、parameters
- 生成 frontmatter（name, version, description）和正文（功能、参数、使用场景）

### Component 8: MigrationReporter

**职责**: 生成迁移报告。

**接口定义**:
```python
@dataclass
class MigrationReport:
    summary: MigrationSummary
    functions: List[FunctionMigrationDetail]
    api_endpoints: List[APIMigrationDetail]
    cron_tasks: List[CronMigrationDetail]
    risks: List[RiskItem]
    recommendations: List[Recommendation]
    estimated_effort: EffortEstimate

class MigrationReporter:
    def generate_report(
        self, 
        scan_result: ScanResult,
        analysis_result: AnalysisResult,
        generation_result: GenerationResult
    ) -> MigrationReport:
        """生成完整的迁移报告"""
    
    def export_markdown(self, report: MigrationReport) -> str:
        """导出为 Markdown 格式"""
    
    def export_json(self, report: MigrationReport) -> dict:
        """导出为 JSON 格式"""
```

---

## Data Flow

### 完整迁移流程

```
owlclaw migrate --project ./my-app --output ./migration
    │
    ├── Step 1: Scan（扫描）
    │   ├── PythonFunctionScanner → 函数列表
    │   ├── OpenAPIScanner → API 端点列表
    │   ├── CronScanner → 定时任务列表
    │   └── ORMScanner → ORM 操作列表
    │
    ├── Step 2: Analyze（分析）
    │   ├── 评估每个函数的迁移可行性
    │   ├── 计算复杂度评分
    │   ├── 识别风险项
    │   └── 排列优先级
    │
    ├── Step 3: Generate（生成）
    │   ├── @handler 注册代码
    │   ├── @cron 触发器代码
    │   ├── SKILL.md 文档
    │   └── 配置文件模板
    │
    └── Step 4: Report（报告）
        ├── 迁移摘要（总数、成功率、风险）
        ├── 函数级别详细报告
        ├── 建议和优先级
        └── 工作量预估
```

### Dry-run 模式

```
owlclaw migrate --project ./my-app --dry-run
    │
    ├── Scan（实际执行）
    ├── Analyze（实际执行）
    ├── Generate（仅预览，不写文件）
    └── Report（输出到 stdout）
```

---

## Error Handling

### 扫描失败

**场景**：项目包含无法解析的 Python 文件

**处理**：跳过该文件，记录 warning 到 ScanResult.errors，继续扫描其余文件

### 生成冲突

**场景**：目标文件已存在

**处理**：默认不覆盖（`--force` 参数强制覆盖），生成 `.bak` 备份

---

## Configuration

### 配置文件

```yaml
# .owlclaw-migrate.yaml
scan:
  include: ["src/**/*.py"]
  exclude: ["tests/**", "migrations/**"]
  scan_openapi: true
  openapi_paths: ["docs/openapi.yaml"]

generate:
  output_dir: "./migration"
  code_style: black
  include_type_hints: true

analysis:
  min_complexity: 1
  max_complexity: 10
  skip_private: true
```

---

## Testing Strategy

### 单元测试

```python
def test_python_function_scanner_identifies_public_functions():
    """测试 PythonFunctionScanner 正确识别公开函数"""

def test_handler_generator_produces_valid_code():
    """测试 HandlerGenerator 生成的代码语法正确"""

def test_skill_generator_follows_agent_skills_spec():
    """测试 SKILLGenerator 输出符合 Agent Skills 规范"""
```

### 集成测试

```python
def test_full_migration_pipeline():
    """端到端测试：从扫描到生成报告"""

def test_dry_run_no_side_effects():
    """Dry-run 模式不产生文件副作用"""
```

---

## Migration Plan

### Phase 1：核心扫描和生成（3-4 天）
- [ ] ProjectScanner + PythonFunctionScanner
- [ ] HandlerGenerator + SKILLGenerator
- [ ] MigrationReporter（Markdown）

### Phase 2：高级功能（2-3 天）
- [ ] OpenAPIScanner
- [ ] CronScanner
- [ ] Interactive Wizard

### Phase 3：优化（1-2 天）
- [ ] ORMScanner
- [ ] 增量扫描
- [ ] JSON/PDF 报告输出

---

## References

- [OwlClaw 架构分析](../../docs/ARCHITECTURE_ANALYSIS.md) §5.2.4 能力注册
- [CLI Scan Spec](../cli-scan/)
- [Agent Skills 规范](https://agentskills.io)

---

**维护者**：OwlClaw Team  
**最后更新**：2026-02-22
