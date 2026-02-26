"""owlclaw skill create — conversational SKILL.md creation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from owlclaw.capabilities.skill_creator import SkillConversationState, SkillCreatorAgent
from owlclaw.capabilities.skills import SkillsLoader
from owlclaw.cli.skill_templates import load_template


def _collect_capability_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    loader = SkillsLoader(path)
    return [skill.name for skill in loader.scan()]


def create_command(
    interactive: Annotated[bool, typer.Option("--interactive", help="Start conversational creation flow.")] = False,
    from_template: Annotated[str, typer.Option("--from-template", help="Create skill from local template name.", is_flag=False)] = "",
    from_doc: Annotated[str, typer.Option("--from-doc", help="Generate from business document (Phase 2).", is_flag=False)] = "",
    output: Annotated[str, typer.Option("--output", help="Output directory for generated skill.", is_flag=False)] = "skills",
    capabilities_path: Annotated[
        str,
        typer.Option("--capabilities-path", help="Path used to discover existing capabilities.", is_flag=False),
    ] = "skills",
) -> None:
    """Create SKILL.md using interactive mode or templates."""
    if from_doc:
        typer.echo("Error: --from-doc is planned for Phase 2 and not available yet.", err=True)
        raise typer.Exit(2)

    out_dir = Path(output).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    if from_template:
        content = load_template(from_template.strip())
        name_line = next((line for line in content.splitlines() if line.startswith("name: ")), "name: generated-skill")
        skill_name = name_line.replace("name: ", "", 1).strip()
        target_dir = out_dir / skill_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "SKILL.md"
        target_file.write_text(content, encoding="utf-8")
        typer.echo(f"Generated from template: {target_file}")
        return

    if not interactive:
        typer.echo("Error: use --interactive or --from-template.", err=True)
        raise typer.Exit(2)

    capabilities = _collect_capability_names(Path(capabilities_path).expanduser())
    creator = SkillCreatorAgent(available_capabilities=capabilities)
    state = SkillConversationState()

    typer.echo("OwlClaw Skill Creator\n")
    if capabilities:
        typer.echo(f"Detected capabilities: {', '.join(capabilities)}\n")
    first = typer.prompt("请描述你想让 Agent 做什么")
    creator.update_state_from_user_input(state, first)

    rounds = 0
    while rounds < creator.MAX_ROUNDS and not creator.is_complete(state):
        q = creator.next_question(state)
        if not q:
            break
        answer = typer.prompt(q)
        creator.update_state_from_user_input(state, answer)
        rounds += 1

    if not creator.is_complete(state):
        typer.echo("Error: 信息不足，无法生成 SKILL.md。请补充触发条件和核心目标。", err=True)
        raise typer.Exit(2)

    rendered = creator.generate_skill_markdown(state)
    preview = typer.confirm("已生成 SKILL.md，是否预览？", default=True)
    if preview:
        typer.echo("\n" + rendered)
    save = typer.confirm("是否保存到文件？", default=True)
    if not save:
        typer.echo("Cancelled.")
        raise typer.Exit(1)

    skill_name = next(
        (line.replace("name: ", "", 1).strip() for line in rendered.splitlines() if line.startswith("name: ")),
        "generated-skill",
    )
    target_dir = out_dir / skill_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "SKILL.md"
    target_file.write_text(rendered, encoding="utf-8")
    typer.echo(f"Saved: {target_file}")
