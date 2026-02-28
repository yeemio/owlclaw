"""Validate content publication evidence and emit a summary report."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENGLISH_CHANNELS = {"reddit", "hackernews", "hn"}
CHINESE_CHANNELS = {"juejin", "v2ex"}


@dataclass(frozen=True)
class PublicationItem:
    channel: str
    url: str
    language: str
    title: str
    published_at: str


def _normalize_channel(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"hacker news", "hackernews", "hn", "show hn"}:
        return "hackernews"
    return value


def _normalize_language(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"en", "english"}:
        return "en"
    if value in {"zh", "cn", "chinese"}:
        return "zh"
    return value


def load_items(path: Path) -> list[PublicationItem]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Publication evidence JSON must be a list")

    items: list[PublicationItem] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Entry #{idx} must be an object")
        channel = _normalize_channel(str(item.get("channel", "")))
        url = str(item.get("url", "")).strip()
        language = _normalize_language(str(item.get("language", "")))
        title = str(item.get("title", "")).strip()
        published_at = str(item.get("published_at", "")).strip()
        if not channel:
            raise ValueError(f"Entry #{idx} missing channel")
        if not url.startswith("http://") and not url.startswith("https://"):
            raise ValueError(f"Entry #{idx} has invalid url: {url}")
        if language not in {"en", "zh"}:
            raise ValueError(f"Entry #{idx} language must be en/zh")
        if not title:
            raise ValueError(f"Entry #{idx} missing title")
        if not published_at:
            raise ValueError(f"Entry #{idx} missing published_at")
        items.append(
            PublicationItem(
                channel=channel,
                url=url,
                language=language,
                title=title,
                published_at=published_at,
            )
        )
    return items


def _coerce_item(item: PublicationItem | dict[str, Any]) -> PublicationItem:
    if isinstance(item, PublicationItem):
        return item
    if isinstance(item, dict):
        return PublicationItem(
            channel=_normalize_channel(str(item.get("channel", ""))),
            url=str(item.get("url", "")).strip(),
            language=_normalize_language(str(item.get("language", ""))),
            title=str(item.get("title", "")).strip(),
            published_at=str(item.get("published_at", "")).strip(),
        )
    raise TypeError("Unsupported publication item type")


def evaluate(items: list[PublicationItem | dict[str, Any]]) -> dict[str, Any]:
    normalized_items = [_coerce_item(item) for item in items]
    channels = {item.channel for item in normalized_items}
    unique_count = len(channels)
    has_english = any(item.channel in ENGLISH_CHANNELS and item.language == "en" for item in normalized_items)
    has_chinese = any(item.channel in CHINESE_CHANNELS and item.language == "zh" for item in normalized_items)
    meets_2_6 = has_english
    meets_2_7 = has_chinese
    meets_5_1 = unique_count >= 2
    return {
        "total_posts": len(normalized_items),
        "unique_channels": sorted(channels),
        "meets_task_2_6": meets_2_6,
        "meets_task_2_7": meets_2_7,
        "meets_task_5_1": meets_5_1,
        "all_required_passed": meets_2_6 and meets_2_7 and meets_5_1,
        "posts": [item.__dict__ for item in normalized_items],
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Content Publication Evidence",
        "",
        "## Gate Status",
        "",
        f"- Task 2.6 (Reddit/HN English): `{result['meets_task_2_6']}`",
        f"- Task 2.7 (掘金/V2EX Chinese): `{result['meets_task_2_7']}`",
        f"- Task 5.1 (>=2 channels): `{result['meets_task_5_1']}`",
        f"- All required passed: `{result['all_required_passed']}`",
        "",
        "## Published Posts",
        "",
        "| Channel | Language | Published At | Title | URL |",
        "|---|---|---|---|---|",
    ]
    for post in result["posts"]:
        assert isinstance(post, dict)
        lines.append(
            f"| {post['channel']} | {post['language']} | {post['published_at']} | "
            f"{post['title']} | {post['url']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Record publication evidence for content-launch tasks.")
    parser.add_argument("--input-json", required=True, help="JSON list with publication entries.")
    parser.add_argument("--output-json", default="docs/content/publication-evidence.json")
    parser.add_argument("--output-md", default="docs/content/publication-evidence.md")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    items = load_items(input_path)
    result = evaluate(items)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    output_md.write_text(render_markdown(result), encoding="utf-8")

    print(f"[publication] wrote {output_json}")
    print(f"[publication] wrote {output_md}")
    print(f"[publication] all_required_passed={result['all_required_passed']}")


if __name__ == "__main__":
    main()
