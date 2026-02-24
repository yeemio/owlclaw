from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import typer

from owlclaw.cli.scan_cli import run_scan_command, validate_scan_config_command


def test_scan_cli_writes_output_file() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
        output = root / "scan.json"

        run_scan_command(path=str(root), format_name="json", output=str(output), incremental=False, workers=1, verbose=False)

        payload = json.loads(output.read_text(encoding="utf-8"))
        assert "metadata" in payload
        assert "files" in payload


def test_scan_cli_config_validate() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        config = root / ".owlclaw-scan.yaml"
        config.write_text("workers: 2\n", encoding="utf-8")
        validate_scan_config_command(path=str(root), config=str(config))

        with pytest.raises(typer.Exit) as exc_info:
            validate_scan_config_command(path=str(root), config=str(root / "missing.yaml"))
        assert exc_info.value.exit_code == 2
