"""Complete mionyee-style OwlClaw example with three core capabilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from owlclaw import OwlClaw


def _build_app() -> OwlClaw:
    app = OwlClaw("mionyee-trading")
    base_dir = Path(__file__).parent
    app.mount_skills(str(base_dir / "skills"))

    @app.handler("entry-monitor")
    async def entry_monitor(session: dict) -> dict:
        symbols = session.get("symbols", ["AAPL", "MSFT"])
        return {
            "action": "scan_entry",
            "symbols": symbols,
            "signals": [],
            "reason": "Scheduled entry check completed.",
        }

    @app.handler("morning-decision")
    async def morning_decision(session: dict) -> dict:
        market_open = bool(session.get("market_open", True))
        if market_open:
            return {"priority": "entry-monitor", "next": ["entry-monitor", "knowledge-feedback"]}
        return {"priority": "knowledge-feedback", "next": ["knowledge-feedback"]}

    @app.handler("knowledge-feedback")
    async def knowledge_feedback(session: dict) -> dict:
        latest_trade = session.get("latest_trade", {"symbol": "AAPL", "pnl": 0.0})
        return {
            "recorded": True,
            "summary": f"Captured feedback for {latest_trade.get('symbol', 'UNKNOWN')}",
            "pnl": latest_trade.get("pnl", 0.0),
        }

    @app.state("portfolio_state")
    def portfolio_state() -> dict:
        return {
            "positions": 3,
            "cash_ratio": 0.27,
            "risk_mode": "normal",
        }

    return app


def _simulate_task_result(task_id: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "passed",
        "output": {
            "task_id": task_id,
            "hatchet_workflow_id": f"wf-{task_id}",
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mionyee-trading demo tasks.")
    parser.add_argument("--all", action="store_true", help="Run all demo tasks.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    app = _build_app()
    loaded = sorted(skill.name for skill in app.skills_loader.list_skills())

    if args.all:
        payload = {
            "results": [_simulate_task_result(task_id) for task_id in ("1", "2", "3")],
        }
        if args.json:
            print(json.dumps(payload))
            return
        print(payload)
        return

    print(f"loaded_skills={loaded}")
    print("registered=entry-monitor,morning-decision,knowledge-feedback")


if __name__ == "__main__":
    main()
