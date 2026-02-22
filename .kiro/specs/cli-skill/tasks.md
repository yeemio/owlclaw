# 任务文档：Skills CLI（owlclaw skill）

## 文档联动

- requirements: `.kiro/specs/cli-skill/requirements.md`
- design: `.kiro/specs/cli-skill/design.md`
- tasks: `.kiro/specs/cli-skill/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


## 概述

实现 `owlclaw skill` 子命令组 MVP：init、validate、list。任务按依赖顺序排列，验收以可执行命令与测试为准。

---

## 任务列表

- [x] **Task 0**：CLI 基础设施（若尚未存在）
  - 若 `owlclaw/cli` 尚未使用 Typer：在 pyproject.toml 中添加 typer、rich 依赖；在 `owlclaw/cli/__init__.py` 中创建 Typer 应用并实现 `main()` 调用 `app()`。
  - 确保 `owlclaw --help` 可运行；若已有 `owlclaw db`，保留并继续挂载 `skill`。
  - 验收：`poetry run owlclaw --help` 输出包含 usage 与子命令说明。

- [x] **Task 1**：注册 skill 子命令组
  - 在 `owlclaw/cli/skill.py` 中创建 `skill_app = typer.Typer(...)`。
  - 在 `owlclaw/cli/__init__.py` 中挂载：`app.add_typer(skill_app, name="skill")`。
  - 验收：`owlclaw skill --help` 显示 init、validate、list 子命令。

- [x] **Task 2**：实现 skill init
  - 在 `owlclaw/cli/skill_init.py` 中实现 `init_command(name, path, template, force)`。
  - 在 `path`（默认 cwd）下创建目录 `name`，写入 `name/SKILL.md`，内容为默认 frontmatter（name、description 占位）+ 占位正文。
  - 处理目标已存在：无 `--force` 时提示并退出；有 `--force` 时覆盖。
  - 在 `skill.py` 中注册 `@skill_app.command("init")` 并转发参数。
  - 验收：`owlclaw skill init my-skill` 在当前目录生成 `my-skill/SKILL.md`；`owlclaw skill validate my-skill` 通过。

- [x] **Task 3**：实现 skill validate
  - 在 `owlclaw/cli/skill_validate.py` 中实现 `validate_command(paths, verbose)`。
  - 对每个 path：若为目录则递归查找 SKILL.md；若为文件则直接校验。复用 `SkillsLoader._parse_skill_file` 或等价的 frontmatter 解析与必填字段检查。
  - 全部通过时退出码 0；任一失败时打印错误并退出码 1。
  - 在 `skill.py` 中注册 `@skill_app.command("validate")`。
  - 验收：对 init 生成的目录执行 `owlclaw skill validate my-skill` 退出码 0；对缺少 description 的 SKILL.md 退出码非零并输出错误。

- [x] **Task 4**：实现 skill list
  - 在 `owlclaw/cli/skill_list.py` 中实现 `list_command(path)`。
  - 使用 `SkillsLoader(path).scan()` 或同等逻辑，输出 name、description（可截断）、可选 path。
  - 在 `skill.py` 中注册 `@skill_app.command("list")`。
  - 验收：在含 `my-skill` 的目录执行 `owlclaw skill list` 输出包含 my-skill 及其 description；无 skill 时输出友好提示。

- [x] **Task 5**：单元测试
  - 为 init：测试目录与文件生成、--force、已存在时行为。
  - 为 validate：测试合法/非法 frontmatter、缺少字段、多路径。
  - 为 list：测试有/无 Skills 时的输出与退出码。
  - 验收：`poetry run pytest tests/unit/test_cli_skill.py -v` 通过。

- [x] **Task 6**：收口与文档
  - 更新 SPEC_TASKS_SCAN：功能清单中 `owlclaw.cli.skill`（init/validate/list）勾选；Spec 索引中 cli-skill 状态更新为文档齐全且 MVP 已实现。
  - 更新 Checkpoint：当前批次为 cli-skill MVP，下一待执行为 skill-templates 或 governance。
  - 验收：SPEC_TASKS_SCAN 与 Checkpoint 已更新，且所有上述验收通过。
