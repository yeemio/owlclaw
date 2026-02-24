from __future__ import annotations

import pytest

from owlclaw.integrations.queue_adapters import ensure_adapter_dependency


def test_ensure_adapter_dependency_allows_mock() -> None:
    ensure_adapter_dependency("mock")


def test_ensure_adapter_dependency_rejects_unknown_adapter() -> None:
    with pytest.raises(ValueError, match="Unsupported queue adapter type"):
        ensure_adapter_dependency("unknown")


@pytest.mark.parametrize(
    ("adapter_type", "package_name", "expected_install"),
    [
        ("kafka", "aiokafka", "poetry add aiokafka"),
        ("rabbitmq", "aio_pika", "poetry add aio-pika"),
        ("sqs", "aioboto3", "poetry add aioboto3"),
    ],
)
def test_ensure_adapter_dependency_reports_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
    adapter_type: str,
    package_name: str,
    expected_install: str,
) -> None:
    def _missing_spec(name: str):
        if name == package_name:
            return None
        return object()

    monkeypatch.setattr("owlclaw.integrations.queue_adapters.dependencies.find_spec", _missing_spec)

    with pytest.raises(RuntimeError, match=expected_install):
        ensure_adapter_dependency(adapter_type)


def test_ensure_adapter_dependency_passes_when_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("owlclaw.integrations.queue_adapters.dependencies.find_spec", lambda _: object())
    ensure_adapter_dependency("kafka")
