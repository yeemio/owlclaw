"""Performance checks for SKILL template library (skill-templates Task 19.3)."""

from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from owlclaw.templates.skills import (
    TemplateRegistry,
    TemplateRenderer,
    TemplateSearcher,
    TemplateValidator,
)


def _templates_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "owlclaw" / "templates" / "skills" / "templates"


def _sample_value_for_param(param: Any) -> Any:
    if param.choices:
        return param.choices[0]
    if param.default is not None:
        return param.default
    if param.type == "int":
        return 60
    if param.type == "bool":
        return True
    if param.type == "list":
        return ["item-a", "item-b"]
    return "demo-value"


def test_skill_template_performance_targets() -> None:
    templates_dir = _templates_dir()

    start_load = time.perf_counter()
    registry = TemplateRegistry(templates_dir)
    load_seconds = time.perf_counter() - start_load
    assert load_seconds < 1.0
    assert len(registry.list_templates()) >= 15

    template = registry.list_templates()[0]
    params: dict[str, Any] = {}
    for p in template.parameters:
        if p.required or p.default is not None:
            params[p.name] = _sample_value_for_param(p)

    renderer = TemplateRenderer(registry)
    start_render = time.perf_counter()
    rendered = ""
    for _ in range(20):
        rendered = renderer.render(template.id, params)
    avg_render_ms = (time.perf_counter() - start_render) * 1000 / 20
    assert avg_render_ms < 100
    assert rendered

    searcher = TemplateSearcher(registry)
    start_search = time.perf_counter()
    results = []
    for _ in range(20):
        results = searcher.search("health", limit=10)
    avg_search_ms = (time.perf_counter() - start_search) * 1000 / 20
    assert avg_search_ms < 200
    assert isinstance(results, list)

    validator = TemplateValidator()
    with TemporaryDirectory() as tmp_dir:
        skill_file = Path(tmp_dir) / "SKILL.md"
        skill_file.write_text(
            "---\nname: perf-skill\ndescription: performance check\n---\n# Title\n\nBody\n",
            encoding="utf-8",
        )
        start_validate = time.perf_counter()
        errors = []
        for _ in range(20):
            errors = validator.validate_skill_file(skill_file)
        avg_validate_ms = (time.perf_counter() - start_validate) * 1000 / 20
        assert avg_validate_ms < 500
        assert errors == []
