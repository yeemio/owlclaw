from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import FileDiscovery


@settings(deadline=None, max_examples=20)
@given(name=st.from_regex(r"[a-z][a-z0-9_]{0,8}", fullmatch=True), excluded_dir=st.sampled_from(["venv", ".venv", "env"]))
def test_property_file_discovery_with_exclusions(name: str, excluded_dir: str) -> None:
    # Property 1: File Discovery with Exclusions
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "src").mkdir()
        (root / excluded_dir).mkdir()
        included_file = root / "src" / f"{name}.py"
        excluded_file = root / excluded_dir / f"{name}.py"
        included_file.write_text("x = 1\n", encoding="utf-8")
        excluded_file.write_text("x = 2\n", encoding="utf-8")

        discovery = FileDiscovery()
        result = discovery.discover(root)

        assert included_file in result
        assert excluded_file not in result


@settings(deadline=None, max_examples=20)
@given(
    base=st.from_regex(r"[a-z][a-z0-9_]{0,8}", fullmatch=True),
    include_py=st.booleans(),
    include_txt=st.booleans(),
)
def test_property_configuration_pattern_filtering(base: str, include_py: bool, include_txt: bool) -> None:
    # Property 20: Configuration Pattern Filtering
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        py_file = root / f"{base}.py"
        txt_file = root / f"{base}.txt"
        py_file.write_text("print('ok')\n", encoding="utf-8")
        txt_file.write_text("not python\n", encoding="utf-8")

        include_patterns: list[str] = []
        if include_py:
            include_patterns.append("*.py")
        if include_txt:
            include_patterns.append("*.txt")
        if not include_patterns:
            include_patterns = ["*.py"]

        discovery = FileDiscovery(include_patterns=include_patterns, exclude_patterns=[])
        result = discovery.discover(root)

        assert (py_file in result) == ("*.py" in include_patterns)
        assert (txt_file in result) == ("*.txt" in include_patterns)
