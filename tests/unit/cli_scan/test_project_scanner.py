from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import ProjectScanner, ScanConfig


@settings(deadline=None, max_examples=20)
@given(threshold=st.integers(min_value=1, max_value=6))
def test_property_complexity_threshold_filtering(threshold: int) -> None:
    # Property 21: Complexity Threshold Filtering
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        file_path = root / "mod.py"
        file_path.write_text(
            "def simple(x):\n"
            "    return x\n\n"
            "def branchy(x):\n"
            "    if x > 0:\n"
            "        x += 1\n"
            "    if x > 1:\n"
            "        x += 1\n"
            "    if x > 2:\n"
            "        x += 1\n"
            "    return x\n",
            encoding="utf-8",
        )
        scanner = ProjectScanner(
            ScanConfig(
                project_path=root,
                min_complexity_threshold=threshold,
                extract_docstrings=False,
                analyze_dependencies=False,
            )
        )
        result = scanner.scan()
        functions = result.files["mod.py"].functions
        assert all(item.complexity.cyclomatic >= threshold for item in functions)


@settings(deadline=None, max_examples=20)
@given(extract_docstrings=st.booleans(), calculate_complexity=st.booleans(), analyze_dependencies=st.booleans())
def test_property_feature_toggle_respect(
    extract_docstrings: bool,
    calculate_complexity: bool,
    analyze_dependencies: bool,
) -> None:
    # Property 22: Feature Toggle Respect
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        file_path = root / "mod.py"
        file_path.write_text(
            "import json\n\n"
            "def fn(x):\n"
            "    \"\"\"demo doc\"\"\"\n"
            "    return json.dumps(x)\n",
            encoding="utf-8",
        )
        scanner = ProjectScanner(
            ScanConfig(
                project_path=root,
                extract_docstrings=extract_docstrings,
                calculate_complexity=calculate_complexity,
                analyze_dependencies=analyze_dependencies,
            )
        )
        result = scanner.scan()
        file_result = result.files["mod.py"]
        fn = file_result.functions[0]

        if extract_docstrings:
            assert fn.docstring.raw == "demo doc"
        else:
            assert fn.docstring.raw == ""

        if analyze_dependencies:
            assert file_result.imports
            assert fn.dependencies
        else:
            assert file_result.imports == []
            assert fn.dependencies == []

        if calculate_complexity:
            assert fn.complexity.loc >= 1
        else:
            assert fn.complexity.loc == 0


@settings(deadline=None, max_examples=20)
@given(trailing=st.text(min_size=0, max_size=20))
def test_property_error_logging_completeness(trailing: str) -> None:
    # Property 25: Error Logging Completeness
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
        (root / "broken.py").write_text(f"def bad(:\n    pass\n{trailing}", encoding="utf-8")

        scanner = ProjectScanner(ScanConfig(project_path=root))
        result = scanner.scan()

        assert result.metadata.scanned_files == 2
        assert result.metadata.failed_files == 1
        assert result.files["broken.py"].errors
        assert "line=" in result.files["broken.py"].errors[0]


@settings(deadline=None, max_examples=20)
@given(file_count=st.integers(min_value=1, max_value=5), broken_index=st.integers(min_value=0, max_value=4))
def test_property_scan_statistics_accuracy(file_count: int, broken_index: int) -> None:
    # Property 26: Scan Statistics Accuracy
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        broken_slot = broken_index % file_count
        for i in range(file_count):
            target = root / f"f{i}.py"
            if i == broken_slot:
                target.write_text("def bad(:\n    pass\n", encoding="utf-8")
            else:
                target.write_text("def ok():\n    return 1\n", encoding="utf-8")

        scanner = ProjectScanner(ScanConfig(project_path=root))
        result = scanner.scan()

        assert result.metadata.scanned_files == file_count
        assert result.metadata.failed_files == 1
        observed_failed = sum(1 for item in result.files.values() if item.errors)
        assert observed_failed == result.metadata.failed_files
