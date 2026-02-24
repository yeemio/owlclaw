"""Unit tests for OwlHub static site generator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.owlhub.site import SiteGenerator


def _sample_index() -> dict:
    return {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 1,
        "skills": [
            {
                "manifest": {
                    "name": "entry-monitor",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "Monitor entries",
                    "tags": ["trading", "monitor"],
                },
                "download_url": "https://example.com/entry-monitor-1.0.0.tar.gz",
                "published_at": "2026-02-20T00:00:00+00:00",
                "statistics": {"total_downloads": 10, "downloads_last_30d": 6},
            }
        ],
        "search_index": [
            {
                "id": "acme/entry-monitor@1.0.0",
                "name": "entry-monitor",
                "publisher": "acme",
                "version": "1.0.0",
                "tags": ["trading", "monitor"],
                "search_text": "entry-monitor monitor entries trading monitor",
            }
        ],
    }


def test_generate_site_pages_and_metadata(tmp_path: Path) -> None:
    generator = SiteGenerator()
    generator.generate(index_data=_sample_index(), output_dir=tmp_path, base_url="https://owlhub.example")

    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "search.html").exists()
    assert (tmp_path / "skills" / "acme-entry-monitor-1.0.0.html").exists()
    assert (tmp_path / "rss.xml").exists()
    assert (tmp_path / "sitemap.xml").exists()
    assert (tmp_path / "search-index.json").exists()
    assert (tmp_path / "dashboard.html").exists()


def test_generated_html_contains_skill_content(tmp_path: Path) -> None:
    generator = SiteGenerator()
    generator.generate(index_data=_sample_index(), output_dir=tmp_path)
    index_html = (tmp_path / "index.html").read_text(encoding="utf-8")
    detail_html = (tmp_path / "skills" / "acme-entry-monitor-1.0.0.html").read_text(encoding="utf-8")

    assert "entry-monitor" in index_html
    assert "Monitor entries" in index_html
    assert "Download package" in detail_html


def test_generated_rss_sitemap_and_search_index(tmp_path: Path) -> None:
    generator = SiteGenerator()
    generator.generate(index_data=_sample_index(), output_dir=tmp_path, base_url="https://owlhub.example")

    rss = (tmp_path / "rss.xml").read_text(encoding="utf-8")
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    search_index = json.loads((tmp_path / "search-index.json").read_text(encoding="utf-8"))

    assert "<rss" in rss
    assert "entry-monitor" in rss
    assert "<urlset" in sitemap
    assert "skills/acme-entry-monitor-1.0.0.html" in sitemap
    assert len(search_index) == 1
    assert search_index[0]["id"] == "acme/entry-monitor@1.0.0"


@settings(max_examples=50, deadline=None)
@given(
    name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=12),
    publisher=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=12),
    version=st.text(alphabet="0123456789.", min_size=5, max_size=10),
    description=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=5, max_size=40),
)
def test_property_7_skill_detail_contains_required_fields(
    name: str,
    publisher: str,
    version: str,
    description: str,
) -> None:
    """Property 7: detail page contains required skill information."""
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": 1,
        "skills": [
            {
                "manifest": {
                    "name": name,
                    "publisher": publisher,
                    "version": version,
                    "description": description,
                    "tags": ["demo"],
                },
                "download_url": "https://example.com/demo.tar.gz",
                "statistics": {"total_downloads": 1, "downloads_last_30d": 1},
            }
        ],
        "search_index": [],
    }
    generator = SiteGenerator()
    with tempfile.TemporaryDirectory() as workdir:
        output_dir = Path(workdir) / f"case-{publisher}-{name}-{version}"
        generator.generate(index_data=index, output_dir=output_dir)
        detail = (output_dir / "skills" / f"{publisher}-{name}-{version}.html").read_text(encoding="utf-8")
        assert name in detail
        assert publisher in detail
        assert version in detail
        assert description in detail


@settings(max_examples=50, deadline=None)
@given(
    count=st.integers(min_value=1, max_value=40),
    page_size=st.integers(min_value=1, max_value=10),
)
def test_property_8_pagination_consistency(count: int, page_size: int) -> None:
    """Property 8: pagination covers all skills without duplicates."""
    skills = []
    for i in range(count):
        skills.append(
            {
                "manifest": {
                    "name": f"skill-{i}",
                    "publisher": "acme",
                    "version": "1.0.0",
                    "description": "demo",
                    "tags": ["p"],
                },
                "download_url": f"https://example.com/{i}.tar.gz",
                "statistics": {"total_downloads": i, "downloads_last_30d": i},
            }
        )
    index = {
        "version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "total_skills": len(skills),
        "skills": skills,
        "search_index": [],
    }

    generator = SiteGenerator()
    with tempfile.TemporaryDirectory() as workdir:
        output_dir = Path(workdir) / f"case-{count}-{page_size}"
        generator.generate(index_data=index, output_dir=output_dir, page_size=page_size)

        rendered_ids: list[str] = []
        html_files = [output_dir / "index.html"]
        pages_dir = output_dir / "pages"
        if pages_dir.exists():
            html_files.extend(sorted(pages_dir.glob("page-*.html")))
        for html in html_files:
            text = html.read_text(encoding="utf-8")
            for i in range(count):
                marker = f'data-skill-id="acme/skill-{i}@1.0.0"'
                if marker in text:
                    rendered_ids.append(f"acme/skill-{i}@1.0.0")

        assert len(rendered_ids) == len(set(rendered_ids))
        assert len(set(rendered_ids)) == count
