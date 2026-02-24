"""Unit tests for OwlHub static site generator."""

from __future__ import annotations

import json
from pathlib import Path

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
