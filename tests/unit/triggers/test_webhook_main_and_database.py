from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from owlclaw.triggers.webhook import HttpGatewayConfig, WebhookDatabaseManager, build_webhook_application


@dataclass
class _Runtime:
    async def trigger(self, input_data: Any) -> dict[str, Any]:  # noqa: ARG002
        return {"execution_id": "main", "status": "completed"}


def test_webhook_application_lifecycle_and_health() -> None:
    app = build_webhook_application(runtime=_Runtime(), config=HttpGatewayConfig(tls_enabled=True))
    assert app.started is False
    import asyncio

    asyncio.run(app.start())
    health = asyncio.run(app.health_status())
    assert health["started"] is True
    assert health["tls_enabled"] is True
    asyncio.run(app.stop())
    assert app.started is False


def test_webhook_database_manager_migration_and_seed() -> None:
    manager = WebhookDatabaseManager()
    status1 = manager.run_migration("004_webhook")
    assert status1.current_version == "004_webhook"
    loaded = manager.load_seed_data([{"id": "seed-1"}, {"id": "seed-2"}])
    assert loaded == 2
    status2 = manager.status()
    assert status2.seeded_records == 2
