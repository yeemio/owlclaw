# owlclaw skill 命令参考

> 注：OwlHub 发布闸门命令命名正在架构审校中，见 `docs/OWLHUB_CLI_NAMING_DECISION_PROPOSAL.md`。

## 命令概览

| 命令 | 说明 |
|------|------|
| `owlclaw skill init` | 从模板创建 SKILL.md |
| `owlclaw skill validate` | 验证 SKILL.md 文件 |
| `owlclaw skill list` | 列出目录中的 Skills |
| `owlclaw skill templates` | 列出模板库中的模板 |
| `owlclaw skill search` | 从 OwlHub 索引搜索技能 |
| `owlclaw skill install` | 从 OwlHub 索引安装技能 |
| `owlclaw skill installed` | 从 lock 文件列出已安装技能 |

---

## owlclaw skill init

从模板创建 SKILL.md 文件。

### 用法

```bash
# 交互式（使用默认模板）
owlclaw skill init --name my-skill

# 非交互式（指定模板和参数）
owlclaw skill init --template monitoring/health-check \
  --param "skill_name=api-mon,skill_description=Monitor API health" \
  --output capabilities
```

### 选项

| 选项 | 短选项 | 说明 |
|------|--------|------|
| `--name` | `-n` | Skill 名称（默认模板必需） |
| `--template` | `-t` | 模板 ID，如 `monitoring/health-check` |
| `--output` | `-o` | 输出目录，默认 `capabilities` |
| `--params-file` | | 参数文件路径（JSON 或 YAML） |
| `--param` | | 参数，`key=value` 或 `key=val1,val2`（逗号分隔多值） |
| `--force` | `-f` | 覆盖已存在的文件 |

### 示例

```bash
# 使用 monitoring/health-check 模板
owlclaw skill init -t monitoring/health-check \
  -n api-monitor \
  --param "skill_description=Monitor APIs,endpoints=/health,/ready"

# 从 YAML 文件加载参数
owlclaw skill init -t analysis/data-analyzer --params-file params.yaml -o skills/
```

---

## owlclaw skill validate

验证 SKILL.md 文件格式和内容。

### 用法

```bash
owlclaw skill validate <path>
```

### 参数

- `path`: 文件路径或目录；为目录时递归验证其中的 SKILL.md

### 选项

| 选项 | 说明 |
|------|------|
| `--strict` | 将警告视为失败 |

### 示例

```bash
owlclaw skill validate capabilities/
owlclaw skill validate capabilities/my-skill/SKILL.md --strict
```

---

## owlclaw skill list

列出指定目录下的 Skills。

### 用法

```bash
owlclaw skill list [path]
```

### 参数

- `path`: 目录路径，默认 `capabilities` 或 `skills`

---

## owlclaw skill templates

列出模板库中的模板。

### 用法

```bash
owlclaw skill templates [options]
```

### 选项

| 选项 | 短选项 | 说明 |
|------|--------|------|
| `--category` | `-c` | 按类别过滤 |
| `--tags` | | 按标签过滤（逗号分隔） |
| `--search` | `-s` | 关键词搜索 |
| `--show` | | 显示指定模板详情，如 `--show monitoring/health-check` |
| `--verbose` | `-v` | 显示详细信息 |
| `--json` | | JSON 输出 |

### 示例

```bash
# 列出所有模板
owlclaw skill templates

# 按类别过滤
owlclaw skill templates -c monitoring

# 搜索关键词
owlclaw skill templates -s health

# 查看模板详情
owlclaw skill templates --show monitoring/health-check
```

---

## 常见问题

**Q: 模板 ID 格式是什么？**  
A: `category/name`，如 `monitoring/health-check`。可用 `owlclaw skill templates` 查看完整列表。

**Q: --param 如何传列表？**  
A: 用逗号分隔，如 `--param "endpoints=/a,/b,/c"`。

**Q: 验证失败常见原因？**  
A: `name` 需为 kebab-case；frontmatter 需为有效 YAML；body 需包含至少一个 `##` 标题。

---

## owlclaw skill search

从 `index.json` 搜索技能（支持关键词和 tag 过滤）。

### 用法

```bash
owlclaw skill search [--query <text>] [--tags <tag1,tag2>] [--index-url <path-or-url>]
```

### 示例

```bash
owlclaw skill search --query monitor
owlclaw skill search --query entry --tags trading,signal --index-url ./index.json
```

---

## owlclaw skill install

按名称安装技能，可指定版本。安装后自动写入 `skill-lock.json`。

### 用法

```bash
owlclaw skill install <name> [--version <semver>] [--index-url <path-or-url>]
```

### 示例

```bash
owlclaw skill install entry-monitor
owlclaw skill install entry-monitor --version 1.0.0 --index-url ./index.json
```

---

## owlclaw skill installed

读取 lock 文件，输出已安装技能列表。

### 用法

```bash
owlclaw skill installed [--lock-file <path>]
```
