from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import ParallelExecutor


def _name_worker(path: Path) -> str:
    return path.name


def _maybe_fail_worker(path: Path) -> str:
    if path.stem.startswith("bad_"):
        raise ValueError("intentional failure")
    return path.name


@settings(deadline=None, max_examples=10)
@given(names=st.lists(st.from_regex(r"[a-z][a-z0-9_]{0,6}", fullmatch=True), min_size=1, max_size=6, unique=True))
def test_property_parallel_scan_determinism(names: list[str]) -> None:
    # Property 15: Parallel Scan Determinism
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        files = []
        for name in names:
            path = root / f"{name}.py"
            path.write_text("x = 1\n", encoding="utf-8")
            files.append(path)

        executor = ParallelExecutor(workers=2)
        first = executor.run(files, _name_worker)
        second = executor.run(files, _name_worker)

        assert [item.file_path for item in first] == [str(path) for path in files]
        assert [item.result for item in first] == [item.result for item in second]


@settings(deadline=None, max_examples=10)
@given(
    good_names=st.lists(st.from_regex(r"[a-z][a-z0-9_]{0,6}", fullmatch=True), min_size=1, max_size=5, unique=True),
    bad_name=st.from_regex(r"[a-z][a-z0-9_]{0,6}", fullmatch=True),
)
def test_property_parallel_error_handling(good_names: list[str], bad_name: str) -> None:
    # Property 16: Parallel Error Handling
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        files = []
        bad_path = root / f"bad_{bad_name}.py"
        bad_path.write_text("x = 1\n", encoding="utf-8")
        files.append(bad_path)
        for name in good_names:
            path = root / f"{name}.py"
            path.write_text("x = 1\n", encoding="utf-8")
            files.append(path)

        executor = ParallelExecutor(workers=2)
        results = executor.run(files, _maybe_fail_worker)

        failures = [item for item in results if item.error]
        successes = [item for item in results if not item.error]
        assert len(failures) == 1
        assert "intentional failure" in (failures[0].error or "")
        assert len(successes) == len(files) - 1
