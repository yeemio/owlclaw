"""OwlHub CLI client for search/install/update workflows."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from packaging.version import InvalidVersion, Version

from owlclaw.owlhub.indexer.builder import IndexBuilder
from owlclaw.owlhub.validator import Validator


@dataclass(frozen=True)
class SearchResult:
    """One search hit from OwlHub index."""

    name: str
    publisher: str
    version: str
    description: str
    tags: list[str]
    version_state: str
    download_url: str
    checksum: str


class OwlHubClient:
    """Read OwlHub index and perform local install/update operations."""

    def __init__(self, *, index_url: str, install_dir: Path, lock_file: Path):
        self.index_url = index_url
        self.install_dir = install_dir
        self.lock_file = lock_file
        self.validator = Validator()
        self.index_builder = IndexBuilder()
        self.last_install_warning: str | None = None

    def search(
        self,
        query: str = "",
        tags: list[str] | None = None,
        tag_mode: str = "and",
        include_draft: bool = False,
    ) -> list[SearchResult]:
        """Search skills by name/description and optional tags."""
        data = self._load_index()
        normalized_query = query.strip().lower()
        requested_tags = {tag.strip().lower() for tag in (tags or []) if tag.strip()}
        normalized_mode = tag_mode.strip().lower()
        if normalized_mode not in {"and", "or"}:
            normalized_mode = "and"

        results: list[SearchResult] = []
        for entry in data.get("skills", []):
            manifest = entry.get("manifest", {})
            name = str(manifest.get("name", "")).strip()
            description = str(manifest.get("description", "")).strip()
            publisher = str(manifest.get("publisher", "")).strip()
            if _is_hidden_entry(entry):
                continue
            version = str(manifest.get("version", "")).strip()
            version_state = str(entry.get("version_state", "released")).strip().lower()
            skill_tags = {
                str(tag).strip().lower()
                for tag in manifest.get("tags", [])
                if isinstance(tag, str) and tag.strip()
            }

            if normalized_query and normalized_query not in f"{name} {description}".lower():
                continue
            if not include_draft and version_state == "draft":
                continue
            if requested_tags:
                if normalized_mode == "and" and not requested_tags.issubset(skill_tags):
                    continue
                if normalized_mode == "or" and requested_tags.isdisjoint(skill_tags):
                    continue
            results.append(
                SearchResult(
                    name=name,
                    publisher=publisher,
                    version=version,
                    description=description,
                    tags=sorted(skill_tags),
                    version_state=version_state,
                    download_url=str(entry.get("download_url", "")),
                    checksum=str(entry.get("checksum", "")),
                )
            )

        results.sort(key=lambda item: (item.name, item.version), reverse=False)
        return results

    def install(self, *, name: str, version: str | None = None) -> Path:
        """Install one skill by name and optional exact version."""
        candidates = self.search(query=name)
        matched = [item for item in candidates if item.name == name]
        if version is not None:
            matched = [item for item in matched if item.version == version]
        if not matched:
            raise ValueError(f"skill not found: {name}{'@' + version if version else ''}")
        selected = sorted(matched, key=lambda item: item.version)[-1]
        self.last_install_warning = None
        source_entry = _find_source_entry(self._load_index(), selected)
        if source_entry is not None and _is_hidden_entry(source_entry):
            raise ValueError(f"skill {selected.publisher}/{selected.name} is blocked by moderation policy")
        if selected.version_state == "deprecated":
            self.last_install_warning = f"skill {selected.name}@{selected.version} is deprecated"

        downloaded = self._download(selected.download_url)
        actual_checksum = self.index_builder.calculate_checksum(downloaded)
        if selected.checksum and actual_checksum != selected.checksum:
            raise ValueError("checksum verification failed")

        target = self.install_dir / selected.name / selected.version
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)

        if tarfile.is_tarfile(downloaded):
            with tarfile.open(downloaded, "r:*") as archive:
                archive.extractall(target)
        else:
            if downloaded.is_dir():
                shutil.copytree(downloaded, target, dirs_exist_ok=True)
            else:
                shutil.copy2(downloaded, target / downloaded.name)

        self._validate_install(target)
        self._write_lock(selected, target)
        return target

    def list_installed(self) -> list[dict[str, Any]]:
        """List installed skills from lock file."""
        if not self.lock_file.exists():
            return []
        data = json.loads(self.lock_file.read_text(encoding="utf-8"))
        skills = data.get("skills", [])
        return skills if isinstance(skills, list) else []

    def update(self, name: str | None = None) -> list[dict[str, str]]:
        """Update one installed skill (or all) to latest indexed version."""
        installed = self.list_installed()
        if not installed:
            return []

        updates: list[dict[str, str]] = []
        for item in installed:
            skill_name = str(item.get("name", "")).strip()
            current_version = str(item.get("version", "")).strip()
            if not skill_name:
                continue
            if name and skill_name != name:
                continue

            latest = self._resolve_latest_version(skill_name)
            if latest is None:
                continue
            if _compare_version(latest.version, current_version) <= 0:
                continue

            self.install(name=skill_name, version=latest.version)
            updates.append(
                {
                    "name": skill_name,
                    "from_version": current_version,
                    "to_version": latest.version,
                }
            )

        return updates

    def validate_local(self, path: Path) -> bool:
        """Validate a local skill package path."""
        structure = self.validator.validate_structure(path)
        return structure.is_valid

    def _load_index(self) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(self.index_url)
        if parsed.scheme in {"http", "https"}:
            with urllib.request.urlopen(self.index_url, timeout=30) as response:
                payload = response.read().decode("utf-8")
            return cast(dict[str, Any], json.loads(payload))
        path = Path(self.index_url.replace("file://", "")).resolve()
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    def _download(self, url: str) -> Path:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme in {"http", "https"}:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pkg") as handle:
                handle.write(data)
                return Path(handle.name)
        if parsed.scheme == "file":
            return Path(parsed.path).resolve()
        return Path(url).resolve()

    def _validate_install(self, installed_path: Path) -> None:
        if not any(installed_path.rglob("SKILL.md")):
            raise ValueError("installed package missing SKILL.md")

    def _resolve_latest_version(self, name: str) -> SearchResult | None:
        candidates = self.search(query=name)
        matched = [item for item in candidates if item.name == name]
        if not matched:
            return None
        matched.sort(key=lambda item: _version_sort_key(item.version))
        return matched[-1]

    def _write_lock(self, selected: SearchResult, target: Path) -> None:
        existing = {"version": "1.0", "generated_at": "", "skills": []}
        if self.lock_file.exists():
            loaded = json.loads(self.lock_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing.update(loaded)

        skills: list[dict[str, Any]] = []
        raw_skills = existing.get("skills", [])
        if isinstance(raw_skills, list):
            for item in raw_skills:
                if isinstance(item, dict) and item.get("name") != selected.name:
                    skills.append(item)
        skills.append(
            {
                "name": selected.name,
                "publisher": selected.publisher,
                "version": selected.version,
                "download_url": selected.download_url,
                "checksum": selected.checksum,
                "install_path": str(target),
                "version_state": selected.version_state,
            }
        )
        payload = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "skills": sorted(skills, key=lambda item: str(item.get("name", ""))),
        }
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _version_sort_key(version_text: str) -> tuple[int, Version | str]:
    try:
        return (1, Version(version_text))
    except InvalidVersion:
        return (0, version_text)


def _compare_version(left: str, right: str) -> int:
    left_key = _version_sort_key(left)
    right_key = _version_sort_key(right)
    if left_key > right_key:
        return 1
    if left_key < right_key:
        return -1
    return 0


def _is_hidden_entry(entry: dict[str, Any]) -> bool:
    takedown = entry.get("takedown", {})
    if isinstance(takedown, dict) and bool(takedown.get("is_taken_down", False)):
        return True
    if bool(entry.get("is_taken_down", False)):
        return True
    return bool(entry.get("blacklisted", False))


def _find_source_entry(index_data: dict[str, Any], selected: SearchResult) -> dict[str, Any] | None:
    skills = index_data.get("skills", [])
    if not isinstance(skills, list):
        return None
    for entry in skills:
        manifest = entry.get("manifest", {})
        if (
            str(manifest.get("publisher", "")) == selected.publisher
            and str(manifest.get("name", "")) == selected.name
            and str(manifest.get("version", "")) == selected.version
        ):
            return entry if isinstance(entry, dict) else None
    return None
