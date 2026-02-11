"""Unit tests for Hatchet integration (config and client, no server)."""

import pytest

from owlclaw.integrations.hatchet import HatchetConfig, HatchetClient, _substitute_env_dict


def test_hatchet_config_defaults():
    """HatchetConfig has expected defaults (single-instance multi-DB: hatchet database)."""
    config = HatchetConfig()
    assert config.server_url == "http://localhost:7077"
    assert config.namespace == "owlclaw"
    assert config.mode == "production"
    assert config.max_concurrent_tasks == 10
    assert config.postgres_db == "hatchet"
    assert config.postgres_user == "hatchet"


def test_hatchet_config_mode_validation():
    """HatchetConfig rejects invalid mode."""
    with pytest.raises(ValueError, match="mode must be"):
        HatchetConfig(mode="invalid")


def test_hatchet_config_server_url_validation():
    """HatchetConfig rejects invalid server_url."""
    with pytest.raises(ValueError, match="server_url"):
        HatchetConfig(server_url="not-a-url")


def test_hatchet_config_postgres_port_validation():
    """HatchetConfig rejects postgres_port out of range."""
    with pytest.raises(ValueError, match="postgres_port"):
        HatchetConfig(postgres_port=0)
    with pytest.raises(ValueError, match="postgres_port"):
        HatchetConfig(postgres_port=70000)


def test_hatchet_config_from_yaml(tmp_path):
    """HatchetConfig.from_yaml loads hatchet section."""
    config_file = tmp_path / "owlclaw.yaml"
    config_file.write_text("""
app:
  name: test
hatchet:
  server_url: http://hatchet:7077
  namespace: myns
  mode: lite
  max_concurrent_tasks: 5
""", encoding="utf-8")
    config = HatchetConfig.from_yaml(config_file)
    assert config.server_url == "http://hatchet:7077"
    assert config.namespace == "myns"
    assert config.mode == "lite"
    assert config.max_concurrent_tasks == 5


def test_hatchet_config_from_yaml_env_substitution(tmp_path, monkeypatch):
    """HatchetConfig.from_yaml substitutes ${VAR} from environment."""
    monkeypatch.setenv("HATCHET_NS", "from-env")
    config_file = tmp_path / "owlclaw.yaml"
    config_file.write_text("""
hatchet:
  server_url: http://localhost:7077
  namespace: ${HATCHET_NS}
  mode: production
""", encoding="utf-8")
    config = HatchetConfig.from_yaml(config_file)
    assert config.namespace == "from-env"


def test_substitute_env_dict(monkeypatch):
    """_substitute_env_dict replaces ${VAR} in nested dicts."""
    monkeypatch.setenv("SUBST_FOO", "bar")
    out = _substitute_env_dict({"a": "${SUBST_FOO}", "b": {"c": "no-var"}})
    assert out["a"] == "bar"
    assert out["b"]["c"] == "no-var"


def test_hatchet_client_connect_without_token_raises():
    """HatchetClient.connect() raises when no api_token or env."""
    config = HatchetConfig()
    client = HatchetClient(config)
    with pytest.raises(ValueError, match="API token required"):
        client.connect()


def test_hatchet_client_task_before_connect_raises():
    """Using task() decorator before connect() raises RuntimeError."""
    config = HatchetConfig(api_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJ0ZXN0In0.x")
    client = HatchetClient(config)

    with pytest.raises(RuntimeError, match="connect"):
        @client.task(name="test-task")
        async def my_task(ctx):
            pass


def test_hatchet_client_durable_task_before_connect_raises():
    """Using durable_task() decorator before connect() raises RuntimeError."""
    config = HatchetConfig(api_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJ0ZXN0In0.x")
    client = HatchetClient(config)

    with pytest.raises(RuntimeError, match="connect"):
        @client.durable_task(name="durable-test")
        async def my_durable(ctx):
            pass


@pytest.mark.asyncio
async def test_hatchet_client_run_task_now_unregistered_raises():
    """run_task_now() for unregistered task raises ValueError."""
    client = HatchetClient(HatchetConfig())
    with pytest.raises(ValueError, match="not registered"):
        await client.run_task_now("nonexistent")


@pytest.mark.asyncio
async def test_hatchet_client_schedule_task_unregistered_raises():
    """schedule_task() for unregistered task raises ValueError."""
    client = HatchetClient(HatchetConfig())
    with pytest.raises(ValueError, match="not registered"):
        await client.schedule_task("nonexistent", delay_seconds=10)


@pytest.mark.asyncio
async def test_hatchet_client_schedule_task_invalid_delay_raises():
    """schedule_task() with delay_seconds <= 0 raises ValueError."""
    client = HatchetClient(HatchetConfig())
    client._workflows["dummy"] = None
    with pytest.raises(ValueError, match="delay_seconds must be positive"):
        await client.schedule_task("dummy", delay_seconds=0)


@pytest.mark.asyncio
async def test_hatchet_client_get_task_status_not_connected_raises():
    """get_task_status() when not connected raises RuntimeError."""
    client = HatchetClient(HatchetConfig())
    with pytest.raises(RuntimeError, match="Not connected"):
        await client.get_task_status("some-id")


@pytest.mark.asyncio
async def test_hatchet_client_list_scheduled_tasks_when_disconnected_returns_empty():
    """list_scheduled_tasks() when disconnected returns empty list."""
    client = HatchetClient(HatchetConfig())
    result = await client.list_scheduled_tasks()
    assert result == []


@pytest.mark.asyncio
async def test_hatchet_client_cancel_task_when_disconnected_returns_false():
    """cancel_task() when disconnected returns False."""
    client = HatchetClient(HatchetConfig())
    result = await client.cancel_task("some-id")
    assert result is False


def test_hatchet_cron_validation():
    """Invalid cron expression raises ValueError (via _validate_cron)."""
    from owlclaw.integrations.hatchet import _validate_cron
    with pytest.raises(ValueError, match="cron"):
        _validate_cron("")
    with pytest.raises(ValueError, match="cron"):
        _validate_cron("1 2 3")  # too few parts
    with pytest.raises(ValueError, match="cron"):
        _validate_cron("invalid")
    _validate_cron("0 9 * * 1-5")
    _validate_cron("0 */5 * * * *")
