# Design Document: cli-scan

> **目标**: 提供 Python 项目 AST 代码扫描器，用于分析代码结构、函数签名、复杂度和依赖关系  
> **状态**: 设计中  
> **最后更新**: 2025-02-22

---

## Overview

cli-scan 是 OwlClaw 的核心基础设施组件，用于分析 Python 项目的源代码结构。它通过解析抽象语法树（AST）提取函数签名、类型信息、文档字符串、依赖关系和复杂度指标，输出结构化的扫描结果供 cli-migrate 等工具使用。

cli-scan 设计为独立可用的命令行工具，支持完整扫描和增量扫描模式，具备并行处理能力以应对大型项目。MVP 阶段专注于 Python 3.8+ 支持，后续可扩展至其他语言。

核心能力：
- Python AST 解析与函数签名提取
- 类型注解提取与类型推断
- 文档字符串解析（Google/NumPy/reStructuredText 风格）
- 依赖关系分析与循环依赖检测
- 复杂度计算（圈复杂度、认知复杂度、LOC/SLOC）
- 增量扫描与并行处理
- 结构化输出（JSON/YAML）
- 配置文件支持

---

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│  (ArgumentParser, Command Handlers, Output Formatters)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Scanner Engine                          │
│  (File Discovery, Parallel Processing, Incremental Logic)    │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
             ▼                            ▼
┌────────────────────────┐    ┌──────────────────────────────┐
│    Parser Module       │    │    Analyzer Module           │
│  - AST Parsing         │    │  - Complexity Calculator     │
│  - Signature Extractor │    │  - Dependency Analyzer       │
│  - Docstring Parser    │    │  - Type Inferencer           │
│  - Type Hint Extractor │    │                              │
└────────────────────────┘    └──────────────────────────────┘
             │                            │
             └────────────┬───────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Serializer Module                         │
│  (JSON/YAML Output, Schema Validation, Result Aggregation)   │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. CLI Layer (命令行接口层)

负责命令行参数解析、用户交互和输出格式化。

主要类：
- `CLIApplication`: 主入口，处理命令分发
- `ScanCommand`: 扫描命令处理器
- `ConfigCommand`: 配置验证命令处理器
- `OutputFormatter`: 输出格式化器（JSON/YAML/终端）

#### 2. Scanner Engine (扫描引擎)

负责文件发现、并行处理调度和增量扫描逻辑。

主要类：
- `ProjectScanner`: 主扫描器，协调整个扫描流程
- `FileDiscovery`: 文件发现器，遍历项目目录
- `IncrementalScanner`: 增量扫描器，使用 git diff 识别变更
- `ParallelExecutor`: 并行执行器，使用 multiprocessing 池
- `ScanCache`: 扫描缓存管理器

#### 3. Parser Module (解析器模块)

负责 Python 源代码解析和信息提取。

主要类：
- `ASTParser`: AST 解析器，使用 Python ast 模块
- `SignatureExtractor`: 函数签名提取器
- `DocstringParser`: 文档字符串解析器
- `TypeHintExtractor`: 类型注解提取器
- `DecoratorExtractor`: 装饰器提取器

#### 4. Analyzer Module (分析器模块)

负责代码分析和度量计算。

主要类：
- `ComplexityCalculator`: 复杂度计算器
- `DependencyAnalyzer`: 依赖关系分析器
- `TypeInferencer`: 类型推断器
- `CyclicDependencyDetector`: 循环依赖检测器

#### 5. Serializer Module (序列化器模块)

负责扫描结果的序列化和输出。

主要类：
- `ResultSerializer`: 结果序列化器
- `JSONSerializer`: JSON 序列化器
- `YAMLSerializer`: YAML 序列化器
- `SchemaValidator`: Schema 验证器

---

## Components and Interfaces

### Component 1: ASTParser

**职责**: 解析 Python 源文件为 AST 并提取基本结构信息。

**接口定义**:
```python
class ASTParser:
    def parse_file(self, file_path: Path) -> Optional[ast.Module]:
        """解析 Python 文件为 AST
        
        Args:
            file_path: Python 源文件路径
            
        Returns:
            AST Module 节点，解析失败返回 None
        """
        
    def extract_functions(self, tree: ast.Module) -> List[ast.FunctionDef]:
        """提取模块级函数定义"""
        
    def extract_classes(self, tree: ast.Module) -> List[ast.ClassDef]:
        """提取类定义"""
        
    def extract_methods(self, class_node: ast.ClassDef) -> List[ast.FunctionDef]:
        """提取类方法"""
```

**实现细节**:
- 使用 `ast.parse()` 解析源代码
- 支持 Python 3.8-3.13 语法特性
- 使用 `ast.NodeVisitor` 遍历 AST
- 捕获 `SyntaxError` 并记录详细错误信息

### Component 2: SignatureExtractor

**职责**: 从函数 AST 节点提取完整的函数签名信息。

**接口定义**:
```python
@dataclass
class FunctionSignature:
    name: str
    module: str
    qualname: str  # 完全限定名
    parameters: List[Parameter]
    return_type: Optional[str]
    decorators: List[Decorator]
    is_async: bool
    is_generator: bool
    lineno: int
    
@dataclass
class Parameter:
    name: str
    annotation: Optional[str]
    default: Optional[str]
    kind: ParameterKind  # POSITIONAL, KEYWORD, VAR_POSITIONAL, VAR_KEYWORD
    
class SignatureExtractor:
    def extract(self, func_node: ast.FunctionDef, context: Context) -> FunctionSignature:
        """提取函数签名"""
```

**实现细节**:
- 解析 `func_node.args` 提取参数信息
- 使用 `ast.unparse()` 将类型注解转换为字符串
- 识别 `*args` 和 `**kwargs`
- 提取装饰器名称和参数
- 检测 `async def` 和 `yield` 关键字

### Component 3: DocstringParser

**职责**: 解析和结构化文档字符串。

**接口定义**:
```python
@dataclass
class ParsedDocstring:
    summary: str
    description: str
    parameters: Dict[str, str]  # param_name -> description
    returns: Optional[str]
    raises: Dict[str, str]  # exception_type -> description
    examples: List[str]
    style: DocstringStyle  # GOOGLE, NUMPY, RESTRUCTUREDTEXT
    raw: str
    
class DocstringParser:
    def parse(self, docstring: str) -> ParsedDocstring:
        """解析文档字符串"""
        
    def detect_style(self, docstring: str) -> DocstringStyle:
        """检测文档字符串风格"""
```

**实现细节**:
- 使用正则表达式识别不同风格的 section 标记
- Google 风格: `Args:`, `Returns:`, `Raises:`
- NumPy 风格: `Parameters`, `Returns`, `Raises` (下划线分隔)
- reStructuredText 风格: `:param`, `:returns:`, `:raises:`
- 提取代码块（```python 或 >>> 开头）

### Component 4: ComplexityCalculator

**职责**: 计算函数的各种复杂度指标。

**接口定义**:
```python
@dataclass
class ComplexityScore:
    cyclomatic: int  # 圈复杂度
    cognitive: int  # 认知复杂度
    loc: int  # 代码行数
    sloc: int  # 有效代码行数（不含空行和注释）
    parameters: int  # 参数数量
    nesting_depth: int  # 最大嵌套深度
    level: ComplexityLevel  # SIMPLE, MEDIUM, COMPLEX
    
class ComplexityCalculator:
    def calculate(self, func_node: ast.FunctionDef, source: str) -> ComplexityScore:
        """计算函数复杂度"""
        
    def cyclomatic_complexity(self, func_node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        
    def cognitive_complexity(self, func_node: ast.FunctionDef) -> int:
        """计算认知复杂度"""
```

**实现细节**:

圈复杂度算法：
- 初始值为 1
- 每个决策点（if, elif, for, while, except, and, or）+1
- 每个 case 分支 +1

认知复杂度算法：
- 基于嵌套层级和控制流结构
- 嵌套的 if/for/while 增加额外惩罚
- 递归调用 +1
- 跳转语句（break, continue）+1

复杂度等级划分：
- SIMPLE: cyclomatic <= 5
- MEDIUM: 6 <= cyclomatic <= 10
- COMPLEX: cyclomatic > 10

### Component 5: DependencyAnalyzer

**职责**: 分析函数间的调用关系和模块依赖。

**接口定义**:
```python
@dataclass
class Dependency:
    source: str  # 调用方函数的完全限定名
    target: str  # 被调用函数的完全限定名
    import_type: ImportType  # STDLIB, THIRD_PARTY, LOCAL
    lineno: int
    
@dataclass
class DependencyGraph:
    nodes: List[str]  # 函数完全限定名列表
    edges: List[Dependency]  # 依赖边列表
    cycles: List[List[str]]  # 循环依赖列表
    
class DependencyAnalyzer:
    def analyze(self, tree: ast.Module, context: Context) -> DependencyGraph:
        """分析依赖关系"""
        
    def extract_imports(self, tree: ast.Module) -> List[Import]:
        """提取导入语句"""
        
    def extract_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """提取函数调用"""
        
    def detect_cycles(self, graph: DependencyGraph) -> List[List[str]]:
        """检测循环依赖"""
```

**实现细节**:
- 使用 `ast.NodeVisitor` 遍历函数体中的 `Call` 节点
- 解析 `import` 和 `from...import` 语句
- 使用 `importlib.util.find_spec()` 判断导入类型
- 使用 Tarjan 算法检测强连通分量（循环依赖）

### Component 6: TypeInferencer

**职责**: 推断缺少类型注解的变量类型。

**接口定义**:
```python
@dataclass
class InferredType:
    type_str: str
    confidence: Confidence  # HIGH, MEDIUM, LOW
    source: TypeSource  # DEFAULT_VALUE, ASSIGNMENT, RETURN_STMT
    
class TypeInferencer:
    def infer_parameter_type(self, param: ast.arg, default: Optional[ast.expr]) -> InferredType:
        """推断参数类型"""
        
    def infer_return_type(self, func_node: ast.FunctionDef) -> InferredType:
        """推断返回类型"""
```

**实现细节**:
- 从默认值推断：`def foo(x=5)` -> `int`
- 从赋值推断：`x = []` -> `List`
- 从返回语句推断：`return {"key": "value"}` -> `Dict[str, str]`
- 识别常见模式：`[]` -> `List`, `{}` -> `Dict`, `None` -> `Optional`
- 置信度评分：
  - HIGH: 从字面量或明确类型推断
  - MEDIUM: 从函数调用返回值推断
  - LOW: 从复杂表达式推断

### Component 7: ProjectScanner

**职责**: 协调整个扫描流程，管理并行处理和增量扫描。

**接口定义**:
```python
@dataclass
class ScanConfig:
    project_path: Path
    include_patterns: List[str]  # glob patterns
    exclude_patterns: List[str]
    incremental: bool
    workers: int
    extract_docstrings: bool
    calculate_complexity: bool
    analyze_dependencies: bool
    min_complexity_threshold: int
    
class ProjectScanner:
    def __init__(self, config: ScanConfig):
        self.config = config
        self.file_discovery = FileDiscovery(config)
        self.parser = ASTParser()
        self.cache = ScanCache()
        
    def scan(self) -> ScanResult:
        """执行扫描"""
        files = self._discover_files()
        if self.config.incremental:
            files = self._filter_changed_files(files)
        results = self._scan_parallel(files)
        return self._aggregate_results(results)
        
    def _scan_file(self, file_path: Path) -> FileScanResult:
        """扫描单个文件"""
```

**实现细节**:
- 使用 `multiprocessing.Pool` 实现并行扫描
- 工作进程数默认为 `os.cpu_count()`
- 使用 `functools.partial` 传递配置到工作进程
- 捕获并记录每个文件的扫描错误
- 使用 pickle 序列化结果在进程间传递

### Component 8: IncrementalScanner

**职责**: 实现增量扫描逻辑。

**接口定义**:
```python
class IncrementalScanner:
    def get_changed_files(self, project_path: Path) -> List[Path]:
        """获取变更的文件列表"""
        
    def load_cache(self) -> Optional[ScanResult]:
        """加载上次扫描结果"""
        
    def save_cache(self, result: ScanResult):
        """保存扫描结果到缓存"""
        
    def merge_results(self, cached: ScanResult, incremental: ScanResult) -> ScanResult:
        """合并缓存结果和增量结果"""
```

**实现细节**:
- 使用 `subprocess.run(['git', 'diff', '--name-only', 'HEAD'])` 获取变更文件
- 缓存文件存储在 `.owlclaw-scan-cache.json`
- 缓存包含文件路径、修改时间和扫描结果
- 合并时移除已删除文件的结果
- 更新变更文件的结果

---

## Data Models

### ScanResult (扫描结果)

```python
@dataclass
class ScanResult:
    metadata: ScanMetadata
    files: Dict[str, FileScanResult]  # file_path -> result
    dependency_graph: DependencyGraph
    statistics: ScanStatistics
    
@dataclass
class ScanMetadata:
    scan_time: datetime
    project_path: str
    total_files: int
    scanned_files: int
    failed_files: int
    scan_duration: float  # seconds
    incremental: bool
    
@dataclass
class FileScanResult:
    file_path: str
    module_name: str
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    imports: List[Import]
    errors: List[ScanError]
    scan_timestamp: datetime
    
@dataclass
class FunctionInfo:
    signature: FunctionSignature
    docstring: Optional[ParsedDocstring]
    complexity: ComplexityScore
    dependencies: List[str]  # 调用的函数列表
    inferred_types: Dict[str, InferredType]  # param_name -> type
    
@dataclass
class ClassInfo:
    name: str
    bases: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str]
    lineno: int
```

### Configuration Schema

配置文件 `.owlclaw-scan.yaml`:

```yaml
# 包含的目录和文件模式
include:
  - "src/**/*.py"
  - "lib/**/*.py"

# 排除的目录和文件模式
exclude:
  - "**/test_*.py"
  - "**/tests/**"
  - "**/__pycache__/**"
  - "**/venv/**"
  - "**/.venv/**"
  - "**/site-packages/**"

# 扫描选项
scan:
  extract_docstrings: true
  calculate_complexity: true
  analyze_dependencies: true
  min_complexity_threshold: 0  # 只输出复杂度 >= 此值的函数

# 并行处理
parallel:
  enabled: true
  workers: null  # null 表示自动检测 CPU 核心数

# 增量扫描
incremental:
  enabled: false
  cache_file: ".owlclaw-scan-cache.json"

# 输出选项
output:
  format: "json"  # json 或 yaml
  file: null  # null 表示输出到 stdout
  pretty: true  # 格式化输出
```

### Output Schema

JSON 输出格式：

```json
{
  "metadata": {
    "scan_time": "2025-02-22T10:30:00Z",
    "project_path": "/path/to/project",
    "total_files": 150,
    "scanned_files": 148,
    "failed_files": 2,
    "scan_duration": 3.45,
    "incremental": false
  },
  "files": {
    "src/main.py": {
      "file_path": "src/main.py",
      "module_name": "src.main",
      "functions": [
        {
          "signature": {
            "name": "process_data",
            "module": "src.main",
            "qualname": "src.main.process_data",
            "parameters": [
              {
                "name": "data",
                "annotation": "List[Dict[str, Any]]",
                "default": null,
                "kind": "POSITIONAL"
              }
            ],
            "return_type": "pd.DataFrame",
            "decorators": [],
            "is_async": false,
            "is_generator": false,
            "lineno": 15
          },
          "docstring": {
            "summary": "Process raw data into DataFrame",
            "description": "...",
            "parameters": {"data": "List of data dictionaries"},
            "returns": "Processed DataFrame",
            "raises": {},
            "examples": [],
            "style": "GOOGLE",
            "raw": "..."
          },
          "complexity": {
            "cyclomatic": 8,
            "cognitive": 12,
            "loc": 45,
            "sloc": 38,
            "parameters": 1,
            "nesting_depth": 3,
            "level": "MEDIUM"
          },
          "dependencies": ["pandas.DataFrame", "src.utils.validate"],
          "inferred_types": {}
        }
      ],
      "classes": [],
      "imports": [
        {"module": "pandas", "names": ["DataFrame"], "type": "THIRD_PARTY"}
      ],
      "errors": [],
      "scan_timestamp": "2025-02-22T10:30:01Z"
    }
  },
  "dependency_graph": {
    "nodes": ["src.main.process_data", "src.utils.validate"],
    "edges": [
      {
        "source": "src.main.process_data",
        "target": "src.utils.validate",
        "import_type": "LOCAL",
        "lineno": 20
      }
    ],
    "cycles": []
  },
  "statistics": {
    "total_functions": 245,
    "total_classes": 38,
    "avg_complexity": 6.2,
    "high_complexity_functions": 12
  }
}
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas of redundancy:

1. **Serialization round-trips**: Requirements 2.6, 9.1, 9.2, 14.1, and 14.4 all relate to serialization. These can be consolidated into comprehensive round-trip properties for JSON and YAML.

2. **CLI parameter handling**: Requirements 12.2-12.6 overlap with earlier requirements (7.1, 8.3, 9.3). The CLI properties should focus on parameter parsing, while functional properties cover the actual behavior.

3. **File discovery**: Requirements 1.1 and 1.6 both relate to file discovery and can be combined into a single property about correct file filtering.

4. **Signature extraction completeness**: Requirements 2.1-2.5 all relate to extracting different aspects of function signatures. These can be combined into a comprehensive signature extraction property.

5. **Error handling**: Requirements 1.5, 8.6, 11.1, and 11.6 all relate to error handling and can be consolidated.

The following properties represent the unique, non-redundant validation requirements:

### Property 1: File Discovery with Exclusions

*For any* project directory structure with Python files and excluded directories (venv, .venv, env, site-packages), the scanner should discover all .py files except those in excluded directories.

**Validates: Requirements 1.1, 1.6**

### Property 2: Valid Python Parsing

*For any* syntactically valid Python source file (Python 3.8-3.13), the parser should successfully parse it into an AST and extract all module-level functions, classes, and methods.

**Validates: Requirements 1.2, 1.3, 13.1**

### Property 3: Syntax Error Resilience

*For any* set of files where some contain syntax errors, the scanner should record errors for invalid files and successfully scan all valid files.

**Validates: Requirements 1.5, 11.6**

### Property 4: Complete Signature Extraction

*For any* valid Python function definition (with any combination of positional, keyword, variadic parameters, type hints, decorators, async/generator modifiers), the signature extractor should capture all components accurately.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

### Property 5: Signature Round-Trip Consistency

*For any* valid Python source file, parsing → extracting signatures → validating should ensure the extracted signatures match the source code structure.

**Validates: Requirements 13.4**

### Property 6: Docstring Extraction Preservation

*For any* Python function, class, or module with a docstring, the scanner should extract the docstring preserving its original formatting and indentation.

**Validates: Requirements 3.1, 3.5**

### Property 7: Structured Docstring Parsing

*For any* docstring containing parameter descriptions, return descriptions, or exception descriptions (in any supported style), the parser should extract these structured sections correctly.

**Validates: Requirements 3.3, 3.4**

### Property 8: Type Inference from Defaults

*For any* function parameter with a default value but no type hint, the type inferencer should infer a type from the default value with appropriate confidence.

**Validates: Requirements 4.1**

### Property 9: Type Inference Fallback

*For any* parameter or return type that cannot be inferred, the scanner should mark it as "unknown" rather than failing or guessing incorrectly.

**Validates: Requirements 4.5**

### Property 10: Function Call Detection

*For any* function body containing function calls, the dependency analyzer should identify all call sites and their targets.

**Validates: Requirements 5.1**

### Property 11: Import Classification

*For any* Python import statement, the analyzer should correctly classify it as STDLIB, THIRD_PARTY, or LOCAL.

**Validates: Requirements 5.3, 5.4**

### Property 12: Cycle Detection

*For any* dependency graph containing circular dependencies, the cycle detector should identify all strongly connected components.

**Validates: Requirements 5.5**

### Property 13: Complexity Metrics Completeness

*For any* function, the complexity calculator should compute all metrics (cyclomatic, cognitive, LOC, SLOC, parameters, nesting depth) and assign the correct complexity level.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**

### Property 14: Incremental Scan Correctness

*For any* project with cached scan results, when files are modified, added, or deleted, incremental scanning should produce the same final result as a full scan.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 15: Parallel Scan Determinism

*For any* project scanned with different worker counts, the results should be identical (deterministic output regardless of parallelization).

**Validates: Requirements 8.4**

### Property 16: Parallel Error Handling

*For any* set of files scanned in parallel where some files cause errors, all errors should be captured and all valid files should be scanned successfully.

**Validates: Requirements 8.6**

### Property 17: JSON Serialization Round-Trip

*For any* ScanResult object, serializing to JSON then deserializing should produce an equivalent object.

**Validates: Requirements 9.1, 14.4**

### Property 18: YAML Serialization Round-Trip

*For any* ScanResult object, serializing to YAML then deserializing should produce an equivalent object.

**Validates: Requirements 9.2, 14.4**

### Property 19: Output Schema Compliance

*For any* scan result output, it should validate against the predefined JSON schema.

**Validates: Requirements 9.6, 14.5**

### Property 20: Configuration Pattern Filtering

*For any* configuration with include/exclude glob patterns, the scanner should only process files matching include patterns and not matching exclude patterns.

**Validates: Requirements 10.2, 10.3**

### Property 21: Complexity Threshold Filtering

*For any* configuration with a minimum complexity threshold, the output should only contain functions with complexity >= threshold.

**Validates: Requirements 10.4**

### Property 22: Feature Toggle Respect

*For any* configuration with feature toggles disabled (docstrings, complexity, dependencies), the corresponding data should not be present in the output.

**Validates: Requirements 10.5**

### Property 23: Configuration Round-Trip

*For any* valid configuration object, parsing → serializing → parsing should produce an equivalent configuration.

**Validates: Requirements 15.4**

### Property 24: Configuration Validation

*For any* configuration file with invalid values (wrong types, out-of-range values), the validator should reject it with descriptive error messages.

**Validates: Requirements 15.2, 15.3**

### Property 25: Error Logging Completeness

*For any* error encountered during scanning, the error log should contain the file path, error type, and descriptive message.

**Validates: Requirements 11.1**

### Property 26: Scan Statistics Accuracy

*For any* completed scan, the statistics (total files, scanned files, failed files) should accurately reflect the scan results.

**Validates: Requirements 9.5, 11.5**

---

## Error Handling

### Error Categories

#### 1. File System Errors

**Scenarios**:
- File not found
- Permission denied
- Symbolic link loops
- File too large

**Handling**:
```python
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
except (FileNotFoundError, PermissionError) as e:
    logger.warning(f"Cannot read {file_path}: {e}")
    return FileScanResult(
        file_path=str(file_path),
        errors=[ScanError(type="FileSystemError", message=str(e))]
    )
```

#### 2. Parsing Errors

**Scenarios**:
- Syntax errors in Python code
- Unsupported Python version features
- Encoding issues

**Handling**:
```python
try:
    tree = ast.parse(source, filename=str(file_path))
except SyntaxError as e:
    logger.error(f"Syntax error in {file_path}:{e.lineno}: {e.msg}")
    return FileScanResult(
        file_path=str(file_path),
        errors=[ScanError(
            type="SyntaxError",
            message=e.msg,
            lineno=e.lineno,
            offset=e.offset
        )]
    )
```

#### 3. Analysis Errors

**Scenarios**:
- Type inference failures
- Circular dependency detection failures
- Complexity calculation errors

**Handling**:
- Log warnings for non-critical failures
- Use fallback values (e.g., "unknown" for types)
- Continue processing other functions

#### 4. Serialization Errors

**Scenarios**:
- Non-serializable objects in results
- Schema validation failures
- File write errors

**Handling**:
```python
try:
    json.dump(result, f, cls=CustomEncoder)
except TypeError as e:
    logger.error(f"Serialization error: {e}")
    # Attempt to serialize with fallback encoder
    json.dump(result, f, default=str)
```

#### 5. Configuration Errors

**Scenarios**:
- Invalid YAML syntax
- Missing required fields
- Invalid field values

**Handling**:
```python
try:
    config = yaml.safe_load(f)
    validate_config(config)
except yaml.YAMLError as e:
    raise ConfigError(f"Invalid YAML: {e}")
except ValidationError as e:
    raise ConfigError(f"Invalid configuration: {e}")
```

### Error Recovery Strategy

1. **Fail Fast**: Configuration and CLI argument errors should fail immediately
2. **Continue on File Errors**: File-level errors should not stop the entire scan
3. **Graceful Degradation**: Missing optional data (docstrings, type hints) should not cause failures
4. **Detailed Logging**: All errors should be logged with context for debugging

---

## Testing Strategy

### Dual Testing Approach

The testing strategy combines unit tests for specific examples and edge cases with property-based tests for comprehensive coverage of input spaces.

**Unit Tests**: Focus on specific examples, integration points, and edge cases
**Property Tests**: Verify universal properties across randomized inputs

### Unit Testing

Unit tests validate specific scenarios and edge cases:

**Parser Tests**:
- Parse empty file
- Parse file with only imports
- Parse file with syntax error at specific line
- Parse file with Python 3.10+ match statement
- Parse file with Python 3.12+ type parameter syntax

**Signature Extraction Tests**:
- Extract function with no parameters
- Extract function with *args and **kwargs
- Extract function with complex type hints (Union, Optional, Generic)
- Extract async function
- Extract generator function with yield

**Docstring Tests**:
- Parse Google-style docstring
- Parse NumPy-style docstring
- Parse reStructuredText-style docstring
- Parse docstring with code examples
- Handle missing docstring

**Complexity Tests**:
- Calculate complexity for simple linear function (expected: cyclomatic=1)
- Calculate complexity for function with nested if statements
- Calculate complexity for function with multiple loops
- Verify complexity level assignment (simple/medium/complex)

**Dependency Tests**:
- Detect function calls within same module
- Detect imported function calls
- Detect method calls on objects
- Identify circular dependencies in test fixture

**Incremental Scan Tests**:
- Scan project, modify file, verify only modified file rescanned
- Scan project, delete file, verify file removed from results
- Scan project, add file, verify new file included

**Configuration Tests**:
- Load valid configuration file
- Reject configuration with invalid field types
- Apply default values when config missing
- Validate glob patterns

### Property-Based Testing

Property tests verify universal correctness properties using randomized inputs. Each test should run minimum 100 iterations.

**Testing Library**: Use `hypothesis` for Python property-based testing

**Test Configuration**:
```python
from hypothesis import given, settings
import hypothesis.strategies as st

@settings(max_examples=100)
@given(st.text())
def test_property(input_data):
    # Feature: cli-scan, Property 1: File Discovery with Exclusions
    ...
```

**Property Test Cases**:

1. **File Discovery** (Property 1)
   - Generate random directory structures with .py files
   - Include random excluded directories
   - Verify all non-excluded .py files discovered

2. **Valid Python Parsing** (Property 2)
   - Generate valid Python AST
   - Unparse to source code
   - Parse and verify all functions/classes extracted

3. **Syntax Error Resilience** (Property 3)
   - Generate mix of valid and invalid Python files
   - Verify all valid files scanned successfully
   - Verify errors recorded for invalid files

4. **Complete Signature Extraction** (Property 4)
   - Generate random function definitions with various parameter types
   - Extract signatures
   - Verify all components present

5. **Signature Round-Trip** (Property 5)
   - Generate random Python functions
   - Parse → extract → validate
   - Verify extracted signature matches source

6. **Docstring Preservation** (Property 6)
   - Generate random docstrings with various formatting
   - Extract and compare with original
   - Verify formatting preserved

7. **Type Inference** (Properties 8, 9)
   - Generate parameters with various default values
   - Verify type inference or "unknown" marking

8. **Dependency Detection** (Property 10)
   - Generate functions with random call patterns
   - Verify all calls detected

9. **Cycle Detection** (Property 12)
   - Generate dependency graphs with known cycles
   - Verify all cycles detected

10. **Complexity Metrics** (Property 13)
    - Generate functions with known complexity
    - Verify all metrics calculated correctly

11. **Incremental Scan Correctness** (Property 14)
    - Generate project, scan, modify, scan incrementally
    - Verify incremental result equals full scan result

12. **Parallel Determinism** (Property 15)
    - Scan same project with different worker counts
    - Verify results identical

13. **JSON Round-Trip** (Property 17)
    - Generate random ScanResult objects
    - Serialize → deserialize
    - Verify equivalence

14. **YAML Round-Trip** (Property 18)
    - Generate random ScanResult objects
    - Serialize → deserialize
    - Verify equivalence

15. **Schema Compliance** (Property 19)
    - Generate random scan results
    - Validate against JSON schema
    - Verify all pass validation

16. **Pattern Filtering** (Property 20)
    - Generate random file sets and patterns
    - Apply filtering
    - Verify only matching files included

17. **Threshold Filtering** (Property 21)
    - Generate functions with various complexity
    - Apply threshold
    - Verify only functions >= threshold included

18. **Feature Toggles** (Property 22)
    - Generate config with features disabled
    - Scan and verify corresponding data absent

19. **Config Round-Trip** (Property 23)
    - Generate random valid configs
    - Parse → serialize → parse
    - Verify equivalence

20. **Config Validation** (Property 24)
    - Generate invalid configs
    - Verify validation rejects with errors

21. **Error Logging** (Property 25)
    - Generate errors during scanning
    - Verify all errors logged with required fields

22. **Statistics Accuracy** (Property 26)
    - Scan projects with known file counts
    - Verify statistics match actual results

**Property Test Tags**:
Each property test must include a comment tag:
```python
# Feature: cli-scan, Property 17: JSON Serialization Round-Trip
```

### Integration Testing

Integration tests verify end-to-end workflows:

- Full project scan with all features enabled
- Incremental scan workflow (scan → modify → rescan)
- CLI invocation with various argument combinations
- Configuration file loading and application
- Output file generation (JSON and YAML)
- Parallel scanning with multiple workers

### Performance Testing

While not part of automated testing, performance should be validated:

- Scan 1000 files and measure duration (target: < 10 seconds)
- Memory usage during large project scans
- Parallel speedup with different worker counts

---

## Implementation Details

### File Structure

```
owlclaw-cli-scan/
├── owlclaw_scan/
│   ├── __init__.py
│   ├── __main__.py              # CLI entry point
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py               # CLIApplication
│   │   ├── commands.py          # ScanCommand, ConfigCommand
│   │   └── formatters.py        # OutputFormatter
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── project_scanner.py   # ProjectScanner
│   │   ├── file_discovery.py    # FileDiscovery
│   │   ├── incremental.py       # IncrementalScanner
│   │   ├── parallel.py          # ParallelExecutor
│   │   └── cache.py             # ScanCache
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── ast_parser.py        # ASTParser
│   │   ├── signature.py         # SignatureExtractor
│   │   ├── docstring.py         # DocstringParser
│   │   └── types.py             # TypeHintExtractor
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── complexity.py        # ComplexityCalculator
│   │   ├── dependencies.py      # DependencyAnalyzer
│   │   ├── type_inference.py    # TypeInferencer
│   │   └── cycles.py            # CyclicDependencyDetector
│   ├── serializer/
│   │   ├── __init__.py
│   │   ├── json_serializer.py   # JSONSerializer
│   │   ├── yaml_serializer.py   # YAMLSerializer
│   │   └── schema.py            # SchemaValidator
│   ├── models/
│   │   ├── __init__.py
│   │   ├── scan_result.py       # ScanResult, FileScanResult
│   │   ├── signature.py         # FunctionSignature, Parameter
│   │   ├── docstring.py         # ParsedDocstring
│   │   ├── complexity.py        # ComplexityScore
│   │   ├── dependency.py        # Dependency, DependencyGraph
│   │   └── config.py            # ScanConfig
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Logging configuration
│       └── git.py               # Git integration utilities
├── tests/
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_signature.py
│   │   ├── test_docstring.py
│   │   ├── test_complexity.py
│   │   ├── test_dependencies.py
│   │   ├── test_type_inference.py
│   │   └── test_serializer.py
│   ├── property/
│   │   ├── test_properties.py   # All property-based tests
│   │   └── strategies.py        # Hypothesis strategies
│   ├── integration/
│   │   ├── test_full_scan.py
│   │   ├── test_incremental.py
│   │   └── test_cli.py
│   └── fixtures/
│       ├── sample_projects/     # Test Python projects
│       └── configs/             # Test configuration files
├── schema/
│   └── scan_result.schema.json  # JSON Schema for output
├── pyproject.toml
├── README.md
└── LICENSE
```

### Key Algorithms

#### Cyclomatic Complexity Calculation

```python
def cyclomatic_complexity(func_node: ast.FunctionDef) -> int:
    """
    Calculate cyclomatic complexity using the formula:
    M = E - N + 2P
    
    Simplified for single function: count decision points + 1
    """
    complexity = 1
    
    for node in ast.walk(func_node):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            # Each 'and'/'or' adds a decision point
            complexity += len(node.values) - 1
        elif isinstance(node, ast.Match):  # Python 3.10+
            complexity += len(node.cases)
    
    return complexity
```

#### Cognitive Complexity Calculation

```python
def cognitive_complexity(func_node: ast.FunctionDef) -> int:
    """
    Calculate cognitive complexity based on nesting and control flow.
    
    Rules:
    - Each control flow structure adds 1
    - Nested structures add their nesting level
    - Break/continue add 1
    - Recursion adds 1
    """
    complexity = 0
    nesting_level = 0
    func_name = func_node.name
    
    class CognitiveVisitor(ast.NodeVisitor):
        nonlocal complexity, nesting_level
        
        def visit_If(self, node):
            nonlocal complexity, nesting_level
            complexity += 1 + nesting_level
            nesting_level += 1
            self.generic_visit(node)
            nesting_level -= 1
        
        def visit_For(self, node):
            nonlocal complexity, nesting_level
            complexity += 1 + nesting_level
            nesting_level += 1
            self.generic_visit(node)
            nesting_level -= 1
        
        def visit_While(self, node):
            nonlocal complexity, nesting_level
            complexity += 1 + nesting_level
            nesting_level += 1
            self.generic_visit(node)
            nesting_level -= 1
        
        def visit_Call(self, node):
            nonlocal complexity
            # Check for recursion
            if isinstance(node.func, ast.Name) and node.func.id == func_name:
                complexity += 1
            self.generic_visit(node)
        
        def visit_Break(self, node):
            nonlocal complexity
            complexity += 1
        
        def visit_Continue(self, node):
            nonlocal complexity
            complexity += 1
    
    visitor = CognitiveVisitor()
    visitor.visit(func_node)
    return complexity
```

#### Cycle Detection (Tarjan's Algorithm)

```python
def detect_cycles(graph: DependencyGraph) -> List[List[str]]:
    """
    Detect strongly connected components (cycles) using Tarjan's algorithm.
    """
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = set()
    cycles = []
    
    # Build adjacency list
    adj = defaultdict(list)
    for edge in graph.edges:
        adj[edge.source].append(edge.target)
    
    def strongconnect(node):
        index[node] = index_counter[0]
        lowlinks[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        
        for successor in adj[node]:
            if successor not in index:
                strongconnect(successor)
                lowlinks[node] = min(lowlinks[node], lowlinks[successor])
            elif successor in on_stack:
                lowlinks[node] = min(lowlinks[node], index[successor])
        
        if lowlinks[node] == index[node]:
            component = []
            while True:
                successor = stack.pop()
                on_stack.remove(successor)
                component.append(successor)
                if successor == node:
                    break
            if len(component) > 1:  # Only cycles, not single nodes
                cycles.append(component)
    
    for node in graph.nodes:
        if node not in index:
            strongconnect(node)
    
    return cycles
```

#### Type Inference from Default Values

```python
def infer_from_default(default: ast.expr) -> InferredType:
    """
    Infer type from default value expression.
    """
    if isinstance(default, ast.Constant):
        value = default.value
        if value is None:
            return InferredType("Optional", Confidence.MEDIUM, TypeSource.DEFAULT_VALUE)
        type_str = type(value).__name__
        return InferredType(type_str, Confidence.HIGH, TypeSource.DEFAULT_VALUE)
    
    elif isinstance(default, ast.List):
        if default.elts:
            # Infer element type from first element
            elem_type = infer_from_default(default.elts[0])
            return InferredType(f"List[{elem_type.type_str}]", Confidence.MEDIUM, TypeSource.DEFAULT_VALUE)
        return InferredType("List", Confidence.HIGH, TypeSource.DEFAULT_VALUE)
    
    elif isinstance(default, ast.Dict):
        if default.keys and default.values:
            key_type = infer_from_default(default.keys[0])
            val_type = infer_from_default(default.values[0])
            return InferredType(f"Dict[{key_type.type_str}, {val_type.type_str}]", 
                              Confidence.MEDIUM, TypeSource.DEFAULT_VALUE)
        return InferredType("Dict", Confidence.HIGH, TypeSource.DEFAULT_VALUE)
    
    elif isinstance(default, ast.Set):
        return InferredType("Set", Confidence.HIGH, TypeSource.DEFAULT_VALUE)
    
    elif isinstance(default, ast.Tuple):
        return InferredType("Tuple", Confidence.HIGH, TypeSource.DEFAULT_VALUE)
    
    else:
        # Complex expression, low confidence
        return InferredType("unknown", Confidence.LOW, TypeSource.DEFAULT_VALUE)
```

### Performance Considerations

#### Parallel Scanning Strategy

```python
def _scan_parallel(self, files: List[Path]) -> List[FileScanResult]:
    """
    Scan files in parallel using multiprocessing.
    """
    if len(files) <= 10 or self.config.workers == 1:
        # Small file count, don't bother with parallelization
        return [self._scan_file(f) for f in files]
    
    # Use multiprocessing Pool
    with multiprocessing.Pool(processes=self.config.workers) as pool:
        # Use chunksize for better load balancing
        chunksize = max(1, len(files) // (self.config.workers * 4))
        results = pool.map(
            functools.partial(scan_file_worker, config=self.config),
            files,
            chunksize=chunksize
        )
    
    return results

def scan_file_worker(file_path: Path, config: ScanConfig) -> FileScanResult:
    """
    Worker function for parallel scanning.
    Must be top-level function for pickling.
    """
    scanner = ProjectScanner(config)
    return scanner._scan_file(file_path)
```

#### Caching Strategy

```python
class ScanCache:
    """
    Manage scan result caching for incremental scans.
    """
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
    
    def load(self) -> Optional[ScanResult]:
        if not self.cache_file.exists():
            return None
        
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
            return ScanResult.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid cache file: {e}")
            return None
    
    def save(self, result: ScanResult):
        with open(self.cache_file, 'w') as f:
            json.dump(result.to_dict(), f)
    
    def invalidate_file(self, file_path: str):
        """Remove a file from cache."""
        result = self.load()
        if result and file_path in result.files:
            del result.files[file_path]
            self.save(result)
```

#### Memory Optimization

For large projects:
- Stream file processing (don't load all files into memory)
- Use generators where possible
- Clear AST nodes after processing
- Limit cache size (e.g., only cache last 1000 files)

```python
def _scan_file(self, file_path: Path) -> FileScanResult:
    """Scan single file with memory cleanup."""
    try:
        tree = self.parser.parse_file(file_path)
        result = self._extract_info(tree, file_path)
        
        # Clear AST to free memory
        del tree
        
        return result
    except Exception as e:
        logger.error(f"Error scanning {file_path}: {e}")
        return FileScanResult(file_path=str(file_path), errors=[...])
```

---

## Configuration

### Default Configuration

When no configuration file is present, use these defaults:

```python
DEFAULT_CONFIG = ScanConfig(
    project_path=Path.cwd(),
    include_patterns=["**/*.py"],
    exclude_patterns=[
        "**/test_*.py",
        "**/tests/**",
        "**/__pycache__/**",
        "**/venv/**",
        "**/.venv/**",
        "**/env/**",
        "**/site-packages/**",
        "**/.git/**",
        "**/.tox/**",
        "**/build/**",
        "**/dist/**",
    ],
    incremental=False,
    workers=os.cpu_count() or 4,
    extract_docstrings=True,
    calculate_complexity=True,
    analyze_dependencies=True,
    min_complexity_threshold=0,
)
```

### Configuration Validation

```python
def validate_config(config_dict: dict) -> ScanConfig:
    """
    Validate and parse configuration dictionary.
    """
    errors = []
    
    # Validate include patterns
    if 'include' in config_dict:
        if not isinstance(config_dict['include'], list):
            errors.append("'include' must be a list of patterns")
    
    # Validate workers
    if 'parallel' in config_dict and 'workers' in config_dict['parallel']:
        workers = config_dict['parallel']['workers']
        if workers is not None and (not isinstance(workers, int) or workers < 1):
            errors.append("'workers' must be a positive integer or null")
    
    # Validate min_complexity_threshold
    if 'scan' in config_dict and 'min_complexity_threshold' in config_dict['scan']:
        threshold = config_dict['scan']['min_complexity_threshold']
        if not isinstance(threshold, int) or threshold < 0:
            errors.append("'min_complexity_threshold' must be a non-negative integer")
    
    if errors:
        raise ValidationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return ScanConfig.from_dict(config_dict)
```

---

## CLI Interface

### Command Structure

```bash
owlclaw scan [OPTIONS] <path>
owlclaw scan config validate [config_file]
```

### Arguments and Options

```python
import argparse

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='owlclaw-scan',
        description='AST code scanner for Python projects'
    )
    
    parser.add_argument(
        'path',
        type=Path,
        help='Path to Python project directory'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'yaml'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file path (default: stdout)'
    )
    
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Enable incremental scanning'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        help='Number of worker processes (default: CPU count)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=Path('.owlclaw-scan.yaml'),
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    return parser
```

### Usage Examples

```bash
# Basic scan
owlclaw scan /path/to/project

# Scan with YAML output
owlclaw scan --format yaml /path/to/project

# Scan and save to file
owlclaw scan --output results.json /path/to/project

# Incremental scan with custom workers
owlclaw scan --incremental --workers 8 /path/to/project

# Scan with custom config
owlclaw scan --config my-config.yaml /path/to/project

# Validate configuration
owlclaw scan config validate .owlclaw-scan.yaml

# Verbose output
owlclaw scan --verbose /path/to/project
```

---

## Dependencies

### Core Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.8"
pyyaml = "^6.0"
jsonschema = "^4.17"

[tool.poetry.dev-dependencies]
pytest = "^7.2"
hypothesis = "^6.68"
pytest-cov = "^4.0"
black = "^23.1"
mypy = "^1.0"
ruff = "^0.0.254"
```

### Standard Library Usage

- `ast`: AST parsing and traversal
- `argparse`: CLI argument parsing
- `logging`: Logging infrastructure
- `multiprocessing`: Parallel processing
- `pathlib`: Path manipulation
- `json`: JSON serialization
- `subprocess`: Git integration
- `dataclasses`: Data model definitions
- `typing`: Type annotations

---

## Risks and Mitigations

### Risk 1: Python Version Compatibility

**Impact**: Scanner may fail on newer Python syntax features

**Mitigation**:
- Use `ast.parse()` with appropriate Python version
- Catch `SyntaxError` and log unsupported features
- Test against multiple Python versions in CI

### Risk 2: Large Project Performance

**Impact**: Scanning very large projects (10,000+ files) may be slow

**Mitigation**:
- Implement parallel scanning with multiprocessing
- Use incremental scanning for repeated scans
- Optimize AST traversal algorithms
- Profile and optimize hot paths

### Risk 3: Type Inference Accuracy

**Impact**: Inferred types may be incorrect or too generic

**Mitigation**:
- Provide confidence scores with inferred types
- Mark uncertain types as "unknown"
- Allow users to disable type inference
- Document limitations clearly

### Risk 4: Memory Usage

**Impact**: Large projects may consume excessive memory

**Mitigation**:
- Stream file processing
- Clear AST nodes after processing
- Limit cache size
- Use generators instead of lists where possible

### Risk 5: Dependency Analysis Complexity

**Impact**: Complex import patterns may be missed

**Mitigation**:
- Focus on common import patterns first
- Log unhandled import patterns
- Allow users to disable dependency analysis
- Iterate based on real-world usage

---

**维护者**: OwlClaw 核心团队  
**最后更新**: 2025-02-22  
**状态**: 设计完成，待审核
