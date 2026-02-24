from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import owlclaw.cli as owl_cli
from owlclaw.cli.scan import ConfigManager, ProjectScanner, ScanConfig


def test_integration_full_project_scan() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "a.py").write_text("def a(x: int) -> int:\n    return x + 1\n", encoding="utf-8")
        (root / "b.py").write_text("def b(y):\n    if y:\n        return 1\n    return 0\n", encoding="utf-8")

        scanner = ProjectScanner(ScanConfig(project_path=root))
        result = scanner.scan()
        assert result.metadata.scanned_files == 2
        assert "a.py" in result.files
        assert "b.py" in result.files


def test_integration_incremental_scan_workflow() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = root / "mod.py"
        target.write_text("def f():\n    return 1\n", encoding="utf-8")

        output = root / "out.json"
        assert owl_cli._dispatch_scan_command(["scan", "--path", str(root), "--output", str(output), "--incremental"])
        first = json.loads(output.read_text(encoding="utf-8"))
        assert first["metadata"]["scanned_files"] == 1

        target.write_text("def f():\n    return 2\n", encoding="utf-8")
        assert owl_cli._dispatch_scan_command(["scan", "--path", str(root), "--output", str(output), "--incremental"])
        second = json.loads(output.read_text(encoding="utf-8"))
        assert second["metadata"]["scanned_files"] == 1


def test_integration_cli_invocation_modes() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "x.py").write_text("def x():\n    return 1\n", encoding="utf-8")
        out_json = root / "scan.json"
        out_yaml = root / "scan.yaml"

        assert owl_cli._dispatch_scan_command(["scan", "--path", str(root), "--format", "json", "--output", str(out_json)])
        assert out_json.exists()
        assert owl_cli._dispatch_scan_command(["scan", "--path", str(root), "--format", "yaml", "--output", str(out_yaml)])
        assert out_yaml.exists()


def test_integration_error_scenarios() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "bad.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
        out_file = root / "scan.json"
        assert owl_cli._dispatch_scan_command(["scan", "--path", str(root), "--output", str(out_file)])
        payload = json.loads(out_file.read_text(encoding="utf-8"))
        assert payload["metadata"]["failed_files"] == 1

        manager = ConfigManager()
        with pytest.raises(ValueError):
            manager.validate({"workers": 0})
