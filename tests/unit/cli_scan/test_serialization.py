from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import JSONSerializer, SchemaValidator, YAMLSerializer
from owlclaw.cli.scan.models import FileScanResult, ScanMetadata, ScanResult


def _build_scan_result(project_path: str, scanned: int, failed: int) -> ScanResult:
    metadata = ScanMetadata(
        project_path=project_path,
        scanned_files=scanned,
        failed_files=failed,
        scan_time_seconds=1.23,
    )
    files = {
        "example.py": FileScanResult(file_path="example.py", functions=[], imports=[], errors=[]),
    }
    return ScanResult(metadata=metadata, files=files)


@settings(deadline=None, max_examples=20)
@given(
    project_path=st.text(min_size=1, max_size=20),
    scanned=st.integers(min_value=0, max_value=20),
    failed=st.integers(min_value=0, max_value=20),
)
def test_property_output_schema_compliance(project_path: str, scanned: int, failed: int) -> None:
    # Property 19: Output Schema Compliance
    result = _build_scan_result(project_path, scanned, failed)
    validator = SchemaValidator()
    ok, errors = validator.validate(result.to_dict())
    assert ok is True
    assert errors == []


def test_json_and_yaml_serializer_round_trip_shape() -> None:
    result = _build_scan_result("proj", 3, 1)
    json_payload = JSONSerializer(pretty=True).serialize(result)
    yaml_payload = YAMLSerializer().serialize(result)
    from_json = ScanResult.from_json(json_payload)
    from_yaml = ScanResult.from_yaml(yaml_payload)
    assert from_json.metadata.project_path == "proj"
    assert from_yaml.metadata.scanned_files == 3
