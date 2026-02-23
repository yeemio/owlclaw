# 设计文档：Skills CLI（owlclaw skill）

## 文档联动

- requirements: `.kiro/specs/cli-skill/requirements.md`
- design: `.kiro/specs/cli-skill/design.md`
- tasks: `.kiro/specs/cli-skill/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

Skills CLI 提供 `owlclaw skill` 子命令组，用于在本地创建、校验和列举 Agent Skills（SKILL.md）。MVP 包含三个子命令：**init**、**validate**、**list**，均不依赖 OwlHub 或网络。

设计原则：

1. **复用 SkillsLoader 解析逻辑**：validate 与 list 使用与 `owlclaw.capabilities.skills` 相同的 frontmatter 解析与必填字段规则，避免重复与不一致。
2. **与现有 CLI 一致**：若项目已采用 Typer（如 cli-db），则 skill 子命令挂载到同一 Typer 应用下；入口为 `owlclaw.cli:main`。
3. **纯本地**：不读取远程配置、不调用网络 API。

---

## 架构例外声明（实现阶段需固化）

本 spec 当前未引入业务层面的数据库铁律例外。实现阶段遵循以下约束：

1. 技能管理 CLI 作为本地工具链，不绕过 Skills 规范校验与治理策略。
2. 远程安装/发布流程必须保留完整可追溯元数据（来源、版本、校验和）。
3. `alembic_version` 属于 Alembic 系统表，不适用业务表约束。

## 架构

### 模块结构

```
owlclaw/
└── cli/
    ├── __init__.py          # 主入口，注册 app + db + skill
    ├── skill.py             # skill 子命令组
    ├── skill_init.py        # init 命令
    ├── skill_validate.py    # validate 命令
    └── skill_list.py        # list 命令
```

- 若尚未引入 Typer，则在本 spec 实现中引入 Typer 与 Rich（与 cli-db 对齐），并在 `owlclaw/cli/__init__.py` 中创建根 App、挂载 `db` 与 `skill` 子命令组。
- `skill` 子命令组：`typer.Typer()` 实例，在 `__init__.py` 中通过 `app.add_typer(skill_app, name="skill")` 注册。

### 命令接口

| 命令 | 签名 | 说明 |
|------|------|------|
| init | `owlclaw skill init <name> [--path PATH] [--template TEMPLATE] [--force]` | 创建 name 目录及 SKILL.md |
| validate | `owlclaw skill validate <path>... [--verbose]` | 校验 SKILL.md 合规性 |
| list | `owlclaw skill list [--path PATH]` | 扫描并列出 Skills |

### 与 SkillsLoader 的复用

- **list**：在给定根目录下 `Path(path).rglob("SKILL.md")`，对每个文件调用与 `SkillsLoader._parse_skill_file` 相同的解析逻辑（或直接实例化 `SkillsLoader(path)` 后 `scan()`），收集 `Skill` 的 name、description、file_path 并输出。
- **validate**：对每个 path（若为目录则递归其下 SKILL.md）执行相同解析；若解析失败或缺少 name/description，则视为校验失败，输出错误并设非零退出码。不在内存中保留完整 Skill 列表，仅做校验。

可选：将 frontmatter 解析与必填校验抽成 `owlclaw.capabilities.skills` 中的可复用函数（如 `parse_skill_frontmatter(path) -> Skill | None` 或 `validate_skill_file(path) -> list[str]` 错误列表），供 CLI 与 SkillsLoader 共用。

---

## init 命令详细设计

- **行为**：在 `path`（默认 `Path.cwd()`）下创建目录 `name`，并在其下写入 `SKILL.md`。
- **内容**：
  - Frontmatter：`name`、`description`（占位如 `Description for <name>`）、可选 `metadata: {}`、可选 `owlclaw: {}`。
  - Body：简短占位说明（如 `# Instructions\n\nDescribe when and how to use this skill.`）。
- **模板**：`--template` 在 MVP 中支持 `default` 或省略（等价）。后续 skill-templates spec 可扩展为 monitoring/analysis 等，由模板库提供内容。
- **覆盖**：若 `path/name/SKILL.md` 已存在且未传 `--force`，提示用户并退出；传 `--force` 则覆盖。

---

## validate 命令详细设计

- **输入**：一个或多个 path（文件或目录）。目录则递归查找所有 SKILL.md。
- **校验项**：
  1. 文件存在且可读。
  2. 内容以 `---` 开头（frontmatter 存在）。
  3. Frontmatter 为合法 YAML。
  4. 必填字段：`name`、`description` 存在且非空。
- **输出**：成功时打印每个 path 的 OK 信息；失败时打印 path + 具体错误（如 "missing field: description"），并设退出码为 1（或 2 区分用法错误）。`--verbose` 可输出错误所在行/字段。

---

## list 命令详细设计

- **输入**：`--path` 默认当前工作目录；递归扫描该目录下所有 SKILL.md。
- **解析**：使用与 SkillsLoader 相同的逻辑解析每个 SKILL.md，跳过解析失败的文件（可选：在 verbose 模式下报告跳过原因）。
- **输出**：表格或列表，列至少包含 name、description（可截断至固定长度）；可选列 file_path。无 Skill 时打印 "No skills found."，退出码 0。

---

## 依赖

- **Typer**：CLI 框架（与 cli-db 一致）。
- **Rich**：表格/列表输出（可选，可与 cli-db 共用）。
- **owlclaw.capabilities.skills**：Skill、SkillsLoader 或抽出的解析/校验函数；仅导入解析与校验逻辑，不依赖 CapabilityRegistry 或 App。

---

## 错误处理与退出码

- `0`：成功。
- `1`：校验失败（validate 发现错误）。
- `2`：用法错误（如缺少必填参数、path 不存在）。


---

## 实现细节

### 文件结构

```
owlclaw/
├── cli/
│   ├── __init__.py          # CLI 主入口
│   ├── skill.py             # skill 子命令组
│   ├── skill_init.py        # init 命令实现
│   ├── skill_validate.py    # validate 命令实现
│   ├── skill_list.py        # list 命令实现
│   └── templates/
│       └── skill_default.md # 默认 SKILL.md 模板
└── capabilities/
    └── skills/
        ├── __init__.py
        ├── loader.py        # SkillsLoader
        └── validator.py     # 共享的校验逻辑
```

### CLI 主入口（__init__.py）

```python
import typer
from owlclaw.cli import skill

app = typer.Typer(
    name="owlclaw",
    help="OwlClaw CLI - Agent framework for production",
    add_completion=False
)

# 注册子命令组
app.add_typer(skill.app, name="skill")

def main():
    app()

if __name__ == "__main__":
    main()
```

### skill 子命令组（skill.py）

```python
import typer
from pathlib import Path
from owlclaw.cli import skill_init, skill_validate, skill_list

app = typer.Typer(
    name="skill",
    help="Manage Agent Skills (SKILL.md files)",
    add_completion=False
)

@app.command("init")
def init(
    name: str = typer.Argument(..., help="Skill name (kebab-case)"),
    path: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Parent directory for the skill"
    ),
    template: str = typer.Option(
        "default",
        "--template",
        "-t",
        help="Template to use (default, monitoring, analysis)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing SKILL.md"
    )
):
    """Create a new Skill with SKILL.md"""
    skill_init.create_skill(name, path, template, force)

@app.command("validate")
def validate(
    paths: list[Path] = typer.Argument(..., help="Paths to SKILL.md files or directories"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed errors")
):
    """Validate SKILL.md files"""
    skill_validate.validate_skills(paths, verbose)

@app.command("list")
def list_skills(
    path: Path = typer.Option(
        Path.cwd(),
        "--path",
        "-p",
        help="Directory to scan for skills"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    )
):
    """List all Skills in a directory"""
    skill_list.list_skills(path, json_output)
```

### init 命令实现（skill_init.py）

```python
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console

console = Console()

SKILL_TEMPLATE = """---
name: {name}
description: {description}
metadata:
  version: "1.0.0"
  author: ""
  tags: []
owlclaw:
  task_type: ""
  constraints: {{}}
---

# {title}

## When to Use

Describe when this skill should be used.

## How to Use

Provide step-by-step instructions for using this skill.

## Examples

```
Example usage here
```

## Notes

Additional notes or warnings.
"""

def create_skill(
    name: str,
    path: Path,
    template: str,
    force: bool
):
    """Create a new Skill directory with SKILL.md"""
    
    # Validate name format (kebab-case)
    if not is_valid_skill_name(name):
        console.print(
            f"[red]Error:[/red] Skill name must be kebab-case (e.g., 'my-skill')",
            style="bold"
        )
        raise typer.Exit(2)
    
    # Create skill directory
    skill_dir = path / name
    skill_file = skill_dir / "SKILL.md"
    
    # Check if exists
    if skill_file.exists() and not force:
        console.print(
            f"[yellow]Warning:[/yellow] {skill_file} already exists. Use --force to overwrite.",
            style="bold"
  
```
