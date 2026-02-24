from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import (
    ComplexityLevel,
    ComplexityScore,
    Confidence,
    DocstringStyle,
    FileScanResult,
    FunctionScanResult,
    FunctionSignature,
    InferredType,
    Parameter,
    ParameterKind,
    ParsedDocstring,
    ScanMetadata,
    ScanResult,
    TypeSource,
)


def _safe_text(*, min_size: int = 0, max_size: int = 10):
    return st.text(
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
        min_size=min_size,
        max_size=max_size,
    )


def _parameter_strategy():
    return st.builds(
        Parameter,
        name=_safe_text(min_size=1, max_size=8),
        annotation=st.one_of(st.none(), _safe_text(min_size=1, max_size=8)),
        default=st.one_of(st.none(), _safe_text(min_size=1, max_size=8)),
        kind=st.sampled_from(list(ParameterKind)),
    )


def _signature_strategy():
    return st.builds(
        FunctionSignature,
        name=_safe_text(min_size=1, max_size=8),
        module=_safe_text(min_size=1, max_size=8),
        qualname=_safe_text(min_size=1, max_size=12),
        parameters=st.lists(_parameter_strategy(), max_size=2),
        return_type=st.one_of(st.none(), _safe_text(min_size=1, max_size=8)),
        is_async=st.booleans(),
        is_generator=st.booleans(),
        lineno=st.integers(min_value=1, max_value=2000),
    )


def _function_result_strategy():
    return st.builds(
        FunctionScanResult,
        signature=_signature_strategy(),
        docstring=st.builds(
            ParsedDocstring,
            summary=_safe_text(max_size=20),
            description=_safe_text(max_size=40),
            parameters=st.dictionaries(
                keys=_safe_text(min_size=1, max_size=6),
                values=_safe_text(max_size=10),
                max_size=2,
            ),
            returns=st.one_of(st.none(), _safe_text(max_size=10)),
            raises=st.dictionaries(
                keys=_safe_text(min_size=1, max_size=6),
                values=_safe_text(max_size=10),
                max_size=2,
            ),
            examples=st.lists(_safe_text(max_size=10), max_size=1),
            style=st.sampled_from(list(DocstringStyle)),
            raw=_safe_text(max_size=20),
        ),
        complexity=st.builds(
            ComplexityScore,
            cyclomatic=st.integers(min_value=1, max_value=20),
            cognitive=st.integers(min_value=0, max_value=30),
            loc=st.integers(min_value=0, max_value=400),
            sloc=st.integers(min_value=0, max_value=400),
            parameters=st.integers(min_value=0, max_value=20),
            nesting_depth=st.integers(min_value=0, max_value=10),
            level=st.sampled_from(list(ComplexityLevel)),
        ),
        inferred_types=st.dictionaries(
            keys=_safe_text(min_size=1, max_size=6),
            values=st.builds(
                InferredType,
                type_str=_safe_text(min_size=1, max_size=8),
                confidence=st.sampled_from(list(Confidence)),
                source=st.sampled_from(list(TypeSource)),
            ),
            max_size=2,
        ),
        dependencies=st.lists(_safe_text(min_size=1, max_size=10), max_size=2),
    )


def _scan_result_strategy():
    return st.builds(
        ScanResult,
        metadata=st.builds(
            ScanMetadata,
            project_path=_safe_text(min_size=1, max_size=10),
            scanned_files=st.integers(min_value=0, max_value=50),
            failed_files=st.integers(min_value=0, max_value=10),
            scan_time_seconds=st.integers(min_value=0, max_value=60_000).map(lambda v: v / 1000.0),
        ),
        files=st.dictionaries(
            keys=_safe_text(min_size=1, max_size=10),
            values=st.builds(
                FileScanResult,
                file_path=_safe_text(min_size=1, max_size=10),
                functions=st.lists(_function_result_strategy(), max_size=2),
                errors=st.lists(_safe_text(max_size=10), max_size=1),
            ),
            max_size=2,
        ),
    )


@settings(deadline=None, max_examples=20)
@given(result=_scan_result_strategy())
def test_property_json_serialization_round_trip(result: ScanResult) -> None:
    payload = result.to_json()
    loaded = ScanResult.from_json(payload)
    assert loaded.to_dict() == result.to_dict()


@settings(deadline=None, max_examples=20)
@given(result=_scan_result_strategy())
def test_property_yaml_serialization_round_trip(result: ScanResult) -> None:
    payload = result.to_yaml()
    loaded = ScanResult.from_yaml(payload)
    assert loaded.to_dict() == result.to_dict()
