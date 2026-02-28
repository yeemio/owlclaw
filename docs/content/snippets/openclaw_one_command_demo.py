"""Runnable 3-step demo snippet for content article draft."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from owlclaw import OwlClaw

def _prepare_runtime(runtime_dir: Path) -> Path:
    soul = runtime_dir / "SOUL.md"
    identity = runtime_dir / "IDENTITY.md"
    soul.write_text("# Article Demo Agent\n\nYou are a practical assistant.\n", encoding="utf-8")
    identity.write_text("# Identity\n\n- Role: demo agent\n", encoding="utf-8")

    skills_dir = runtime_dir / "skills"
    skill_dir = skills_dir / "demo-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: demo-skill
description: Demo skill for article quick start.
metadata:
  version: "1.0.0"
owlclaw:
  task_type: ops
---
# Demo skill
""",
        encoding="utf-8",
    )
    return skills_dir


async def run_demo() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="owlclaw-article-demo-") as tmp:
        runtime_dir = Path(tmp)
        skills_dir = _prepare_runtime(runtime_dir)
        app = OwlClaw.lite("article-demo", skills_path=str(skills_dir), heartbeat_interval_minutes=1)

        @app.handler("demo-skill")
        async def demo_skill(session: dict[str, Any]) -> dict[str, Any]:
            return {
                "status": "ok",
                "tenant_id": session.get("tenant_id", "t-1"),
                "message": "OpenClaw can call OwlClaw capabilities.",
            }

        runtime = await app.start(app_dir=str(runtime_dir))
        try:
            if app.registry is None:
                raise RuntimeError("registry is not initialized")
            result = await app.registry.invoke_handler("demo-skill", session={"tenant_id": "t-1"})
            return {
                "runtime_initialized": runtime.is_initialized,
                "step_1_install": True,
                "step_2_configure": True,
                "step_3_use": True,
                "result": result,
            }
        finally:
            await app.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw one-command demo snippet")
    parser.add_argument("--once", action="store_true", help="Run once and print JSON output.")
    args = parser.parse_args()

    payload = asyncio.run(run_demo())
    if args.once:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
