from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import ConfigManager, ScanConfig


@settings(deadline=None, max_examples=20)
@given(
    incremental=st.booleans(),
    workers=st.integers(min_value=1, max_value=8),
    threshold=st.integers(min_value=0, max_value=20),
)
def test_property_configuration_round_trip(incremental: bool, workers: int, threshold: int) -> None:
    # Property 23: Configuration Round-Trip
    manager = ConfigManager()
    config = ScanConfig(
        project_path=Path("."),
        include_patterns=["*.py", "tests/*.py"],
        exclude_patterns=["*/.venv/*"],
        incremental=incremental,
        workers=workers,
        min_complexity_threshold=threshold,
    )
    payload = manager.dump_yaml(config)
    loaded = manager.load_yaml(Path("."), payload)
    assert manager.to_dict(loaded) == manager.to_dict(config)


@settings(deadline=None, max_examples=20)
@given(workers=st.one_of(st.integers(max_value=0), st.text(max_size=4)))
def test_property_configuration_validation(workers: int | str) -> None:
    # Property 24: Configuration Validation
    manager = ConfigManager()
    payload = {"workers": workers}
    if isinstance(workers, int) and workers >= 1:
        validated = manager.validate(payload)
        assert validated["workers"] == workers
    else:
        with pytest.raises(ValueError):
            manager.validate(payload)


def test_config_manager_unit_loading_and_defaults() -> None:
    manager = ConfigManager()
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config_file = root / ".owlclaw-scan.yaml"
        config_file.write_text("workers: 3\nextract_docstrings: false\n", encoding="utf-8")
        loaded = manager.load(root, config_file=config_file)
        assert loaded.workers == 3
        assert loaded.extract_docstrings is False
        assert loaded.include_patterns == ["*.py"]

        defaults = manager.load(root, config_file=root / "missing.yaml")
        assert defaults.workers == 1
        assert defaults.incremental is False


def test_config_manager_unit_invalid_values_and_globs() -> None:
    manager = ConfigManager()
    with pytest.raises(ValueError):
        manager.validate({"include_patterns": "*.py"})
    with pytest.raises(ValueError):
        manager.validate({"min_complexity_threshold": -1})
    with pytest.raises(ValueError):
        manager.validate({"include_patterns": ["[abc"]})
