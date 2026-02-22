# SKILL.md 模板开发指南

## 模板文件格式

### 1. 元数据注释块

每个模板文件必须以 Jinja2 注释块 `{# ... #}` 开头，包含 YAML 格式的元数据：

```yaml
{#
name: Health Check Monitor
description: 监控服务健康状态
tags:
  - monitoring
  - health
  - api
parameters:
  - name: skill_name
    type: str
    required: true
    description: Skill 名称（kebab-case）
  - name: skill_description
    type: str
    required: true
    description: Skill 描述
  - name: endpoints
    type: list
    required: false
    default: []
    description: 监控端点列表
examples:
  - owlclaw skill init --template monitoring/health-check --param "skill_name=api-mon"
#}
```

### 2. 元数据字段规范

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | str | ✓ | 模板显示名称 |
| description | str | ✓ | 模板描述 |
| tags | list[str] | ✓ | 标签列表 |
| parameters | list | ✓ | 参数定义 |
| examples | list[str] | 否 | 使用示例 |

### 3. 参数定义

```yaml
parameters:
  - name: param_name
    type: str | int | bool | list
    required: true | false
    default: <值>   # 可选
    description: 参数说明
    choices: [...]  # 可选，限定取值
```

### 4. Jinja2 语法使用

- 变量：`{{ skill_name }}`
- 条件：`{% if endpoints %}` ... `{% endif %}`
- 循环：`{% for ep in endpoints %}` ... `{% endfor %}`
- 过滤器：`{{ name | kebab_case }}`、`{{ name | snake_case }}`

## 模板目录结构

```
owlclaw/templates/skills/templates/
├── monitoring/     # 类别目录名 = TemplateCategory 枚举值
│   ├── health-check.md.j2
│   ├── metric-monitor.md.j2
│   └── alert-handler.md.j2
├── analysis/
├── workflow/
├── integration/
└── report/
```

## 新增模板步骤

1. 在对应类别目录下创建 `*.md.j2` 文件
2. 编写元数据注释块（必须包含 name、description、tags、parameters）
3. 编写 frontmatter 和 Markdown body
4. 运行 `owlclaw skill validate <输出路径>` 验证
5. 使用 `scripts/test_template.py` 测试（如已实现）

## 审查清单

- [ ] 元数据块格式正确（YAML 可解析）
- [ ] 所有必需参数有 description
- [ ] `skill_name` 使用 `kebab_case`  filter
- [ ] frontmatter 包含 name、description
- [ ] 至少有一个 `##` 标题
- [ ] 模板可成功渲染（无未定义变量）
