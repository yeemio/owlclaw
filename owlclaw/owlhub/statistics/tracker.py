"""Statistics tracking primitives for OwlHub."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillStatistics:
    """Aggregated statistics for one skill."""

    skill_name: str
    publisher: str
    total_downloads: int
    downloads_last_30d: int
    total_installs: int
    active_installs: int
    last_updated: datetime


@dataclass
class _CachedReleaseStats:
    total_downloads: int
    downloads_last_30d: int
    last_updated: datetime
    expires_at: datetime


class StatisticsTracker:
    """Track skill usage statistics using local events and GitHub release data."""

    def __init__(
        self,
        *,
        github_token: str | None = None,
        cache_ttl_seconds: int = 3600,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.github_token = github_token
        self.cache_ttl_seconds = cache_ttl_seconds
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._download_events: dict[tuple[str, str], list[datetime]] = {}
        self._install_events: dict[tuple[str, str], list[tuple[str, datetime]]] = {}
        self._cache: dict[str, _CachedReleaseStats] = {}

    def record_download(
        self,
        *,
        skill_name: str,
        publisher: str,
        version: str,
        occurred_at: datetime | None = None,
    ) -> None:
        """Record one local download event."""
        _ = version
        key = (publisher, skill_name)
        self._download_events.setdefault(key, []).append(occurred_at or self._now_fn())

    def record_install(
        self,
        *,
        skill_name: str,
        publisher: str,
        version: str,
        user_id: str,
        occurred_at: datetime | None = None,
    ) -> None:
        """Record one local install event."""
        _ = version
        key = (publisher, skill_name)
        self._install_events.setdefault(key, []).append((user_id, occurred_at or self._now_fn()))

    def get_statistics(self, *, skill_name: str, publisher: str, repository: str | None = None) -> SkillStatistics:
        """Aggregate local events and optional GitHub release download metrics."""
        github_total = 0
        github_last_30d = 0
        github_updated = self._now_fn()
        if repository:
            github_total, github_last_30d, github_updated = self._get_github_release_stats(repository)

        now = self._now_fn()
        window_start = now - timedelta(days=30)
        key = (publisher, skill_name)

        downloads = self._download_events.get(key, [])
        installs = self._install_events.get(key, [])

        local_total_downloads = len(downloads)
        local_downloads_30d = sum(1 for event_time in downloads if event_time >= window_start)
        local_total_installs = len(installs)
        active_users = {user_id for user_id, event_time in installs if event_time >= window_start}

        return SkillStatistics(
            skill_name=skill_name,
            publisher=publisher,
            total_downloads=github_total + local_total_downloads,
            downloads_last_30d=github_last_30d + local_downloads_30d,
            total_installs=local_total_installs,
            active_installs=len(active_users),
            last_updated=max(github_updated, now),
        )

    def _get_github_release_stats(self, repository: str) -> tuple[int, int, datetime]:
        cached = self._cache.get(repository)
        now = self._now_fn()
        if cached and cached.expires_at > now:
            return (cached.total_downloads, cached.downloads_last_30d, cached.last_updated)

        owner_repo = self._normalize_repository(repository)
        if owner_repo is None:
            logger.warning("Unsupported repository format for statistics: %s", repository)
            return (0, 0, now)
        owner, repo = owner_repo
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        request = urllib.request.Request(url, headers=self._build_headers())
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                logger.warning("GitHub API rate limited for %s/%s", owner, repo)
            else:
                logger.warning("GitHub API request failed for %s/%s: %s", owner, repo, exc)
            return (0, 0, now)
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            logger.warning("Failed to fetch GitHub statistics for %s/%s: %s", owner, repo, exc)
            return (0, 0, now)

        total_downloads = 0
        downloads_last_30d = 0
        window_start = now - timedelta(days=30)
        for release in payload if isinstance(payload, list) else []:
            if not isinstance(release, dict):
                continue
            published_at_text = str(release.get("published_at", "")).strip()
            published_at = _parse_datetime(published_at_text)
            release_downloads = 0
            for asset in release.get("assets", []):
                if isinstance(asset, dict):
                    count = asset.get("download_count", 0)
                    if isinstance(count, int):
                        release_downloads += count
            total_downloads += release_downloads
            if published_at and published_at >= window_start:
                downloads_last_30d += release_downloads

        cached_value = _CachedReleaseStats(
            total_downloads=total_downloads,
            downloads_last_30d=downloads_last_30d,
            last_updated=now,
            expires_at=now + timedelta(seconds=self.cache_ttl_seconds),
        )
        self._cache[repository] = cached_value
        return (total_downloads, downloads_last_30d, now)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "owlclaw-owlhub"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    @staticmethod
    def _normalize_repository(repository: str) -> tuple[str, str] | None:
        if "/" in repository and not repository.startswith("http"):
            owner, repo = repository.split("/", 1)
            if owner and repo:
                return (owner, repo)
        parsed = urllib.parse.urlparse(repository)
        if parsed.netloc != "github.com":
            return None
        parts = [segment for segment in parsed.path.split("/") if segment]
        if len(parts) < 2:
            return None
        return (parts[0], parts[1].removesuffix(".git"))


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
