"""Unit tests for owlclaw.templates.skills.searcher (skill-templates Task 6)."""

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

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

    def test_search_with_non_positive_limit_returns_empty(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [("monitoring", "Health", "Monitor", ["health"])])
        searcher = TemplateSearcher(reg)
        assert searcher.search("health", limit=0) == []
        assert searcher.search("health", limit=-1) == []

    def test_recommend_with_non_positive_limit_returns_empty(self, tmp_path: Path) -> None:
        reg = _make_registry(tmp_path, [("monitoring", "X", "Y", [])])
        searcher = TemplateSearcher(reg)
        assert searcher.recommend(limit=0) == []
        assert searcher.recommend(limit=-1) == []

    @settings(max_examples=30, deadline=None)
    @given(
        templates=st.lists(
            st.tuples(
                st.sampled_from([c.value for c in TemplateCategory]),
                st.from_regex(r"[A-Z][a-z]{2,12}", fullmatch=True),
                st.text(min_size=5, max_size=40),
                st.lists(st.from_regex(r"[a-z]{3,10}", fullmatch=True), min_size=0, max_size=3, unique=True),
            ),
            min_size=1,
            max_size=12,
            unique_by=lambda t: (t[0], t[1]),
        ),
        query=st.text(min_size=1, max_size=10).filter(lambda q: bool(q.strip())),
    )
    def test_property_search_results_sorted_by_relevance(
        self,
        templates: list[tuple[str, str, str, list[str]]],
        query: str,
    ) -> None:
        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(Path(tmp_dir), templates)
            results = TemplateSearcher(reg).search(query, limit=20)
            for idx in range(len(results) - 1):
                assert results[idx].score >= results[idx + 1].score

    @settings(max_examples=30, deadline=None)
    @given(
        templates=st.lists(
            st.tuples(
                st.sampled_from([c.value for c in TemplateCategory]),
                st.from_regex(r"[A-Z][a-z]{2,12}", fullmatch=True),
                st.text(min_size=5, max_size=40),
                st.lists(st.from_regex(r"[a-z]{3,10}", fullmatch=True), min_size=0, max_size=3, unique=True),
            ),
            min_size=1,
            max_size=12,
            unique_by=lambda t: (t[0], t[1]),
        )
    )
    def test_property_search_results_are_unique(self, templates: list[tuple[str, str, str, list[str]]]) -> None:
        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(Path(tmp_dir), templates)
            results = TemplateSearcher(reg).search("a", limit=20)
            ids = [r.template.id for r in results]
            assert len(ids) == len(set(ids))

    @settings(max_examples=30, deadline=None)
    @given(
        target_category=st.sampled_from(list(TemplateCategory)),
        names=st.lists(st.from_regex(r"[A-Z][a-z]{2,10}", fullmatch=True), min_size=1, max_size=8, unique=True),
    )
    def test_property_category_filtering(self, target_category: TemplateCategory, names: list[str]) -> None:
        templates: list[tuple[str, str, str, list[str]]] = []
        for name in names:
            templates.append((target_category.value, f"{name} Health", "health monitor", ["health"]))
            templates.append(("analysis", f"{name} Data", "data analyzer", ["data"]))
        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(Path(tmp_dir), templates)
            results = TemplateSearcher(reg).search("health", category=target_category, limit=50)
            assert all(r.template.category == target_category for r in results)

    @settings(max_examples=30, deadline=None)
    @given(
        tag=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
        other_tag=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
    )
    def test_property_tag_filtering(self, tag: str, other_tag: str) -> None:
        templates = [
            ("monitoring", "Health Check", "monitor health", [tag]),
            ("monitoring", "Metric Watch", "monitor metric", [other_tag]),
        ]
        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(Path(tmp_dir), templates)
            results = TemplateSearcher(reg).search("monitor", tags=[tag], limit=20)
            assert all(tag in r.template.tags for r in results)

    @settings(max_examples=30, deadline=None)
    @given(
        keyword=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
        category=st.sampled_from(list(TemplateCategory)),
    )
    def test_property_search_coverage(self, keyword: str, category: TemplateCategory) -> None:
        templates = [
            (category.value, "Target Skill", f"This template handles {keyword} workflows", [keyword]),
            ("monitoring", "Other Skill", "No related text", ["other"]),
        ]
        with TemporaryDirectory() as tmp_dir:
            reg = _make_registry(Path(tmp_dir), templates)
            results = TemplateSearcher(reg).search(keyword, limit=20)
            assert any(r.template.id == f"{category.value}/target-skill" for r in results)
