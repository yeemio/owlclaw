"""Static site generator for OwlHub index data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass(frozen=True)
class SkillPage:
    """Rendered page info for one skill version."""

    url_path: str
    file_path: Path


class SiteGenerator:
    """Generate static HTML pages and metadata artifacts from index payload."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        default_templates = Path(__file__).resolve().parent / "templates"
        self.templates_dir = templates_dir or default_templates
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, *, index_data: dict[str, Any], output_dir: Path, base_url: str = "https://owlhub.local") -> None:
        """Generate index/detail/search pages, rss feed, sitemap and search metadata."""
        output_dir.mkdir(parents=True, exist_ok=True)
        skills = index_data.get("skills", [])
        generated_at = str(index_data.get("generated_at", ""))
        pages = self._render_pages(skills=skills, generated_at=generated_at, output_dir=output_dir)

        search_index_path = output_dir / "search-index.json"
        search_index = index_data.get("search_index", [])
        search_index_path.write_text(json.dumps(search_index, ensure_ascii=False, indent=2), encoding="utf-8")

        rss_path = output_dir / "rss.xml"
        rss_path.write_text(self._build_rss(skills=skills, base_url=base_url), encoding="utf-8")

        sitemap_path = output_dir / "sitemap.xml"
        sitemap_path.write_text(self._build_sitemap(pages=pages, base_url=base_url), encoding="utf-8")

    def _render_pages(self, *, skills: list[dict[str, Any]], generated_at: str, output_dir: Path) -> list[SkillPage]:
        pages: list[SkillPage] = []
        normalized_skills = [self._normalize_skill(item) for item in skills]

        index_template = self._env.get_template("index.html")
        index_output = output_dir / "index.html"
        index_output.write_text(index_template.render(skills=normalized_skills, generated_at=generated_at), encoding="utf-8")
        pages.append(SkillPage(url_path="/index.html", file_path=index_output))

        search_template = self._env.get_template("search.html")
        search_output = output_dir / "search.html"
        search_output.write_text(search_template.render(skills=normalized_skills, generated_at=generated_at), encoding="utf-8")
        pages.append(SkillPage(url_path="/search.html", file_path=search_output))

        detail_template = self._env.get_template("skill_detail.html")
        skills_dir = output_dir / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        for item in normalized_skills:
            slug = f"{item['publisher']}-{item['name']}-{item['version']}".replace("/", "-")
            file_name = f"{slug}.html"
            detail_path = skills_dir / file_name
            detail_path.write_text(detail_template.render(skill=item, generated_at=generated_at), encoding="utf-8")
            pages.append(SkillPage(url_path=f"/skills/{file_name}", file_path=detail_path))

        return pages

    @staticmethod
    def _normalize_skill(item: dict[str, Any]) -> dict[str, Any]:
        manifest = item.get("manifest", {})
        return {
            "name": str(manifest.get("name", "")),
            "publisher": str(manifest.get("publisher", "")),
            "version": str(manifest.get("version", "")),
            "description": str(manifest.get("description", "")),
            "tags": [tag for tag in manifest.get("tags", []) if isinstance(tag, str)],
            "download_url": str(item.get("download_url", "")),
            "statistics": item.get("statistics", {}),
        }

    @staticmethod
    def _build_rss(*, skills: list[dict[str, Any]], base_url: str) -> str:
        now = datetime.now(timezone.utc).isoformat()
        items: list[str] = []
        for item in skills:
            manifest = item.get("manifest", {})
            name = escape(str(manifest.get("name", "")))
            publisher = escape(str(manifest.get("publisher", "")))
            version = escape(str(manifest.get("version", "")))
            description = escape(str(manifest.get("description", "")))
            slug = f"{publisher}-{name}-{version}".replace("/", "-")
            link = f"{base_url.rstrip('/')}/skills/{slug}.html"
            items.append(
                "<item>"
                f"<title>{name} {version}</title>"
                f"<link>{link}</link>"
                f"<description>{description}</description>"
                f"<pubDate>{escape(str(item.get('published_at', now)))}</pubDate>"
                "</item>"
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<rss version=\"2.0\"><channel>"
            "<title>OwlHub Updates</title>"
            f"<link>{base_url.rstrip('/')}</link>"
            "<description>Latest skill updates from OwlHub</description>"
            f"<lastBuildDate>{now}</lastBuildDate>"
            f"{''.join(items)}"
            "</channel></rss>"
        )

    @staticmethod
    def _build_sitemap(*, pages: list[SkillPage], base_url: str) -> str:
        now = datetime.now(timezone.utc).date().isoformat()
        urls = [
            "<url>"
            f"<loc>{escape(base_url.rstrip('/') + page.url_path)}</loc>"
            f"<lastmod>{now}</lastmod>"
            "</url>"
            for page in pages
        ]
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            f"{''.join(urls)}"
            "</urlset>"
        )
