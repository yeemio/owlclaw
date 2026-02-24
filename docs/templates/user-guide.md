# SKILL.md 模板库 — 用户指南

## 快速开始（< 5 分钟）

### 1. 列出可用模板

```bash
owlclaw skill templates
```

### 2. 从模板创建 Skill

```bash
# 使用默认模板（简单 scaffold）
owlclaw skill init --name my-skill

# 使用监控模板（非交互式）
owlclaw skill init --template monitoring/health-check \
  --param "skill_name=API Monitor,skill_description=Monitor APIs,endpoints=/health,/ready" \
  --output capabilities
```

### 3. 验证生成的文件

```bash
owlclaw skill validate capabilities/
```

## CLI 命令说明

| 命令 | 说明 |
|------|------|
| `owlclaw skill init` | 从模板创建 SKILL.md |
| `owlclaw skill validate` | 验证 SKILL.md 文件 |
| `owlclaw skill list` | 列出目录中的 Skills |
| `owlclaw skill templates` | 列出模板库中的模板 |

### init 选项

- `--name`, `-n`: Skill 名称（默认模板必需）
- `--template`, `-t`: 模板 ID（如 `monitoring/health-check`）
- `--output`, `-o`: 输出目录
- `--params-file`: 参数文件（JSON/YAML）
- `--param`: 参数（`key=value`，逗号分隔）
- `--force`, `-f`: 覆盖已存在的文件

### templates 选项

- `--category`, `-c`: 按类别过滤
- `--tags`: 按标签过滤（逗号分隔）
- `--search`, `-s`: 关键词搜索
- `--show`: 显示模板详情
- `--verbose`, `-v`: 显示详细信息
- `--json`: JSON 输出

## 最佳实践

- 先执行 `owlclaw skill templates --show <template_id>` 确认必需参数
- `skill_name` 保持 kebab-case，避免后续校验失败
- 将复杂参数放到 `--params-file`（JSON/YAML）便于复用
- 生成后立即执行 `owlclaw skill validate <path>`，在提交前使用 `--strict`

## 故障排查

- **模板未找到**：确认 template ID 格式为 `category/name`（如 `monitoring/health-check`）
- **缺少必需参数**：使用 `owlclaw skill templates --show monitoring/health-check` 查看参数
- **验证失败**：检查 name 是否为 kebab-case，frontmatter 格式是否正确
