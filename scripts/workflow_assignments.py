"""Parse and validate manual worktree assignments from WORKTREE_ASSIGNMENTS.md."""

from __future__ import annotations

import re
from pathlib import Path


ASSIGNMENTS_PATH = Path(".kiro") / "WORKTREE_ASSIGNMENTS.md"

ROLE_HEADING_RE = re.compile(r"^###\s+(owlclaw(?:-codex(?:-gpt)?|-review)?)\b.*$", re.MULTILINE)


def _parse_field_table(section: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [part.strip() for part in stripped.strip("|").split("|")]
        if len(parts) != 2:
            continue
        key, value = parts
        if key in {"字段", "------"}:
            continue
        fields[key] = value
    return fields


def _parse_table_after_heading(section: str, heading: str) -> list[dict[str, str]]:
    lines = section.splitlines()
    start_index = -1
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start_index = index + 1
            break
    if start_index < 0:
        return []

    table_lines: list[str] = []
    for line in lines[start_index:]:
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if not stripped.startswith("|"):
            if table_lines:
                break
            continue
        table_lines.append(stripped)

    if len(table_lines) < 2:
        return []

    headers = [part.strip() for part in table_lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != len(headers):
            continue
        rows.append(dict(zip(headers, parts)))
    return rows


def _clean_markdown_cell(value: str) -> str:
    cleaned = value.strip()
    cleaned = cleaned.strip("`")
    cleaned = cleaned.replace("**", "")
    return cleaned


def _role_sections(text: str) -> dict[str, str]:
    matches = list(ROLE_HEADING_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        role_name = match.group(1)
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[role_name] = text[start:end]
    return sections


def _coding_worktree_sections(text: str) -> dict[str, str]:
    sections = _role_sections(text)
    return {
        "codex": sections.get("owlclaw-codex", ""),
        "codex-gpt": sections.get("owlclaw-codex-gpt", ""),
    }


def load_assignment_matrix(repo_root: Path) -> dict[str, dict[str, object]]:
    path = repo_root / ASSIGNMENTS_PATH
    text = path.read_text(encoding="utf-8")
    sections = _coding_worktree_sections(text)
    matrix: dict[str, dict[str, object]] = {}
    for agent, section in sections.items():
        fields = _parse_field_table(section)
        current_specs = [
            _clean_markdown_cell(row.get("Spec", ""))
            for row in _parse_table_after_heading(section, "**当前分配的 spec**：")
            if row.get("Spec")
        ]
        queued_specs = [
            _clean_markdown_cell(row.get("Spec", ""))
            for row in _parse_table_after_heading(section, f"### {fields.get('分支', '')} 分配（当前批次）")
            if row.get("Spec")
        ]
        all_specs = {spec for spec in [*current_specs, *queued_specs] if spec}
        matrix[agent] = {
            "agent": agent,
            "branch": _clean_markdown_cell(fields.get("分支", "")),
            "status": _clean_markdown_cell(fields.get("工作状态", "")),
            "specs": sorted(all_specs),
            "path": _clean_markdown_cell(fields.get("目录", "")),
        }
    return matrix


def validate_assignment_target(
    repo_root: Path,
    *,
    target_agent: str,
    target_branch: str,
    spec_name: str,
) -> tuple[bool, str]:
    matrix = load_assignment_matrix(repo_root)
    record = matrix.get(target_agent)
    if not record:
        return False, f"target agent '{target_agent}' is not a coding worktree in WORKTREE_ASSIGNMENTS.md"
    if record["branch"] != target_branch:
        return False, f"target branch '{target_branch}' does not match assigned branch '{record['branch']}' for {target_agent}"
    if spec_name and spec_name not in set(record["specs"]):
        return False, f"spec '{spec_name}' is not assigned to {target_agent}/{target_branch} in WORKTREE_ASSIGNMENTS.md"
    return True, ""
