# 设计文档：SKILL.md 模板库

## 概述

本文档描述了 SKILL.md 模板库的设计。该模板库提供可复用的 SKILL.md 模板集合，降低业务接入成本，帮助开发者快速创建符合 Agent Skills 规范的能力描述文档。

模板库按照使用场景分类（monitoring/analysis/workflow/integration/report），每个模板都包含完整的结构、示例和最佳实践指导，使开发者能够快速上手并保持一致性。

### 核心设计原则

1. **分类清晰**：按照使用场景分类，便于查找和选择
2. **结构完整**：每个模板包含完整的 frontmatter 和 Markdown 指令
3. **示例丰富**：提供真实场景的示例，降低理解成本
4. **最佳实践**：内置最佳实践指导，避免常见错误
5. **可扩展性**：支持自定义模板和模板继承

### 设计目标

- 提供 5 大类别的模板（monitoring、analysis、workflow、integration、report）
- 每个类别包含 2-3 个具体模板
- 支持模板验证和自动补全
- 支持模板搜索和推荐
- 与 `owlclaw skill init` CLI 集成

## 架构

### 系统上下文

```
开发者
    ↓
owlclaw skill init (CLI)
    ↓
skill-templates 模块 (模板库)
    ↓
生成 SKILL.md 文件
    ↓
业务应用 capabilities/ 目录
```

### 集成边界

**OwlClaw 组件：**
- CLI 工具 (`owlclaw skill init`)
- Skills 加载器 (`owlclaw.capabilities.skills`)
- Skills 验证器 (`owlclaw skill validate`)

**模板库组件：**
- 模板存储和管理
- 模板渲染引擎
- 模板验证器
- 模板搜索引擎

**外部依赖：**
- Jinja2（模板渲染）
- YAML（frontmatter 解析）
- Agent Skills 规范（模板格式标准）

### 数据流

```
开发者执行 owlclaw skill init
    ↓
CLI 询问使用场景
    ↓
模板库搜索匹配的模板
    ↓
展示模板列表供选择
    ↓
收集模板参数（名称、描述等）
    ↓
渲染模板生成 SKILL.md
    ↓
写入到 capabilities/ 目录
    ↓
自动验证生成的文件
```

### 组件架构

```
owlclaw/templates/skills/
├─ __init__.py (模板库入口)
├─ registry.py (模板注册表)
├─ renderer.py (模板渲染器)
├─ validator.py (模板验证器)
├─ searcher.py (模板搜索器)
└─ templates/ (模板文件)
   ├─ monitoring/
   │  ├─ health-check.md.j2
   │  ├─ metric-monitor.md.j2
   │  └─ alert-handler.md.j2
   ├─ analysis/
   │  ├─ data-analyzer.md.j2
   │  ├─ trend-detector.md.j2
   │  └─ anomaly-detector.md.j2
   ├─ workflow/
   │  ├─ approval-flow.md.j2
   │  ├─ task-scheduler.md.j2
   │  └─ event-handler.md.j2
   ├─ integration/
   │  ├─ api-client.md.j2
   │  ├─ webhook-handler.md.j2
   │  └─ data-sync.md.j2
   └─ report/
      ├─ daily-report.md.j2
      ├─ summary-generator.md.j2
      └─ notification-sender.md.j2
```

## 组件和接口

### 1. TemplateRegistry

模板注册表，管理所有可用的模板。

#### 接口定义

```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class TemplateCategory(Enum):
    """模板类别"""
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"
    REPORT = "report"

@dataclass
class TemplateMetadata:
    """模板元数据"""
    id: str  # 模板唯一标识，如 "monitoring/health-check"
    name: str  # 模板显示名称
    category: TemplateCategory  # 模板类别
    description: str  # 模板描述
    tags: List[str]  # 标签，用于搜索
    parameters: List['TemplateParameter']  # 模板参数
    examples: List[str]  # 使用示例
    file_path: Path  # 模板文件路径

@dataclass
class TemplateParameter:
    """模板参数"""
    name: str  # 参数名称
    type: str  # 参数类型：str, int, bool, list
    description: str  # 参数描述
    required: bool = True  # 是否必需
    default: Optional[Any] = None  # 默认值
    choices: Optional[List[Any]] = None  # 可选值列表

class TemplateRegistry:
    """模板注册表"""
    
    def __init__(self, templates_dir: Path):
        """
        初始化模板注册表
        
        Args:
            templates_dir: 模板目录路径
        """
        self.templates_dir = templates_dir
        self._templates: Dict[str, TemplateMetadata] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载所有模板"""
        for category_dir in self.templates_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = TemplateCategory(category_dir.name)
            
            for template_file in category_dir.glob("*.md.j2"):
                metadata = self._parse_template_metadata(template_file, category)
                self._templates[metadata.id] = metadata
    
    def _parse_template_metadata(
        self,
        template_file: Path,
        category: TemplateCategory,
    ) -> TemplateMetadata:
        """
        解析模板元数据
        
        从模板文件的注释中提取元数据
        
        Args:
            template_file: 模板文件路径
            category: 模板类别
        
        Returns:
            模板元数据
        """
        # 读取模板文件
        content = template_file.read_text(encoding='utf-8')
        
        # 解析元数据注释块（{# ... #}）
        # 格式：
        # {#
        # name: Health Check Monitor
        # description: Monitor system health and alert on issues
        # tags: [monitoring, health, alert]
        # parameters:
        #   - name: check_interval
        #     type: int
        #     description: Check interval in seconds
        #     default: 60
        # #}
        
        # 实现解析逻辑...
        pass
    
    def get_template(self, template_id: str) -> Optional[TemplateMetadata]:
        """
        获取模板
        
        Args:
            template_id: 模板 ID
        
        Returns:
            模板元数据，如果不存在则返回 None
        """
        return self._templates.get(template_id)
    
    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[TemplateMetadata]:
        """
        列出模板
        
        Args:
            category: 过滤类别
            tags: 过滤标签
        
        Returns:
            模板列表
        """
        templates = list(self._templates.values())
        
        # 按类别过滤
        if category:
            templates = [t for t in templates if t.category == category]
        
        # 按标签过滤
        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]
        
        return templates
    
    def search_templates(self, query: str) -> List[TemplateMetadata]:
        """
        搜索模板
        
        Args:
            query: 搜索关键词
        
        Returns:
            匹配的模板列表
        """
        query_lower = query.lower()
        results = []
        
        for template in self._templates.values():
            # 搜索名称、描述、标签
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return results
```

### 2. TemplateRenderer

模板渲染器，将模板渲染为 SKILL.md 文件。

```python
from jinja2 import Environment, FileSystemLoader, Template
from typing import Dict, Any

class TemplateRenderer:
    """模板渲染器"""
    
    def __init__(self, templates_dir: Path):
        """
        初始化模板渲染器
        
        Args:
            templates_dir: 模板目录路径
        """
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # 注册自定义过滤器
        self.env.filters['kebab_case'] = self._kebab_case
        self.env.filters['snake_case'] = self._snake_case
    
    def render(
        self,
        template_id: str,
        parameters: Dict[str, Any],
    ) -> str:
        """
        渲染模板
        
        Args:
            template_id: 模板 ID
            parameters: 模板参数
        
        Returns:
            渲染后的 SKILL.md 内容
        """
        # 加载模板
        template_path = self._get_template_path(template_id)
        template = self.env.get_template(str(template_path.relative_to(self.templates_dir)))
        
        # 渲染模板
        content = template.render(**parameters)
        
        return content
    
    def _get_template_path(self, template_id: str) -> Path:
        """获取模板文件路径"""
        # template_id 格式：category/template-name
        return self.templates_dir / f"{template_id}.md.j2"
    
    @staticmethod
    def _kebab_case(text: str) -> str:
        """转换为 kebab-case"""
        import re
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        return text.lower()
    
    @staticmethod
    def _snake_case(text: str) -> str:
        """转换为 snake_case"""
        import re
        text = re.sub(r'[^\w\s_]', '', text)
        text = re.sub(r'[\s-]+', '_', text)
        return text.lower()
```

### 3. TemplateValidator

模板验证器，验证模板和生成的 SKILL.md 文件。

```python
from typing import List, Tuple
import yaml
import re

@dataclass
class ValidationError:
    """验证错误"""
    field: str  # 错误字段
    message: str  # 错误信息
    severity: str  # 严重程度：error, warning

class TemplateValidator:
    """模板验证器"""
    
    def validate_template(self, template_path: Path) -> List[ValidationError]:
        """
        验证模板文件
        
        Args:
            template_path: 模板文件路径
        
        Returns:
            验证错误列表
        """
        errors = []
        
        # 读取模板内容
        content = template_path.read_text(encoding='utf-8')
        
        # 验证元数据注释块存在
        if not re.search(r'\{#.*?#\}', content, re.DOTALL):
            errors.append(ValidationError(
                field="metadata",
                message="Template missing metadata comment block",
                severity="error",
            ))
        
        # 验证 Jinja2 语法
        try:
            from jinja2 import Environment
            env = Environment()
            env.parse(content)
        except Exception as e:
            errors.append(ValidationError(
                field="syntax",
                message=f"Invalid Jinja2 syntax: {e}",
                severity="error",
            ))
        
        return errors
    
    def validate_skill_file(self, skill_path: Path) -> List[ValidationError]:
        """
        验证生成的 SKILL.md 文件
        
        Args:
            skill_path: SKILL.md 文件路径
        
        Returns:
            验证错误列表
        """
        errors = []
        
        # 读取文件内容
        content = skill_path.read_text(encoding='utf-8')
        
        # 分离 frontmatter 和 body
        frontmatter, body = self._parse_skill_file(content)
        
        # 验证 frontmatter
        errors.extend(self._validate_frontmatter(frontmatter))
        
        # 验证 body
        errors.extend(self._validate_body(body))
        
        return errors
    
    def _parse_skill_file(self, content: str) -> Tuple[Dict[str, Any], str]:
        """解析 SKILL.md 文件"""
        # 提取 frontmatter（YAML 块）
        match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not match:
            return {}, content
        
        frontmatter_str, body = match.groups()
        frontmatter = yaml.safe_load(frontmatter_str)
        
        return frontmatter, body
    
    def _validate_frontmatter(self, frontmatter: Dict[str, Any]) -> List[ValidationError]:
        """验证 frontmatter"""
        errors = []
        
        # 验证必需字段
        required_fields = ['name', 'description']
        for field in required_fields:
            if field not in frontmatter:
                errors.append(ValidationError(
                    field=field,
                    message=f"Missing required field: {field}",
                    severity="error",
                ))
        
        # 验证 name 格式（kebab-case）
        if 'name' in frontmatter:
            name = frontmatter['name']
            if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
                errors.append(ValidationError(
                    field="name",
                    message=f"Name must be in kebab-case format: {name}",
                    severity="error",
                ))
        
        # 验证 owlclaw 扩展字段
        if 'owlclaw' in frontmatter:
            owlclaw = frontmatter['owlclaw']
            
            # 验证 spec_version
            if 'spec_version' not in owlclaw:
                errors.append(ValidationError(
                    field="owlclaw.spec_version",
                    message="Missing owlclaw.spec_version",
                    severity="warning",
                ))
            
            # 验证 trigger 格式
            if 'trigger' in owlclaw:
                trigger = owlclaw['trigger']
                if not self._validate_trigger_syntax(trigger):
                    errors.append(ValidationError(
                        field="owlclaw.trigger",
                        message=f"Invalid trigger syntax: {trigger}",
                        severity="error",
                    ))
        
        return errors
    
    def _validate_body(self, body: str) -> List[ValidationError]:
        """验证 Markdown body"""
        errors = []
        
        # 验证至少有一个标题
        if not re.search(r'^#+\s+', body, re.MULTILINE):
            errors.append(ValidationError(
                field="body",
                message="Body should contain at least one heading",
                severity="warning",
            ))
        
        # 验证内容不为空
        if not body.strip():
            errors.append(ValidationError(
                field="body",
                message="Body is empty",
                severity="error",
            ))
        
        return errors
    
    def _validate_trigger_syntax(self, trigger: str) -> bool:
        """验证 trigger 语法"""
        # 支持的格式：
        # - cron("* * * * *")
        # - webhook("/path")
        # - queue("queue-name")
        
        patterns = [
            r'^cron\(".*?"\)$',
            r'^webhook\(".*?"\)$',
            r'^queue\(".*?"\)$',
        ]
        
        return any(re.match(pattern, trigger) for pattern in patterns)
```


### 4. TemplateSearcher

模板搜索引擎，支持智能搜索和推荐。

```python
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class SearchResult:
    """搜索结果"""
    template: TemplateMetadata
    score: float  # 相关性分数 0-1
    match_reason: str  # 匹配原因

class TemplateSearcher:
    """模板搜索器"""
    
    def __init__(self, registry: TemplateRegistry):
        """
        初始化搜索器
        
        Args:
            registry: 模板注册表
        """
        self.registry = registry
    
    def search(
        self,
        query: str,
        category: Optional[TemplateCategory] = None,
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        搜索模板
        
        Args:
            query: 搜索关键词
            category: 过滤类别
            limit: 返回结果数量限制
        
        Returns:
            搜索结果列表，按相关性排序
        """
        # 获取候选模板
        candidates = self.registry.list_templates(category=category)
        
        # 计算相关性分数
        results = []
        for template in candidates:
            score, reason = self._calculate_relevance(query, template)
            if score > 0:
                results.append(SearchResult(
                    template=template,
                    score=score,
                    match_reason=reason,
                ))
        
        # 按分数排序
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results[:limit]
    
    def _calculate_relevance(
        self,
        query: str,
        template: TemplateMetadata,
    ) -> Tuple[float, str]:
        """
        计算相关性分数
        
        Args:
            query: 搜索关键词
            template: 模板元数据
        
        Returns:
            (分数, 匹配原因)
        """
        query_lower = query.lower()
        score = 0.0
        reasons = []
        
        # 名称完全匹配：1.0
        if query_lower == template.name.lower():
            score += 1.0
            reasons.append("exact name match")
        # 名称包含：0.8
        elif query_lower in template.name.lower():
            score += 0.8
            reasons.append("name contains query")
        
        # 描述包含：0.5
        if query_lower in template.description.lower():
            score += 0.5
            reasons.append("description contains query")
        
        # 标签匹配：0.6 per tag
        for tag in template.tags:
            if query_lower in tag.lower():
                score += 0.6
                reasons.append(f"tag match: {tag}")
        
        # 类别匹配：0.3
        if query_lower in template.category.value.lower():
            score += 0.3
            reasons.append("category match")
        
        reason = ", ".join(reasons) if reasons else "no match"
        return min(score, 1.0), reason
    
    def recommend(
        self,
        context: Dict[str, Any],
        limit: int = 5,
    ) -> List[SearchResult]:
        """
        推荐模板
        
        根据上下文信息推荐合适的模板
        
        Args:
            context: 上下文信息，如：
                - use_case: 使用场景描述
                - existing_skills: 已有的 skills
                - tech_stack: 技术栈
            limit: 返回结果数量限制
        
        Returns:
            推荐结果列表
        """
        # 基于上下文推荐
        # 实现推荐算法...
        pass
```

## 数据模型

### 模板文件格式

每个模板文件包含两部分：

1. **元数据注释块**：Jinja2 注释格式，包含模板元数据
2. **模板内容**：Jinja2 模板，包含 SKILL.md 的结构和占位符

#### 示例：monitoring/health-check.md.j2

```jinja2
{#
name: Health Check Monitor
description: Monitor system health and alert on issues
tags: [monitoring, health, alert, cron]
parameters:
  - name: skill_name
    type: str
    description: Skill name in kebab-case
    required: true
  - name: skill_description
    type: str
    description: Skill description
    required: true
  - name: check_interval
    type: int
    description: Check interval in seconds
    default: 60
  - name: alert_threshold
    type: int
    description: Alert threshold (number of failures)
    default: 3
  - name: endpoints
    type: list
    description: List of endpoints to check
    default: []
examples:
  - "Monitor API health every 60 seconds"
  - "Check database connectivity and alert on failure"
#}
---
name: {{ skill_name }}
description: {{ skill_description }}
metadata:
  author: {{ author | default("team-name") }}
  version: "1.0"
owlclaw:
  spec_version: "1.0"
  task_type: monitoring
  constraints:
    max_daily_calls: 1440  # 每分钟一次
  trigger: cron("*/{{ check_interval }} * * * * *")
---

# {{ skill_description }}

## 目标

监控系统健康状态，在检测到问题时及时告警。

## 检查项

{% if endpoints %}
检查以下端点的健康状态：

{% for endpoint in endpoints %}
- {{ endpoint }}
{% endfor %}
{% else %}
请在 `endpoints` 参数中配置需要检查的端点。
{% endif %}

## 告警策略

- 连续失败 {{ alert_threshold }} 次后触发告警
- 告警方式：日志记录 + 通知

## 使用的工具

- `query_state`: 查询上次检查状态
- `log_decision`: 记录检查结果
- `schedule_once`: 在检测到问题时安排立即复查

## 决策流程

1. 检查所有配置的端点
2. 记录检查结果到状态
3. 如果连续失败次数达到阈值，触发告警
4. 如果检测到恢复，清除失败计数

## 注意事项

- 避免过于频繁的检查，建议间隔至少 30 秒
- 告警阈值应根据系统稳定性调整
- 考虑使用指数退避策略处理持续失败的情况
```

### 生成的 SKILL.md 示例

```markdown
---
name: api-health-monitor
description: Monitor API endpoints health and alert on failures
metadata:
  author: platform-team
  version: "1.0"
owlclaw:
  spec_version: "1.0"
  task_type: monitoring
  constraints:
    max_daily_calls: 1440
  trigger: cron("*/60 * * * * *")
---

# Monitor API endpoints health and alert on failures

## 目标

监控系统健康状态，在检测到问题时及时告警。

## 检查项

检查以下端点的健康状态：

- https://api.example.com/health
- https://api.example.com/db/health

## 告警策略

- 连续失败 3 次后触发告警
- 告警方式：日志记录 + 通知

## 使用的工具

- `query_state`: 查询上次检查状态
- `log_decision`: 记录检查结果
- `schedule_once`: 在检测到问题时安排立即复查

## 决策流程

1. 检查所有配置的端点
2. 记录检查结果到状态
3. 如果连续失败次数达到阈值，触发告警
4. 如果检测到恢复，清除失败计数

## 注意事项

- 避免过于频繁的检查，建议间隔至少 30 秒
- 告警阈值应根据系统稳定性调整
- 考虑使用指数退避策略处理持续失败的情况
```


## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：模板注册完整性

*对于任意* 模板目录，当系统加载模板时，所有有效的 `.md.j2` 文件都应该被注册到模板注册表中，并且每个模板都应该有唯一的 ID。

**验证需求：FR-1.1**

### 属性 2：模板元数据完整性

*对于任意* 注册的模板，该模板的元数据应该包含所有必需字段（id、name、category、description、tags、parameters、file_path），并且这些字段的值应该是有效的。

**验证需求：FR-1.2**

### 属性 3：模板分类正确性

*对于任意* 模板，该模板的类别应该与其所在目录的名称一致，并且类别应该是预定义的五个类别之一（monitoring、analysis、workflow、integration、report）。

**验证需求：FR-1.3**

### 属性 4：模板参数定义完整性

*对于任意* 模板参数，该参数应该包含名称、类型、描述和是否必需的信息，并且类型应该是支持的类型之一（str、int、bool、list）。

**验证需求：FR-1.4**

### 属性 5：模板渲染幂等性

*对于任意* 模板和参数集合，使用相同的参数多次渲染同一个模板应该产生相同的输出。

**验证需求：FR-2.1**

### 属性 6：模板参数替换完整性

*对于任意* 模板和参数集合，渲染后的输出应该不包含未替换的 Jinja2 占位符（如 `{{ variable }}`），除非该占位符在条件块中且条件未满足。

**验证需求：FR-2.2**

### 属性 7：必需参数验证

*对于任意* 模板，如果缺少必需参数，渲染操作应该失败并返回明确的错误信息，指出缺少哪个参数。

**验证需求：FR-2.3**

### 属性 8：默认参数应用

*对于任意* 模板参数，如果该参数有默认值且未提供值，渲染时应该使用默认值。

**验证需求：FR-2.4**

### 属性 9：生成文件 frontmatter 有效性

*对于任意* 渲染后的 SKILL.md 文件，该文件的 frontmatter 应该是有效的 YAML 格式，并且包含所有必需字段（name、description）。

**验证需求：FR-3.1**

### 属性 10：生成文件 name 格式正确性

*对于任意* 渲染后的 SKILL.md 文件，frontmatter 中的 `name` 字段应该符合 kebab-case 格式（小写字母、数字和连字符）。

**验证需求：FR-3.2**

### 属性 11：生成文件 trigger 语法正确性

*对于任意* 包含 `owlclaw.trigger` 字段的 SKILL.md 文件，该字段的值应该符合支持的 trigger 语法之一（cron、webhook、queue）。

**验证需求：FR-3.3**

### 属性 12：生成文件 body 非空性

*对于任意* 渲染后的 SKILL.md 文件，Markdown body 部分应该不为空，并且至少包含一个标题。

**验证需求：FR-3.4**

### 属性 13：搜索结果相关性

*对于任意* 搜索查询，返回的结果应该按相关性分数降序排列，并且分数最高的结果应该与查询最相关。

**验证需求：FR-4.1**

### 属性 14：搜索结果唯一性

*对于任意* 搜索查询，返回的结果列表中不应该包含重复的模板。

**验证需求：FR-4.2**

### 属性 15：类别过滤正确性

*对于任意* 类别过滤条件，返回的模板列表中所有模板的类别都应该与过滤条件匹配。

**验证需求：FR-4.3**

### 属性 16：标签过滤正确性

*对于任意* 标签过滤条件，返回的模板列表中所有模板都应该至少包含一个匹配的标签。

**验证需求：FR-4.4**

### 属性 17：模板文件 Jinja2 语法有效性

*对于任意* 模板文件，该文件应该是有效的 Jinja2 模板，能够被 Jinja2 解析器解析而不抛出语法错误。

**验证需求：FR-5.1**

### 属性 18：模板文件元数据注释块存在性

*对于任意* 模板文件，该文件应该包含元数据注释块（`{# ... #}` 格式），并且注释块应该在文件开头。

**验证需求：FR-5.2**

### 属性 19：验证错误信息明确性

*对于任意* 验证失败的情况，验证器应该返回明确的错误信息，包含错误字段、错误描述和严重程度。

**验证需求：FR-5.3**

### 属性 20：Kebab-case 转换正确性

*对于任意* 字符串，kebab-case 过滤器应该将其转换为小写字母、数字和连字符组成的字符串，并且连字符不应该出现在开头或结尾。

**验证需求：FR-2.5**

### 属性 21：Snake-case 转换正确性

*对于任意* 字符串，snake-case 过滤器应该将其转换为小写字母、数字和下划线组成的字符串，并且下划线不应该出现在开头或结尾。

**验证需求：FR-2.6**

### 属性 22：模板列表完整性

*对于任意* 类别，列出该类别的模板时，返回的列表应该包含该类别目录下所有有效的模板文件。

**验证需求：FR-1.5**

### 属性 23：参数类型验证

*对于任意* 模板参数，如果提供的参数值类型与参数定义的类型不匹配，渲染操作应该失败或自动进行类型转换。

**验证需求：FR-2.7**

### 属性 24：参数选项验证

*对于任意* 带有 `choices` 限制的模板参数，如果提供的参数值不在选项列表中，渲染操作应该失败并返回明确的错误信息。

**验证需求：FR-2.8**

### 属性 25：模板搜索覆盖性

*对于任意* 模板，如果搜索查询包含该模板的名称、描述或标签中的关键词，该模板应该出现在搜索结果中。

**验证需求：FR-4.5**


## 错误处理

### 1. 模板文件不存在

**场景**：请求的模板 ID 对应的文件不存在

**处理策略**：
- 返回 None 或抛出 `TemplateNotFoundError`
- 记录警告日志
- 向用户提供可用模板列表

**实现**：
```python
def get_template(self, template_id: str) -> Optional[TemplateMetadata]:
    if template_id not in self._templates:
        logger.warning(f"Template not found: {template_id}")
        return None
    return self._templates[template_id]
```

### 2. 模板语法错误

**场景**：模板文件包含无效的 Jinja2 语法

**处理策略**：
- 在加载时验证模板语法
- 跳过无效的模板并记录错误
- 不影响其他模板的加载

**实现**：
```python
def _load_templates(self) -> None:
    for template_file in self._find_template_files():
        try:
            self._validate_template_syntax(template_file)
            metadata = self._parse_template_metadata(template_file)
            self._templates[metadata.id] = metadata
        except Exception as e:
            logger.error(f"Failed to load template {template_file}: {e}")
            # 继续加载其他模板
```

### 3. 缺少必需参数

**场景**：渲染模板时缺少必需参数

**处理策略**：
- 在渲染前验证参数
- 抛出 `MissingParameterError` 并列出缺少的参数
- 不执行渲染操作

**实现**：
```python
def render(self, template_id: str, parameters: Dict[str, Any]) -> str:
    template_meta = self.registry.get_template(template_id)
    
    # 验证必需参数
    missing = []
    for param in template_meta.parameters:
        if param.required and param.name not in parameters:
            if param.default is None:
                missing.append(param.name)
    
    if missing:
        raise MissingParameterError(
            f"Missing required parameters: {', '.join(missing)}"
        )
    
    # 应用默认值
    for param in template_meta.parameters:
        if param.name not in parameters and param.default is not None:
            parameters[param.name] = param.default
    
    # 渲染模板
    return self._render_template(template_id, parameters)
```

### 4. 参数类型错误

**场景**：提供的参数类型与定义不匹配

**处理策略**：
- 尝试自动类型转换
- 如果转换失败，抛出 `ParameterTypeError`
- 记录详细的错误信息

**实现**：
```python
def _validate_and_convert_parameters(
    self,
    parameters: Dict[str, Any],
    param_defs: List[TemplateParameter],
) -> Dict[str, Any]:
    converted = {}
    
    for param_def in param_defs:
        if param_def.name not in parameters:
            continue
        
        value = parameters[param_def.name]
        
        try:
            # 尝试类型转换
            if param_def.type == 'int':
                converted[param_def.name] = int(value)
            elif param_def.type == 'bool':
                converted[param_def.name] = bool(value)
            elif param_def.type == 'list':
                if not i
                    isinstance(value, list):
                    raise ParameterTypeError(
                        param_def.name,
                        param_def.type,
                        type(value).__name__,
                    )
                converted[param_def.name] = value
            else:
                converted[param_def.name] = str(value)
        except (ValueError, TypeError) as e:
            raise ParameterTypeError(
                param_def.name,
                param_def.type,
                type(value).__name__,
                str(e),
            )
    
    return converted
```

### 5. 参数选项验证错误

**场景**：参数值不在允许的选项列表中

**处理策略**：
- 检查参数是否有 `choices` 限制
- 如果值不在选项中，抛出 `ParameterValueError`
- 在错误信息中列出所有有效选项

**实现**：
```python
def _validate_parameter_choices(
    self,
    parameters: Dict[str, Any],
    param_defs: List[TemplateParameter],
) -> None:
    for param_def in param_defs:
        if param_def.choices is None:
            continue
        
        if param_def.name not in parameters:
            continue
        
        value = parameters[param_def.name]
        
        if value not in param_def.choices:
            raise ParameterValueError(
                param_def.name,
                value,
                param_def.choices,
                f"Value '{value}' is not in allowed choices: {param_def.choices}",
            )
```

### 6. 模板渲染错误

**场景**：Jinja2 渲染过程中出现错误

**处理策略**：
- 捕获 Jinja2 异常
- 转换为 `TemplateRenderError`
- 提供模板位置和错误上下文

**实现**：
```python
from jinja2 import TemplateError as Jinja2TemplateError

def render(
    self,
    template_id: str,
    parameters: Dict[str, Any],
) -> str:
    try:
        template_path = self._get_template_path(template_id)
        template = self.env.get_template(
            str(template_path.relative_to(self.templates_dir))
        )
        content = template.render(**parameters)
        return content
    except Jinja2TemplateError as e:
        raise TemplateRenderError(
            template_id,
            str(e),
            e.lineno if hasattr(e, 'lineno') else None,
        )
```

### 7. 文件系统错误

**场景**：模板文件不存在或无法读取

**处理策略**：
- 检查文件是否存在
- 检查文件权限
- 提供清晰的错误信息

**实现**：
```python
def _get_template_path(self, template_id: str) -> Path:
    template_path = self.templates_dir / f"{template_id}.md.j2"
    
    if not template_path.exists():
        raise TemplateNotFoundError(
            template_id,
            f"Template file not found: {template_path}",
        )
    
    if not template_path.is_file():
        raise TemplateError(
            template_id,
            f"Template path is not a file: {template_path}",
        )
    
    return template_path
```

### 8. 验证错误处理

**场景**：生成的 SKILL.md 文件验证失败

**处理策略**：
- 收集所有验证错误
- 按严重程度分类（error/warning）
- 提供修复建议

**实现**：
```python
def validate_and_report(self, skill_path: Path) -> bool:
    errors = self.validate_skill_file(skill_path)
    
    if not errors:
        print(f"✓ {skill_path} is valid")
        return True
    
    # 分类错误
    critical_errors = [e for e in errors if e.severity == "error"]
    warnings = [e for e in errors if e.severity == "warning"]
    
    # 报告错误
    if critical_errors:
        print(f"✗ {skill_path} has {len(critical_errors)} error(s):")
        for error in critical_errors:
            print(f"  - {error.field}: {error.message}")
    
    if warnings:
        print(f"⚠ {skill_path} has {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  - {warning.field}: {warning.message}")
    
    return len(critical_errors) == 0
```

## 测试策略

### 测试方法

本设计采用双重测试策略：

1. **单元测试**：验证特定示例、边界情况和错误条件
2. **属性测试**：验证跨所有输入的通用属性

两者互补，共同提供全面覆盖：
- 单元测试捕获具体错误
- 属性测试验证通用正确性

### 属性测试配置

使用 Hypothesis 作为 Python 的属性测试库。

配置要求：
- 每个属性测试最少运行 100 次迭代
- 每个测试必须引用设计文档中的属性
- 标签格式：`# Feature: skill-templates, Property {number}: {property_text}`

### 单元测试

**测试范围**：
- 模板加载和注册
- 参数验证和类型转换
- 模板渲染
- 文件验证
- 错误处理

**示例测试用例**：

```python
import pytest
from pathlib import Path
from owlclaw.templates.skills import (
    TemplateRegistry,
    TemplateRenderer,
    TemplateValidator,
    TemplateNotFoundError,
    MissingParameterError,
)

class TestTemplateRegistry:
    def test_load_templates_from_directory(self, tmp_path):
        """测试从目录加载模板"""
        # 创建测试模板
        monitoring_dir = tmp_path / "monitoring"
        monitoring_dir.mkdir()
        (monitoring_dir / "test.md.j2").write_text(
            "{# name: Test Template\ndescription: Test\ntags: [test] #}\n"
            "---\nname: {{ name }}\n---\n# Test"
        )
        
        registry = TemplateRegistry(tmp_path)
        templates = registry.list_templates()
        
        assert len(templates) == 1
        assert templates[0].id == "monitoring/test"
    
    def test_get_template_by_id(self, registry):
        """测试通过 ID 获取模板"""
        template = registry.get_template("monitoring/health-check")
        
        assert template is not None
        assert template.name == "Health Check Monitor"
        assert template.category.value == "monitoring"
    
    def test_search_templates(self, registry):
        """测试搜索模板"""
        results = registry.search_templates("health")
        
        assert len(results) > 0
        assert any("health" in t.name.lower() for t in results)

class TestTemplateRenderer:
    def test_render_template_with_parameters(self, renderer):
        """测试使用参数渲染模板"""
        content = renderer.render(
            "monitoring/health-check",
            {
                "skill_name": "api-health",
                "skill_description": "Monitor API health",
                "check_interval": 60,
            }
        )
        
        assert "name: api-health" in content
        assert "Monitor API health" in content
        assert "60" in content
    
    def test_render_missing_required_parameter(self, renderer):
        """测试缺少必需参数"""
        with pytest.raises(MissingParameterError) as exc_info:
            renderer.render(
                "monitoring/health-check",
                {"skill_name": "test"}  # 缺少 skill_description
            )
        
        assert "skill_description" in str(exc_info.value)
    
    def test_render_with_default_parameters(self, renderer):
        """测试使用默认参数"""
        content = renderer.render(
            "monitoring/health-check",
            {
                "skill_name": "test",
                "skill_description": "Test",
                # check_interval 使用默认值 60
            }
        )
        
        assert "60" in content  # 默认值


class TestTemplateValidator:
    def test_validate_valid_skill_file(self, validator, tmp_path):
        """测试验证有效的 SKILL.md 文件"""
        skill_file = tmp_path / "test-skill.md"
        skill_file.write_text("""---
name: test-skill
description: Test skill
owlclaw:
  spec_version: "1.0"
---

# Test Skill

This is a test skill.
""")
        
        errors = validator.validate_skill_file(skill_file)
        assert len(errors) == 0
    
    def test_validate_missing_required_field(self, validator, tmp_path):
        """测试验证缺少必需字段"""
        skill_file = tmp_path / "test-skill.md"
        skill_file.write_text("""---
name: test-skill
# 缺少 description
---

# Test
""")
        
        errors = validator.validate_skill_file(skill_file)
        assert any(e.field == "description" for e in errors)
    
    def test_validate_invalid_name_format(self, validator, tmp_path):
        """测试验证无效的名称格式"""
        skill_file = tmp_path / "test-skill.md"
        skill_file.write_text("""---
name: TestSkill  # 应该是 kebab-case
description: Test
---

# Test
""")
        
        errors = validator.validate_skill_file(skill_file)
        assert any(e.field == "name" and "kebab-case" in e.message for e in errors)
```

### 属性测试

**测试范围**：
- 模板注册完整性
- 渲染幂等性
- 参数验证
- 搜索正确性
- 格式转换

**示例属性测试**：

```python
from hypothesis import given, strategies as st, settings
from owlclaw.templates.skills import TemplateRegistry, TemplateRenderer

# Feature: skill-templates, Property 5: 模板渲染幂等性
@given(
    skill_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    skill_description=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    check_interval=st.integers(min_value=10, max_value=3600),
)
@settings(max_examples=100)
def test_render_idempotency(renderer, skill_name, skill_description, check_interval):
    """
    属性 5：对于任意模板和参数集合，使用相同的参数多次渲染同一个模板应该产生相同的输出
    """
    parameters = {
        "skill_name": skill_name,
        "skill_description": skill_description,
        "check_interval": check_interval,
    }
    
    result1 = renderer.render("monitoring/health-check", parameters)
    result2 = renderer.render("monitoring/health-check", parameters)
    
    assert result1 == result2

# Feature: skill-templates, Property 20: Kebab-case 转换正确性
@given(text=st.text(min_size=1, max_size=100))
@settings(max_examples=100)
def test_kebab_case_conversion(text):
    """
    属性 20：对于任意字符串，kebab-case 过滤器应该将其转换为小写字母、数字和连字符组成的字符串
    """
    from owlclaw.templates.skills.renderer import TemplateRenderer
    
    result = TemplateRenderer._kebab_case(text)
    
    # 验证只包含小写字母、数字和连字符
    assert all(c.islower() or c.isdigit() or c == '-' for c in result)
    # 验证不以连字符开头或结尾
    if result:
        assert not result.startswith('-')
        assert not result.endswith('-')


# Feature: skill-templates, Property 13: 搜索结果相关性
@given(
    query=st.text(min_size=1, max_size=50),
)
@settings(max_examples=100)
def test_search_results_relevance_ordering(registry, query):
    """
    属性 13：对于任意搜索查询，返回的结果应该按相关性分数降序排列
    """
    from owlclaw.templates.skills import TemplateSearcher
    
    searcher = TemplateSearcher(registry)
    results = searcher.search(query)
    
    # 验证结果按分数降序排列
    for i in range(len(results) - 1):
        assert results[i].score >= results[i+1].score

# Feature: skill-templates, Property 14: 搜索结果唯一性
@given(
    query=st.text(min_size=1, max_size=50),
)
@settings(max_examples=100)
def test_search_results_uniqueness(registry, query):
    """
    属性 14：对于任意搜索查询，返回的结果列表中不应该包含重复的模板
    """
    from owlclaw.templates.skills import TemplateSearcher
    
    searcher = TemplateSearcher(registry)
    results = searcher.search(query)
    
    # 验证没有重复的模板 ID
    template_ids = [r.template.id for r in results]
    assert len(template_ids) == len(set(template_ids))

# Feature: skill-templates, Property 23: 参数类型验证
@given(
    int_value=st.one_of(st.integers(), st.text(), st.floats()),
)
@settings(max_examples=100)
def test_parameter_type_conversion(renderer, int_value):
    """
    属性 23：对于任意模板参数，如果提供的参数值类型与参数定义的类型不匹配，
    渲染操作应该失败或自动进行类型转换
    """
    from owlclaw.templates.skills import ParameterTypeError
    
    parameters = {
        "skill_name": "test",
        "skill_description": "Test",
        "check_interval": int_value,  # 应该是 int 类型
    }
    
    try:
        result = renderer.render("monitoring/health-check", parameters)
        # 如果成功，验证值已被转换为 int
        assert isinstance(int_value, int) or str(int(int_value)) in result
    except (ParameterTypeError, ValueError):
        # 如果失败，应该是因为无法转换
        assert not isinstance(int_value, int)
```

### 集成测试

**测试范围**：
- CLI 集成
- 端到端工作流
- 文件系统操作

**示例集成测试**：

```python
def test_end_to_end_template_workflow(tmp_path):
    """测试完整的模板工作流"""
    # 1. 初始化注册表
    templates_dir = Path("owlclaw/templates/skills/templates")
    registry = TemplateRegistry(templates_dir)
    
    # 2. 搜索模板
    searcher = TemplateSearcher(registry)
    results = searcher.search("health")
    assert len(results) > 0
    
    # 3. 选择模板
    template = results[0].template
    
    # 4. 渲染模板
    renderer = TemplateRenderer(templates_dir)
    content = renderer.render(
        template.id,
        {
            "skill_name": "test-health-check",
            "skill_description": "Test health monitoring",
            "check_interval": 60,
        }
    )
    
    # 5. 写入文件
    output_file = tmp_path / "test-health-check.md"
    output_file.write_text(content)
    
    # 6. 验证文件
    validator = TemplateValidator()
    errors = validator.validate_skill_file(output_file)
    assert len(errors) == 0
```


### 测试覆盖率目标

- 单元测试覆盖率：> 80%
- 属性测试：覆盖所有 25 个正确性属性
- 集成测试：覆盖核心场景

## 部署考虑

### 打包和分发

**模板文件打包**：
- 模板文件作为 Python 包的一部分分发
- 使用 `package_data` 包含模板文件
- 确保模板文件在安装后可访问

**setup.py 配置**：
```python
setup(
    name="owlclaw",
    packages=find_packages(),
    package_data={
        "owlclaw.templates.skills": [
            "templates/**/*.md.j2",
        ],
    },
    include_package_data=True,
)
```

### 模板版本管理

**版本策略**：
- 模板库使用语义化版本
- 每个模板包含版本信息
- 支持模板向后兼容

**版本检查**：
```python
@dataclass
class TemplateMetadata:
    # ... 其他字段
    template_version: str  # 模板版本，如 "1.0.0"
    min_owlclaw_version: str  # 最低 OwlClaw 版本要求

def check_compatibility(template: TemplateMetadata) -> bool:
    """检查模板与当前 OwlClaw 版本的兼容性"""
    from packaging import version
    import owlclaw
    
    current_version = version.parse(owlclaw.__version__)
    min_version = version.parse(template.min_owlclaw_version)
    
    return current_version >= min_version
```

### 模板更新机制

**更新策略**：
- 支持在线更新模板库
- 提供模板更新通知
- 允许用户选择模板版本

**实现**：
```python
class TemplateUpdater:
    """模板更新器"""
    
    def check_updates(self) -> List[TemplateUpdate]:
        """检查可用的模板更新"""
        # 从远程仓库获取最新模板信息
        # 比较本地和远程版本
        # 返回可更新的模板列表
        pass
    
    def update_template(self, template_id: str) -> bool:
        """更新指定模板"""
        # 下载最新模板文件
        # 备份旧版本
        # 替换模板文件
        # 更新注册表
        pass
```


## 性能考虑

### 模板加载性能

**优化策略**：
- 延迟加载：只在需要时加载模板内容
- 缓存：缓存已解析的模板元数据
- 索引：建立模板索引加速搜索

**实现**：
```python
class TemplateRegistry:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self._templates: Dict[str, TemplateMetadata] = {}
        self._template_cache: Dict[str, Template] = {}
        self._search_index: Dict[str, Set[str]] = {}
        
        self._load_templates()
        self._build_search_index()
    
    def _build_search_index(self) -> None:
        """构建搜索索引"""
        for template_id, template in self._templates.items():
            # 索引名称
            for word in template.name.lower().split():
                self._search_index.setdefault(word, set()).add(template_id)
            
            # 索引标签
            for tag in template.tags:
                self._search_index.setdefault(tag.lower(), set()).add(template_id)
    
    def search_templates(self, query: str) -> List[TemplateMetadata]:
        """使用索引加速搜索"""
        query_lower = query.lower()
        matching_ids = self._search_index.get(query_lower, set())
        
        return [self._templates[tid] for tid in matching_ids]
```

### 渲染性能

**优化策略**：
- 模板预编译：使用 Jinja2 的编译缓存
- 参数验证优化：只验证必要的参数
- 批量渲染：支持批量渲染多个模板

**实现**：
```python
from jinja2 import Environment, FileSystemLoader
from jinja2.ext import Extension

class TemplateRenderer:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=False,  # 禁用自动重载以提高性能
            cache_size=400,  # 增加缓存大小
        )
    
    def render_batch(
        self,
        templates: List[Tuple[str, Dict[str, Any]]],
    ) -> List[str]:
        """批量渲染模板"""
        results = []
        for template_id, parameters in templates:
            results.append(self.render(template_id, parameters))
        return results
```

### 内存使用

**优化策略**：
- 流式处理：对大型模板使用流式渲染
- 及时释放：渲染完成后释放不需要的资源
- 限制缓存大小：避免缓存过多模板

**监控**：
```python
import psutil
import logging

class PerformanceMonitor:
    """性能监控器"""
    
    @staticmethod
    def log_memory_usage(operation: str):
        """记录内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        logging.info(
            f"{operation}: RSS={memory_info.rss / 1024 / 1024:.2f}MB, "
            f"VMS={memory_info.vms / 1024 / 1024:.2f}MB"
        )
```


## 安全考虑

### 模板注入防护

**风险**：恶意用户可能通过参数注入恶意代码

**防护措施**：
- 参数白名单：只允许预定义的参数
- 输入验证：验证参数值的格式和内容
- 沙箱执行：在受限环境中渲染模板
- 禁用危险功能：禁用 Jinja2 的危险特性

**实现**：
```python
from jinja2.sandbox import SandboxedEnvironment

class SecureTemplateRenderer(TemplateRenderer):
    """安全的模板渲染器"""
    
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        # 使用沙箱环境
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # 注册安全的过滤器
        self.env.filters['kebab_case'] = self._kebab_case
        self.env.filters['snake_case'] = self._snake_case
    
    def _validate_parameter_safety(
        self,
        parameters: Dict[str, Any],
    ) -> None:
        """验证参数安全性"""
        for key, value in parameters.items():
            # 检查参数名
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise SecurityError(f"Invalid parameter name: {key}")
            
            # 检查参数值
            if isinstance(value, str):
                # 禁止包含危险字符
                if any(c in value for c in ['{{', '}}', '{%', '%}']):
                    raise SecurityError(
                        f"Parameter value contains dangerous characters: {key}"
                    )
```

### 文件系统安全

**风险**：路径遍历攻击

**防护措施**：
- 路径验证：确保所有路径在模板目录内
- 符号链接检查：拒绝符号链接
- 权限检查：验证文件权限

**实现**：
```python
def _validate_template_path(self, template_id: str) -> Path:
    """验证模板路径安全性"""
    template_path = self.templates_dir / f"{template_id}.md.j2"
    
    # 解析为绝对路径
    resolved_path = template_path.resolve()
    resolved_base = self.templates_dir.resolve()
    
    # 确保路径在模板目录内
    if not str(resolved_path).startswith(str(resolved_base)):
        raise SecurityError(
            f"Template path outside templates directory: {template_id}"
        )
    
    # 检查是否为符号链接
    if template_path.is_symlink():
        raise SecurityError(
            f"Template path is a symbolic link: {template_id}"
        )
    
    return template_path
```

### 输出验证

**风险**：生成的文件可能包含恶意内容

**防护措施**：
- 输出验证：验证生成的 SKILL.md 文件
- 内容过滤：过滤潜在的恶意内容
- 大小限制：限制生成文件的大小

**实现**：
```python
def render_safe(
    self,
    template_id: str,
    parameters: Dict[str, Any],
    max_size: int = 1024 * 1024,  # 1MB
) -> str:
    """安全渲染模板"""
    # 验证参数安全性
    self._validate_parameter_safety(parameters)
    
    # 渲染模板
    content = self.render(template_id, parameters)
    
    # 检查输出大小
    if len(content) > max_size:
        raise SecurityError(
            f"Rendered content exceeds maximum size: {len(content)} > {max_size}"
        )
    
    # 验证输出内容
    validator = TemplateValidator()
    errors = validator.validate_skill_content(content)
    if any(e.severity == "error" for e in errors):
        raise SecurityError("Rendered content failed validation")
    
    return content
```


## 可扩展性

### 自定义模板

**支持场景**：
- 用户自定义模板
- 团队特定模板
- 第三方模板

**实现**：
```python
class TemplateRegistry:
    def __init__(
        self,
        templates_dir: Path,
        custom_dirs: Optional[List[Path]] = None,
    ):
        """
        初始化模板注册表
        
        Args:
            templates_dir: 内置模板目录
            custom_dirs: 自定义模板目录列表
        """
        self.templates_dir = templates_dir
        self.custom_dirs = custom_dirs or []
        self._templates: Dict[str, TemplateMetadata] = {}
        
        # 加载内置模板
        self._load_templates_from_dir(templates_dir, builtin=True)
        
        # 加载自定义模板
        for custom_dir in self.custom_dirs:
            self._load_templates_from_dir(custom_dir, builtin=False)
    
    def add_custom_template(
        self,
        template_path: Path,
        category: TemplateCategory,
    ) -> TemplateMetadata:
        """添加自定义模板"""
        metadata = self._parse_template_metadata(template_path, category)
        metadata.custom = True
        self._templates[metadata.id] = metadata
        return metadata
```

### 模板继承

**支持场景**：
- 基于现有模板创建新模板
- 共享通用结构
- 覆盖特定部分

**实现**：
```python
# 基础模板：base-skill.md.j2
{#
name: Base Skill Template
description: Base template for all skills
tags: [base]
#}
---
name: {{ skill_name }}
description: {{ skill_description }}
metadata:
  author: {{ author | default("team-name") }}
  version: "1.0"
owlclaw:
  spec_version: "1.0"
{% block owlclaw_config %}
  # 子模板可以覆盖此块
{% endblock %}
---

{% block content %}
# {{ skill_description }}

## 目标

{{ objective | default("请描述此 skill 的目标") }}

{% block details %}
# 子模板可以覆盖此块
{% endblock %}
{% endblock %}

# 继承模板：monitoring/health-check.md.j2
{% extends "base-skill.md.j2" %}

{% block owlclaw_config %}
  task_type: monitoring
  constraints:
    max_daily_calls: 1440
  trigger: cron("*/{{ check_interval }} * * * * *")
{% endblock %}

{% block details %}
## 检查项

{% for endpoint in endpoints %}
- {{ endpoint }}
{% endfor %}

## 告警策略

- 连续失败 {{ alert_threshold }} 次后触发告警
{% endblock %}
```

### 插件系统

**支持场景**：
- 自定义过滤器
- 自定义验证器
- 自定义搜索算法

**实现**：
```python
from typing import Protocol

class TemplatePlugin(Protocol):
    """模板插件接口"""
    
    def register_filters(self, env: Environment) -> None:
        """注册自定义过滤器"""
        pass
    
    def register_validators(self, validator: TemplateValidator) -> None:
        """注册自定义验证器"""
        pass

class TemplateRegistry:
    def __init__(
        self,
        templates_dir: Path,
        plugins: Optional[List[TemplatePlugin]] = None,
    ):
        self.templates_dir = templates_dir
        self.plugins = plugins or []
        
        # 初始化插件
        for plugin in self.plugins:
            plugin.register_filters(self.env)
            plugin.register_validators(self.validator)

# 示例插件
class CustomFiltersPlugin:
    """自定义过滤器插件"""
    
    def register_filters(self, env: Environment) -> None:
        env.filters['camel_case'] = self._camel_case
        env.filters['pascal_case'] = self._pascal_case
    
    @staticmethod
    def _camel_case(text: str) -> str:
        words = text.replace('-', ' ').replace('_', ' ').split()
        return words[0].lower() + ''.join(w.capitalize() for w in words[1:])
    
    @staticmethod
    def _pascal_case(text: str) -> str:
        words = text.replace('-', ' ').replace('_', ' ').split()
        return ''.join(w.capitalize() for w in words)
```


## CLI 集成

### 命令设计

**主命令**：`owlclaw skill init`

**交互流程**：
1. 询问使用场景或搜索关键词
2. 展示匹配的模板列表
3. 选择模板
4. 收集模板参数
5. 渲染并保存 SKILL.md
6. 自动验证生成的文件

**实现**：
```python
import click
from pathlib import Path
from owlclaw.templates.skills import (
    TemplateRegistry,
    TemplateRenderer,
    TemplateValidator,
    TemplateSearcher,
)

@click.command()
@click.option(
    '--category',
    type=click.Choice(['monitoring', 'analysis', 'workflow', 'integration', 'report']),
    help='Filter templates by category',
)
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path),
    default=Path('capabilities'),
    help='Output directory for generated SKILL.md',
)
@click.option(
    '--no-validate',
    is_flag=True,
    help='Skip validation after generation',
)
def skill_init(category, output_dir, no_validate):
    """Initialize a new SKILL.md from template"""
    
    # 初始化组件
    templates_dir = Path(__file__).parent / 'templates' / 'skills' / 'templates'
    registry = TemplateRegistry(templates_dir)
    searcher = TemplateSearcher(registry)
    renderer = TemplateRenderer(templates_dir)
    validator = TemplateValidator()
    
    # 1. 搜索模板
    query = click.prompt('What kind of skill do you want to create?')
    results = searcher.search(query, category=category)
    
    if not results:
        click.echo('No templates found. Try a different search term.')
        return
    
    # 2. 展示模板列表
    click.echo('\nAvailable templates:')
    for i, result in enumerate(results[:10], 1):
        template = result.template
        click.echo(
            f'{i}. {template.name} ({template.category.value})\n'
            f'   {template.description}\n'
            f'   Match: {result.match_reason}\n'
        )
    
    # 3. 选择模板
    choice = click.prompt(
        'Select a template',
        type=click.IntRange(1, len(results[:10])),
    )
    selected_template = results[choice - 1].template
    
    # 4. 收集参数
    click.echo(f'\nConfiguring {selected_template.name}...')
    parameters = {}
    
    for param in selected_template.parameters:
        if param.required or click.confirm(f'Set {param.name}?', default=False):
            value = click.prompt(
                f'{param.name} ({param.description})',
                default=param.default,
                type=_get_click_type(param.type),
            )
            parameters[param.name] = value
    
    # 5. 渲染模板
    try:
        content = renderer.render(selected_template.id, parameters)
    except Exception as e:
        click.echo(f'Error rendering template: {e}', err=True)
        return
    
    # 6. 保存文件
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_name = parameters.get('skill_name', 'new-skill')
    output_file = output_dir / f'{skill_name}.md'
    
    output_file.write_text(content)
    click.echo(f'\n✓ Created {output_file}')
    
    # 7. 验证文件
    if not no_validate:
        errors = validator.validate_skill_file(output_file)
        if errors:
            click.echo('\n⚠ Validation warnings:')
            for error in errors:
                click.echo(f'  - {error.field}: {error.message}')
        else:
            click.echo('✓ Validation passed')

def _get_click_type(param_type: str):
    """获取 Click 参数类型"""
    if param_type == 'int':
        return int
    elif param_type == 'bool':
        return bool
    elif param_type == 'list':
        return str  # 以逗号分隔的字符串
    else:
        return str
```


### 非交互模式

**支持场景**：
- CI/CD 自动化
- 批量生成
- 脚本集成

**实现**：
```python
@click.command()
@click.argument('template_id')
@click.option('--param', '-p', multiple=True, help='Template parameter (key=value)')
@click.option('--output', '-o', type=click.Path(path_type=Path), required=True)
def skill_generate(template_id, param, output):
    """Generate SKILL.md from template (non-interactive)"""
    
    # 解析参数
    parameters = {}
    for p in param:
        if '=' not in p:
            click.echo(f'Invalid parameter format: {p}', err=True)
            return
        key, value = p.split('=', 1)
        parameters[key] = value
    
    # 渲染模板
    templates_dir = Path(__file__).parent / 'templates' / 'skills' / 'templates'
    renderer = TemplateRenderer(templates_dir)
    
    try:
        content = renderer.render(template_id, parameters)
        output.write_text(content)
        click.echo(f'✓ Generated {output}')
    except Exception as e:
        click.echo(f'Error: {e}', err=True)
        raise click.Abort()

# 使用示例：
# owlclaw skill generate monitoring/health-check \
#   -p skill_name=api-health \
#   -p skill_description="Monitor API health" \
#   -p check_interval=60 \
#   -o capabilities/api-health.md
```

## 监控和日志

### 日志记录

**日志级别**：
- DEBUG：详细的调试信息
- INFO：正常操作信息
- WARNING：警告信息
- ERROR：错误信息

**实现**：
```python
import logging

logger = logging.getLogger('owlclaw.templates.skills')

class TemplateRegistry:
    def _load_templates(self) -> None:
        logger.info(f"Loading templates from {self.templates_dir}")
        
        for category_dir in self.templates_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            logger.debug(f"Scanning category: {category_dir.name}")
            
            for template_file in category_dir.glob("*.md.j2"):
                try:
                    metadata = self._parse_template_metadata(template_file, category)
                    self._templates[metadata.id] = metadata
                    logger.debug(f"Loaded template: {metadata.id}")
                except Exception as e:
                    logger.error(
                        f"Failed to load template {template_file}: {e}",
                        exc_info=True,
                    )
        
        logger.info(f"Loaded {len(self._templates)} templates")
```

### 指标收集

**关键指标**：
- 模板加载时间
- 渲染时间
- 验证时间
- 错误率

**实现**：
```python
import time
from contextlib import contextmanager
from typing import Dict, List

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    @contextmanager
    def measure(self, operation: str):
        """测量操作耗时"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.metrics.setdefault(operation, []).append(duration)
            logger.debug(f"{operation} took {duration:.3f}s")
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """获取操作统计信息"""
        if operation not in self.metrics:
            return {}
        
        durations = self.metrics[operation]
        return {
            'count': len(durations),
            'total': sum(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations),
        }

# 使用示例
metrics = MetricsCollector()

class TemplateRenderer:
    def render(self, template_id: str, parameters: Dict[str, Any]) -> str:
        with metrics.measure(f'render:{template_id}'):
            # 渲染逻辑
            pass
```


## 文档和示例

### 用户文档

**文档结构**：
- 快速开始指南
- 模板参考
- API 文档
- 最佳实践
- 故障排除

**快速开始示例**：
```markdown
# SKILL.md 模板库快速开始

## 安装

```bash
pip install owlclaw
```

## 创建第一个 Skill

### 交互式创建

```bash
owlclaw skill init
```

按照提示选择模板并填写参数。

### 非交互式创建

```bash
owlclaw skill generate monitoring/health-check \
  -p skill_name=api-health \
  -p skill_description="Monitor API health" \
  -p check_interval=60 \
  -o capabilities/api-health.md
```

## 验证 Skill

```bash
owlclaw skill validate capabilities/api-health.md
```

## 可用模板

### Monitoring（监控）
- health-check: 健康检查监控
- metric-monitor: 指标监控
- alert-handler: 告警处理

### Analysis（分析）
- data-analyzer: 数据分析
- trend-detector: 趋势检测
- anomaly-detector: 异常检测

### Workflow（工作流）
- approval-flow: 审批流程
- task-scheduler: 任务调度
- event-handler: 事件处理

### Integration（集成）
- api-client: API 客户端
- webhook-handler: Webhook 处理
- data-sync: 数据同步

### Report（报告）
- daily-report: 日报生成
- summary-generator: 摘要生成
- notification-sender: 通知发送
```

### 开发者文档

**API 参考**：
```python
# 模板注册表
from owlclaw.templates.skills import TemplateRegistry

registry = TemplateRegistry(templates_dir)
templates = registry.list_templates(category='monitoring')
template = registry.get_template('monitoring/health-check')

# 模板渲染
from owlclaw.templates.skills import TemplateRenderer

renderer = TemplateRenderer(templates_dir)
content = renderer.render('monitoring/health-check', {
    'skill_name': 'api-health',
    'skill_description': 'Monitor API health',
    'check_interval': 60,
})

# 模板验证
from owlclaw.templates.skills import TemplateValidator

validator = TemplateValidator()
errors = validator.validate_skill_file(Path('capabilities/api-health.md'))

# 模板搜索
from owlclaw.templates.skills import TemplateSearcher

searcher = TemplateSearcher(registry)
results = searcher.search('health monitoring')
```

### 示例项目

**完整示例**：
```python
#!/usr/bin/env python3
"""
示例：使用模板库创建监控 Skill
"""

from pathlib import Path
from owlclaw.templates.skills import (
    TemplateRegistry,
    TemplateRenderer,
    TemplateValidator,
)

def main():
    # 1. 初始化组件
    templates_dir = Path('owlclaw/templates/skills/templates')
    registry = TemplateRegistry(templates_dir)
    renderer = TemplateRenderer(templates_dir)
    validator = TemplateValidator()
    
    # 2. 选择模板
    template = registry.get_template('monitoring/health-check')
    print(f"Using template: {template.name}")
    print(f"Description: {template.description}")
    
    # 3. 准备参数
    parameters = {
        'skill_name': 'api-health-monitor',
        'skill_description': 'Monitor API endpoints health',
        'check_interval': 60,
        'alert_threshold': 3,
        'endpoints': [
            'https://api.example.com/health',
            'https://api.example.com/db/health',
        ],
        'author': 'platform-team',
    }
    
    # 4. 渲染模板
    content = renderer.render(template.id, parameters)
    
    # 5. 保存文件
    output_dir = Path('capabilities')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{parameters['skill_name']}.md"
    output_file.write_text(content)
    print(f"Created: {output_file}")
    
    # 6. 验证文件
    errors = validator.validate_skill_file(output_file)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error.field}: {error.message}")
    else:
        print("✓ Validation passed")

if __name__ == '__main__':
    main()
```


## 迁移和向后兼容

### 版本迁移

**场景**：模板格式升级时的迁移

**策略**：
- 提供迁移工具
- 支持多版本共存
- 渐进式迁移

**实现**：
```python
class TemplateMigrator:
    """模板迁移器"""
    
    def migrate_template(
        self,
        template_path: Path,
        from_version: str,
        to_version: str,
    ) -> str:
        """迁移模板到新版本"""
        content = template_path.read_text()
        
        # 应用迁移规则
        for version in self._get_migration_path(from_version, to_version):
            migrator = self._get_migrator(version)
            content = migrator.migrate(content)
        
        return content
    
    def _get_migration_path(
        self,
        from_version: str,
        to_version: str,
    ) -> List[str]:
        """获取迁移路径"""
        # 返回需要应用的迁移版本列表
        pass
    
    def _get_migrator(self, version: str):
        """获取版本迁移器"""
        # 返回特定版本的迁移器
        pass

# 示例：1.0 -> 2.0 迁移器
class Migration_1_0_to_2_0:
    """从 1.0 迁移到 2.0"""
    
    def migrate(self, content: str) -> str:
        # 更新元数据格式
        content = self._update_metadata_format(content)
        
        # 更新参数定义
        content = self._update_parameter_format(content)
        
        return content
```

### 向后兼容

**策略**：
- 保持旧版本模板可用
- 自动检测模板版本
- 提供兼容层

**实现**：
```python
class TemplateRegistry:
    def _parse_template_metadata(
        self,
        template_file: Path,
        category: TemplateCategory,
    ) -> TemplateMetadata:
        content = template_file.read_text(encoding='utf-8')
        
        # 检测模板版本
        version = self._detect_template_version(content)
        
        # 使用对应版本的解析器
        parser = self._get_parser(version)
        metadata = parser.parse(content, template_file, category)
        
        return metadata
    
    def _detect_template_version(self, content: str) -> str:
        """检测模板版本"""
        # 从元数据中提取版本信息
        # 如果没有版本信息，默认为 1.0
        match = re.search(r'template_version:\s*"?([0-9.]+)"?', content)
        return match.group(1) if match else "1.0"
```

## 未来扩展

### 计划功能

1. **模板市场**
   - 社区贡献的模板
   - 模板评分和评论
   - 模板下载统计

2. **可视化编辑器**
   - Web 界面编辑模板
   - 实时预览
   - 拖拽式参数配置

3. **AI 辅助**
   - 根据描述自动推荐模板
   - 自动生成模板参数
   - 智能补全和建议

4. **模板组合**
   - 组合多个模板
   - 模板依赖管理
   - 批量生成

5. **国际化**
   - 多语言模板
   - 本地化参数
   - 区域特定模板

### 扩展点

**自定义类别**：
```python
class CustomTemplateCategory(Enum):
    """自定义模板类别"""
    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    WORKFLOW = "workflow"
    INTEGRATION = "integration"
    REPORT = "report"
    # 用户可以添加自定义类别
    CUSTOM_1 = "custom-1"
    CUSTOM_2 = "custom-2"
```

**自定义参数类型**：
```python
class TemplateParameterType(Enum):
    """模板参数类型"""
    STRING = "str"
    INTEGER = "int"
    BOOLEAN = "bool"
    LIST = "list"
    # 扩展类型
    DICT = "dict"
    ENUM = "enum"
    FILE_PATH = "file_path"
    URL = "url"
    EMAIL = "email"
```

## 总结

本设计文档描述了 SKILL.md 模板库的完整架构和实现方案。核心组件包括：

1. **TemplateRegistry**：管理模板注册和发现
2. **TemplateRenderer**：渲染模板生成 SKILL.md
3. **TemplateValidator**：验证模板和生成的文件
4. **TemplateSearcher**：智能搜索和推荐模板

设计遵循以下原则：
- 分类清晰，便于查找
- 结构完整，包含最佳实践
- 可扩展，支持自定义和插件
- 安全可靠，防护注入攻击
- 性能优化，支持大规模使用

通过 25 个正确性属性和全面的测试策略，确保系统的正确性和可靠性。与 OwlClaw CLI 的集成使得模板库易于使用，降低了业务接入成本。

---

**文档版本**：1.0  
**最后更新**：2026-02-22  
**维护者**：平台研发团队
              
{param.description})',
                type=str,
                default=param.default if param.default is not None else '',
            )
            
            # 类型转换
            if param.type == 'int':
                value = int(value)
            elif param.type == 'bool':
                value = value.lower() in ['true', 'yes', '1']
            elif param.type == 'list':
                value = [v.strip() for v in value.split(',')]
            
            parameters[param.name] = value
    
    # 5. 渲染模板
    try:
        content = renderer.render(selected_template.id, parameters)
    except Exception as e:
        click.echo(f'Error rendering template: {e}', err=True)
        return
    
    # 6. 保存文件
    skill_name = parameters.get('skill_name', 'new-skill')
    output_file = output_dir / f'{skill_name}.md'
    
    if output_file.exists():
        if not click.confirm(f'{output_file} already exists. Overwrite?'):
            return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content, encoding='utf-8')
    click.echo(f'\n✓ Created {output_file}')
    
    # 7. 验证文件
    if not no_validate:
        errors = validator.validate_skill_file(output_file)
        if errors:
            click.echo('\n⚠ Validation warnings:')
            for error in errors:
                click.echo(f'  - {error.field}: {error.message}')
        else:
            click.echo('✓ Validation passed')


@click.command()
@click.argument('skill_file', type=click.Path(exists=True, path_type=Path))
def skill_validate(skill_file):
    """Validate a SKILL.md file"""
    validator = TemplateValidator()
    errors = validator.validate_skill_file(skill_file)
    
    if not errors:
        click.echo(f'✓ {skill_file} is valid')
        return
    
    # 分类错误
    critical_errors = [e for e in errors if e.severity == "error"]
    warnings = [e for e in errors if e.severity == "warning"]
    
    if critical_errors:
        click.echo(f'✗ {skill_file} has {len(critical_errors)} error(s):')
        for error in critical_errors:
            click.echo(f'  - {error.field}: {error.message}')
    
    if warnings:
        click.echo(f'⚠ {skill_file} has {len(warnings)} warning(s):')
        for warning in warnings:
            click.echo(f'  - {warning.field}: {warning.message}')
    
    # 返回非零退出码如果有错误
    if critical_errors:
        raise click.ClickException('Validation failed')


@click.command()
@click.option(
    '--category',
    type=click.Choice(['monitoring', 'analysis', 'workflow', 'integration', 'report']),
    help='Filter templates by category',
)
@click.option(
    '--tags',
    help='Filter templates by tags (comma-separated)',
)
def skill_list(category, tags):
    """List available skill templates"""
    templates_dir = Path(__file__).parent / 'templates' / 'skills' / 'templates'
    registry = TemplateRegistry(templates_dir)
    
    # 过滤模板
    tag_list = [t.strip() for t in tags.split(',')] if tags else None
    templates = registry.list_templates(
        category=TemplateCategory(category) if category else None,
        tags=tag_list,
    )
    
    if not templates:
        click.echo('No templates found.')
        return
    
    # 按类别分组
    from collections import defaultdict
    by_category = defaultdict(list)
    for template in templates:
        by_category[template.category.value].append(template)
    
    # 展示模板
    for cat, tmpl_list in sorted(by_category.items()):
        click.echo(f'\n{cat.upper()}:')
        for template in tmpl_list:
            click.echo(f'  - {template.name}')
            click.echo(f'    {template.description}')
            click.echo(f'    Tags: {", ".join(template.tags)}')
            if template.examples:
                click.echo(f'    Examples: {template.examples[0]}')
```

### 非交互模式

**使用场景**：
- CI/CD 自动化
- 脚本批量生成
- 测试

**实现**：
```python
@click.command()
@click.option('--template-id', required=True, help='Template ID (e.g., monitoring/health-check)')
@click.option('--params', required=True, help='Parameters as JSON string')
@click.option('--output', required=True, type=click.Path(path_type=Path), help='Output file path')
@click.option('--no-validate', is_flag=True, help='Skip validation')
def skill_generate(template_id, params, output, no_validate):
    """Generate SKILL.md from template (non-interactive)"""
    import json
    
    # 解析参数
    try:
        parameters = json.loads(params)
    except json.JSONDecodeError as e:
        raise click.ClickException(f'Invalid JSON parameters: {e}')
    
    # 初始化组件
    templates_dir = Path(__file__).parent / 'templates' / 'skills' / 'templates'
    registry = TemplateRegistry(templates_dir)
    renderer = TemplateRenderer(templates_dir)
    validator = TemplateValidator()
    
    # 渲染模板
    try:
        content = renderer.render(template_id, parameters)
    except Exception as e:
        raise click.ClickException(f'Error rendering template: {e}')
    
    # 保存文件
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding='utf-8')
    click.echo(f'✓ Created {output}')
    
    # 验证
    if not no_validate:
        errors = validator.validate_skill_file(output)
        if errors:
            critical = [e for e in errors if e.severity == "error"]
            if critical:
                raise click.ClickException('Validation failed')

# 使用示例：
# owlclaw skill generate \
#   --template-id monitoring/health-check \
#   --params '{"skill_name":"api-health","skill_description":"Monitor API","check_interval":60}' \
#   --output capabilities/api-health.md
```

---

## 文档要求

### 用户文档

**模板使用指南**：
- 如何选择合适的模板
- 如何填写模板参数
- 常见问题和解决方案

**CLI 使用文档**：
- 命令参考
- 使用示例
- 最佳实践

**模板参考**：
- 每个模板的详细说明
- 参数说明
- 使用示例

### 开发者文档

**模板开发指南**：
- 如何创建新模板
- 模板文件格式
- 元数据规范
- 测试要求

**API 文档**：
- 组件接口说明
- 使用示例
- 扩展指南

**架构文档**：
- 系统架构
- 组件交互
- 设计决策

---

## 总结

本设计文档详细描述了 SKILL.md 模板库的完整设计，包括：

1. **核心组件**：TemplateRegistry、TemplateRenderer、TemplateValidator、TemplateSearcher
2. **数据模型**：模板元数据、参数定义、验证错误
3. **正确性属性**：25 个形式化属性定义
4. **错误处理**：8 种错误场景和处理策略
5. **测试策略**：单元测试、属性测试、集成测试
6. **性能优化**：加载、渲染、搜索优化
7. **安全考虑**：注入防护、路径验证、输出验证
8. **可扩展性**：自定义模板、模板继承、插件系统
9. **CLI 集成**：交互式和非交互式命令

该设计遵循以下原则：
- **简单性**：核心功能清晰，易于理解和实现
- **可靠性**：完善的错误处理和验证机制
- **可扩展性**：支持自定义和扩展
- **可测试性**：全面的测试策略和属性定义
- **安全性**：多层安全防护措施

---

**文档版本**：1.0  
**最后更新**：2026-02-22  
**维护者**：平台研发
