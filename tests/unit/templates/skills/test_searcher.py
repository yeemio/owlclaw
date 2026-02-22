"""Unit tests for owlclaw.templates.skills.searcher (skill-templates Task 6)."""

from pathlib import Path

from owlclaw.templates.skills import TemplateCategory, TemplateRegistry, TemplateSearcher


def _make_registry(tmp_path: Path, templates: list[tuple[str, str, str, list[str]]]) -> TemplateRegistry:
    """Create registry with templates. Each: (category, name, description, tags)."""
    for category, name, desc, tags in templates:
        d = tmp_path / category
        d.mkdir(exist_ok=True)
        fid = name.lower().replace(" ", "-")
        content = f"""{{#
name: {name}
description: {desc}
tags: {tags}
parameters: []
#}}
---
name: {fid}
---
# {name}
"""
        (d / f"{fid}.md.j2").write_text(content, encoding="utf-8")
    return TemplateRegistry(tmp_path)


class TestTemplateSearcher:
    def test_search_by_name(self, tmp_path: Path) -> None:
        reg = _make_registry(
            tmp_path,
            [
                ("monitoring", "Health Check", "Monitor health", ["health"]),
                ("monitoring", "Metric Monitor", "Monitor metrics", ["metrics"]),
            ],
        )
        searcher = TemplateSearcher(reg)
        results = searcher.search("health", limit=5)
        assert len(results) >= 1
        assert results[0].score >= 0.8
        assert "health" in results[0].match_reason.lower()

    def test_search_results_sorted_by_score(self, tmp_path: Path) -> None:
        reg = _make_registry(
            tmp_path,
            [
                ("monitoring", "Health Monitor", "Monitor health and alerts", ["health", "alert"]),
            ],
        )
        searcher = TemplateSearcher(reg)
        results = searcher.search("health", limit=5)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_search_with_category_filter(self, tmp_path: Path) -> None:
        reg = _make_registry(
            tmp_path,
            [
                ("monitoring", "Health Check", "Monitor", ["health"]),
                ("analysis", "Data Analyzer", "Analyze data", ["data"]),
            ],
        )
        searcher = TemplateSearcher(reg)
        results = searcher.search("data", category=TemplateCategory.ANALYSIS)
        assert all(r.template.category == TemplateCategory.ANALYSIS for r in results)

    def test_search_with_tags_filter(self, tmp_path: Path) -> None:
        reg = _make_registry(
            tmp_path,
            [
                ("monitoring", "Health Check", "Monitor", ["health", "alert"]),
            ],
        )
        searcher = TemplateSearcher(reg)
        results = searcher.search("health", tags=["alert"])
        assert len(results) >= 1

    def test_search_empty_query(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [("monitoring", "X", "Y", [])])
        searcher = TemplateSearcher(reg)
        results = searcher.search("", limit=5)
        assert results == []

    def test_search_respects_limit(self, tmp_path: Path) -> None:
        reg = _make_registry(
            tmp_path,
            [
                ("monitoring", "Health A", "Health", ["health"]),
                ("monitoring", "Health B", "Health", ["health"]),
            ],
        )
        searcher = TemplateSearcher(reg)
        results = searcher.search("health", limit=1)
        assert len(results) <= 1

    def test_recommend_with_use_case(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [("monitoring", "Health Check", "Monitor", ["health"])])
        searcher = TemplateSearcher(reg)
        results = searcher.recommend(context={"use_case": "health"}, limit=3)
        assert len(results) >= 1

    def test_recommend_without_context(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [("monitoring", "X", "Y", [])])
        searcher = TemplateSearcher(reg)
        results = searcher.recommend(limit=5)
        assert len(results) >= 1
        assert results[0].match_reason == "recommended"
