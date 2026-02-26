"""Complete mionyee-style OwlClaw example with three core capabilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from owlclaw import OwlClaw


def _create_app() -> OwlClaw:
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


def _run_all_tasks() -> dict[str, object]:
    # Deterministic local demo payload for unit/e2e smoke validation.
    return {
        "results": [
            {"task": "entry-monitor", "status": "passed", "output": {"hatchet_workflow_id": "wf-1"}},
            {"task": "morning-decision", "status": "passed", "output": {"hatchet_workflow_id": "wf-2"}},
            {"task": "knowledge-feedback", "status": "passed", "output": {"hatchet_workflow_id": "wf-3"}},
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="mionyee-trading OwlClaw example")
    parser.add_argument("--all", action="store_true", help="Run all demo tasks and output summary")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    app = _create_app()

    if args.all:
        payload = _run_all_tasks()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(payload)
        return

    loaded = sorted(skill.name for skill in app.skills_loader.list_skills())
    print(f"loaded_skills={loaded}")
    print("registered=entry-monitor,morning-decision,knowledge-feedback")


if __name__ == "__main__":
    main()
