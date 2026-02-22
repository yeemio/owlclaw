# 需求文档：Skills CLI（owlclaw skill）

## 文档联动

- requirements: `.kiro/specs/cli-skill/requirements.md`
- design: `.kiro/specs/cli-skill/design.md`
- tasks: `.kiro/specs/cli-skill/tasks.md`
- status source: `.kiro/specs/SPEC_TASKS_SCAN.md`


> **目标**：为 OwlClaw 提供 Skills 的本地创建、校验与列举命令行入口，纯本地操作，不依赖 OwlHub。
> **优先级**：P0（MVP）
> **预估工作量**：1–2 天

---

## 1. 背景与动机

### 1.1 当前问题

- 业务开发者需要手写 SKILL.md 时缺乏统一入口与校验手段。
- 无法快速从零生成一个符合 Agent Skills 规范的 SKILL.md 骨架。
- 项目中已有哪些 Skills 需要靠人工查看目录，缺少 `owlclaw skill list` 这类一览能力。

### 1.2 设计目标

- 提供 `owlclaw skill` 子命令组，MVP 包含 **init**、**validate**、**list**，均为纯本地操作。
- init：从模板或默认骨架生成新 Skill 目录与 SKILL.md。
- validate：校验指定路径下 SKILL.md 的格式与必填字段。
- list：扫描指定目录并列出已发现的 Skills（名称、描述等）。

---

## 2. 用户故事

### 2.1 作为业务开发者

**故事 1：快速创建新 Skill**
```
作为业务开发者
我希望执行 owlclaw skill init my-skill 生成一个符合规范的 Skill 目录和 SKILL.md
这样我可以在此基础上只填业务规则，而不必记格式
```

**验收标准**：
- [ ] 执行 `owlclaw skill init <name>` 在当前目录下创建 `<name>/SKILL.md`
- [ ] 生成的 SKILL.md 包含合法 YAML frontmatter（name、description）及占位正文
- [ ] 若提供 `--path`，在指定路径下创建；否则默认当前工作目录
- [ ] 若目标目录已存在且含 SKILL.md，提示是否覆盖或跳过

**故事 2：校验 Skill 格式**
```
作为业务开发者
我希望执行 owlclaw skill validate <path> 检查 SKILL.md 是否合规
这样我可以在提交前发现缺少 name/description 或 YAML 错误
```

**验收标准**：
- [ ] 执行 `owlclaw skill validate <path>` 时，path 可为 SKILL.md 文件或包含 SKILL.md 的目录
- [ ] 校验 frontmatter 存在、YAML 可解析、必填字段 name/description 存在
- [ ] 校验通过时退出码 0 并输出成功信息；不通过时非零退出码并输出具体错误
- [ ] 支持一次校验多个路径（多个参数或目录递归）

**故事 3：列出项目中的 Skills**
```
作为业务开发者
我希望执行 owlclaw skill list 列出当前项目中已发现的 Skills
这样我可以快速看到有哪些能力以及简短描述
```

**验收标准**：
- [ ] 执行 `owlclaw skill list` 扫描默认目录（如当前目录或配置的 skills 路径）下的 SKILL.md
- [ ] 输出每个 Skill 的 name、description（可截断），可选 file_path
- [ ] 支持 `--path` 指定扫描根目录
- [ ] 无 Skills 时输出友好提示，退出码 0

---

## 3. 功能需求

### 3.1 命令行为

#### FR-1：init 命令

- **需求**：创建新 Skill 目录及 SKILL.md；可选使用模板（MVP 可为单一默认骨架）。
- **参数**：`<name>`（必填）、`--path`（可选，默认 cwd）、`--template`（可选，MVP 可仅支持 default/basic）、`--force`（可选，覆盖已存在文件）。
- **验收**：见故事 1。

#### FR-2：validate 命令

- **需求**：校验指定路径下 SKILL.md 的 Agent Skills 规范合规性（frontmatter、name、description）。
- **参数**：`<path>...`（一个或多个文件或目录）、`--verbose`（可选，输出详细错误位置）。
- **验收**：见故事 2。

#### FR-3：list 命令

- **需求**：递归扫描目录中的 SKILL.md，列出 name、description 等元数据。
- **参数**：`--path`（可选，默认 cwd）。
- **验收**：见故事 3。

### 3.2 与现有组件关系

- **SkillsLoader**（`owlclaw.capabilities.skills`）：list 与 validate 应复用或共用其解析逻辑（frontmatter 解析、必填字段校验），避免重复实现。
- **SKILL.md 格式**：遵循 Agent Skills 规范及 OwlClaw 扩展（owlclaw.task_type、owlclaw.constraints 等）；validate 至少校验规范必填部分。

---

## 4. 非功能需求

- **纯本地**：MVP 不依赖网络或 OwlHub；search/install/publish 为后续 spec。
- **退出码**：成功 0，校验失败或参数错误为非零。
- **输出**：错误信息清晰、可操作；列表输出机器可读可选（如 `--json`），MVP 可为纯文本表格或列表。

---

## 5. 范围边界（MVP 不包含）

- `owlclaw skill search`、`install`、`publish`、`info`：依赖 OwlHub，列入后续 spec。
- 模板库（monitoring/analysis/workflow 等）：由 skill-templates spec 覆盖；本 spec 仅保证 init 可接受 `--template` 并在 MVP 中提供至少一个内置默认模板。
