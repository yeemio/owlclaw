from __future__ import annotations

import ast

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import Confidence, TypeInferencer


@settings(deadline=None, max_examples=25)
@given(default_value=st.one_of(st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.booleans(), st.text(max_size=20)))
def test_property_type_inference_from_defaults(default_value: int | float | bool | str) -> None:
    # Property 8: Type Inference from Defaults
    literal = repr(default_value)
    fn = ast.parse(f"def f(x={literal}):\n    return x\n").body[0]
    assert isinstance(fn, ast.FunctionDef)

    inferencer = TypeInferencer()
    inferred = inferencer.infer_parameter_type(fn.args.args[0], fn.args.defaults[0])
    assert inferred.type_str == type(default_value).__name__
    assert inferred.source.value == "default_value"


@settings(deadline=None, max_examples=25)
@given(expr=st.sampled_from(["some_factory()", "a + b", "lambda x: x", "{k: v for k, v in []}"]))
def test_property_type_inference_fallback(expr: str) -> None:
    # Property 9: Type Inference Fallback
    fn = ast.parse(f"def f(x={expr}):\n    return x\n").body[0]
    assert isinstance(fn, ast.FunctionDef)

    inferencer = TypeInferencer()
    inferred = inferencer.infer_parameter_type(fn.args.args[0], fn.args.defaults[0])
    assert inferred.type_str == "unknown"
    assert inferred.confidence in {Confidence.MEDIUM, Confidence.LOW}


def test_return_type_inference_for_optional_paths() -> None:
    fn = ast.parse("def f(flag):\n    if flag:\n        return 1\n    return None\n").body[0]
    assert isinstance(fn, ast.FunctionDef)

    inferencer = TypeInferencer()
    inferred = inferencer.infer_return_type(fn)
    assert inferred.type_str == "Optional[int]"
