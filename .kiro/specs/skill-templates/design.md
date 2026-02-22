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

