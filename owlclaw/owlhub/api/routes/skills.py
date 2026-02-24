"""Read-only skill endpoints for OwlHub API."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query

from owlclaw.owlhub.api.schemas import SkillDetail, SkillSearchItem, SkillSearchResponse, VersionInfo

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


@lru_cache(maxsize=1)
def _load_index() -> dict[str, Any]:
    index_path = Path(os.getenv("OWLHUB_INDEX_PATH", "./index.json")).resolve()
    if not index_path.exists():
        return {"skills": []}
    return cast(dict[str, Any], json.loads(index_path.read_text(encoding="utf-8")))


def _iter_skills() -> list[dict]:
    data = _load_index()
    skills = data.get("skills", [])
    return skills if isinstance(skills, list) else []


@router.get("", response_model=SkillSearchResponse)
def search_skills(
    query: str = "",
    tags: str = "",
    sort_by: str = Query("name", pattern="^(name|updated_at|downloads)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> SkillSearchResponse:
    requested_tags = {tag.strip().lower() for tag in tags.split(",") if tag.strip()}
    normalized_query = query.strip().lower()

    items: list[SkillSearchItem] = []
    for entry in _iter_skills():
        manifest = entry.get("manifest", {})
        name = str(manifest.get("name", "")).strip()
        publisher = str(manifest.get("publisher", "")).strip()
        version = str(manifest.get("version", "")).strip()
        description = str(manifest.get("description", "")).strip()
        skill_tags = [tag for tag in manifest.get("tags", []) if isinstance(tag, str)]
        lowered_tags = {tag.lower() for tag in skill_tags}
        if normalized_query and normalized_query not in f"{name} {description}".lower():
            continue
        if requested_tags and not requested_tags.issubset(lowered_tags):
            continue
        items.append(
            SkillSearchItem(
                name=name,
                publisher=publisher,
                version=version,
                description=description,
                tags=skill_tags,
                version_state=str(entry.get("version_state", "released")),
            )
        )

    if sort_by == "downloads":
        items.sort(
            key=lambda item: int(
                _find_statistics(item.publisher, item.name, item.version).get("total_downloads", 0)
            ),
            reverse=True,
        )
    elif sort_by == "updated_at":
        items.sort(
            key=lambda item: str(_find_updated_at(item.publisher, item.name, item.version)),
            reverse=True,
        )
    else:
        items.sort(key=lambda item: (item.name, item.version))

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return SkillSearchResponse(total=total, page=page, page_size=page_size, items=items[start:end])


@router.get("/{publisher}/{name}", response_model=SkillDetail)
def get_skill_detail(publisher: str, name: str) -> SkillDetail:
    entries = [entry for entry in _iter_skills() if _is_skill(entry, publisher, name)]
    if not entries:
        raise HTTPException(status_code=404, detail="skill not found")

    entries.sort(key=lambda entry: str(entry.get("manifest", {}).get("version", "")))
    latest = entries[-1]
    manifest = latest.get("manifest", {})
    versions = [
        VersionInfo(
            version=str(entry.get("manifest", {}).get("version", "")),
            version_state=str(entry.get("version_state", "released")),
            published_at=entry.get("published_at"),
            updated_at=entry.get("updated_at"),
        )
        for entry in entries
    ]
    return SkillDetail(
        name=str(manifest.get("name", "")),
        publisher=str(manifest.get("publisher", "")),
        description=str(manifest.get("description", "")),
        tags=[tag for tag in manifest.get("tags", []) if isinstance(tag, str)],
        dependencies=manifest.get("dependencies", {}) if isinstance(manifest.get("dependencies", {}), dict) else {},
        versions=versions,
        statistics=latest.get("statistics", {}) if isinstance(latest.get("statistics", {}), dict) else {},
    )


@router.get("/{publisher}/{name}/versions", response_model=list[VersionInfo])
def get_skill_versions(publisher: str, name: str) -> list[VersionInfo]:
    entries = [entry for entry in _iter_skills() if _is_skill(entry, publisher, name)]
    if not entries:
        raise HTTPException(status_code=404, detail="skill not found")
    entries.sort(key=lambda entry: str(entry.get("manifest", {}).get("version", "")))
    return [
        VersionInfo(
            version=str(entry.get("manifest", {}).get("version", "")),
            version_state=str(entry.get("version_state", "released")),
            published_at=entry.get("published_at"),
            updated_at=entry.get("updated_at"),
        )
        for entry in entries
    ]


def _is_skill(entry: dict, publisher: str, name: str) -> bool:
    manifest = entry.get("manifest", {})
    return str(manifest.get("publisher", "")) == publisher and str(manifest.get("name", "")) == name


def _find_statistics(publisher: str, name: str, version: str) -> dict:
    for entry in _iter_skills():
        manifest = entry.get("manifest", {})
        if (
            str(manifest.get("publisher", "")) == publisher
            and str(manifest.get("name", "")) == name
            and str(manifest.get("version", "")) == version
        ):
            stats = entry.get("statistics", {})
            return stats if isinstance(stats, dict) else {}
    return {}


def _find_updated_at(publisher: str, name: str, version: str) -> str:
    for entry in _iter_skills():
        manifest = entry.get("manifest", {})
        if (
            str(manifest.get("publisher", "")) == publisher
            and str(manifest.get("name", "")) == name
            and str(manifest.get("version", "")) == version
        ):
            return str(entry.get("updated_at", ""))
    return ""
