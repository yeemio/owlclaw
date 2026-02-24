from __future__ import annotations

import time
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import IncrementalScanner
from owlclaw.cli.scan.models import FileScanResult


def _file_result(path: Path) -> FileScanResult:
    return FileScanResult(file_path=str(path), functions=[], imports=[], errors=[])


@settings(deadline=None, max_examples=15)
@given(modify_first=st.booleans(), modify_second=st.booleans())
def test_property_incremental_scan_correctness(modify_first: bool, modify_second: bool) -> None:
    # Property 14: Incremental Scan Correctness
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        a_file = root / "a.py"
        b_file = root / "b.py"
        a_file.write_text("value = 1\n", encoding="utf-8")
        b_file.write_text("value = 2\n", encoding="utf-8")

        scanner = IncrementalScanner(root)
        scanner.save_cache({"a.py": _file_result(a_file), "b.py": _file_result(b_file)})

        time.sleep(1.1)
        if modify_first:
            a_file.write_text("value = 10\n", encoding="utf-8")
        if modify_second:
            b_file.write_text("value = 20\n", encoding="utf-8")

        changed = {path.name for path in scanner.get_changed_files([a_file, b_file])}
        assert ("a.py" in changed) == modify_first
        assert ("b.py" in changed) == modify_second


def test_incremental_scan_modify_delete_add_workflow() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        a_file = root / "a.py"
        b_file = root / "b.py"
        a_file.write_text("value = 1\n", encoding="utf-8")
        b_file.write_text("value = 2\n", encoding="utf-8")

        scanner = IncrementalScanner(root)
        cached = {"a.py": _file_result(a_file), "b.py": _file_result(b_file)}
        scanner.save_cache(cached)

        time.sleep(1.1)
        a_file.write_text("value = 3\n", encoding="utf-8")
        changed = scanner.get_changed_files([a_file, b_file])
        assert [item.name for item in changed] == ["a.py"]

        b_file.unlink()
        c_file = root / "c.py"
        c_file.write_text("value = 4\n", encoding="utf-8")
        incremental_results = {"a.py": _file_result(a_file), "c.py": _file_result(c_file)}
        merged = scanner.merge_results(cached, incremental_results, [a_file, c_file])
        assert "a.py" in merged
        assert "b.py" not in merged
        assert "c.py" in merged
