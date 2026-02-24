from __future__ import annotations

import ast
import keyword

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import ParameterKind, SignatureExtractor


def _identifier() -> st.SearchStrategy[str]:
    return st.from_regex(r"[a-z_][a-z0-9_]{0,7}", fullmatch=True).filter(lambda s: not keyword.iskeyword(s))


@settings(deadline=None, max_examples=25)
@given(fn_name=_identifier(), arg_one=_identifier(), arg_two=_identifier())
def test_property_complete_signature_extraction(fn_name: str, arg_one: str, arg_two: str) -> None:
    # Property 4: Complete Signature Extraction
    source = (
        "@cached(ttl=30)\n"
        f"def {fn_name}({arg_one}: int, {arg_two}: str = 'x', *, flag: bool = False, **kwargs) -> list[str]:\n"
        "    return []\n"
    )
    function_node = ast.parse(source).body[0]
    assert isinstance(function_node, ast.FunctionDef)

    extractor = SignatureExtractor()
    signature = extractor.extract_signature(function_node, module="pkg.mod")

    assert signature.name == fn_name
    assert signature.module == "pkg.mod"
    assert signature.qualname == fn_name
    assert signature.return_type == "list[str]"
    assert len(signature.parameters) == 4
    assert signature.parameters[0].kind is ParameterKind.POSITIONAL
    assert signature.parameters[1].default == "'x'"
    assert signature.parameters[2].kind is ParameterKind.KEYWORD
    assert signature.parameters[3].kind is ParameterKind.VAR_KEYWORD
    assert signature.decorators and signature.decorators[0].name == "cached"
    assert signature.decorators[0].arguments == ["ttl=30"]


@settings(deadline=None, max_examples=25)
@given(fn_name=_identifier(), arg_name=_identifier())
def test_property_signature_round_trip_consistency(fn_name: str, arg_name: str) -> None:
    # Property 5: Signature Round-Trip Consistency
    source = f"def {fn_name}({arg_name}: int = 1) -> int:\n    return {arg_name}\n"
    first_tree = ast.parse(source)
    second_tree = ast.parse(source)
    first_func = first_tree.body[0]
    second_func = second_tree.body[0]
    assert isinstance(first_func, ast.FunctionDef)
    assert isinstance(second_func, ast.FunctionDef)

    extractor = SignatureExtractor()
    first_signature = extractor.extract_signature(first_func, module="pkg.mod")
    second_signature = extractor.extract_signature(second_func, module="pkg.mod")

    assert first_signature == second_signature


def test_signature_extractor_handles_edge_cases() -> None:
    source = (
        "from typing import Optional, Union\n\n"
        "def no_params():\n"
        "    return 1\n\n"
        "def with_var_args(*args: int, **kwargs: str):\n"
        "    return len(args)\n\n"
        "def typed(value: Optional[Union[int, str]]) -> Optional[list[int]]:\n"
        "    return [1] if value else None\n\n"
        "async def async_fn(v: int) -> int:\n"
        "    return v\n\n"
        "def gen_fn(limit: int):\n"
        "    for i in range(limit):\n"
        "        yield i\n"
    )
    module = ast.parse(source)
    extractor = SignatureExtractor()

    no_params = module.body[1]
    with_var_args = module.body[2]
    typed = module.body[3]
    async_fn = module.body[4]
    gen_fn = module.body[5]
    assert isinstance(no_params, ast.FunctionDef)
    assert isinstance(with_var_args, ast.FunctionDef)
    assert isinstance(typed, ast.FunctionDef)
    assert isinstance(async_fn, ast.AsyncFunctionDef)
    assert isinstance(gen_fn, ast.FunctionDef)

    no_params_sig = extractor.extract_signature(no_params, module="pkg.mod")
    assert no_params_sig.parameters == []

    var_sig = extractor.extract_signature(with_var_args, module="pkg.mod")
    assert [p.kind for p in var_sig.parameters] == [ParameterKind.VAR_POSITIONAL, ParameterKind.VAR_KEYWORD]

    typed_sig = extractor.extract_signature(typed, module="pkg.mod")
    assert typed_sig.parameters[0].annotation == "Optional[Union[int, str]]"
    assert typed_sig.return_type == "Optional[list[int]]"

    async_sig = extractor.extract_signature(async_fn, module="pkg.mod")
    assert async_sig.is_async is True
    assert async_sig.is_generator is False

    gen_sig = extractor.extract_signature(gen_fn, module="pkg.mod")
    assert gen_sig.is_generator is True
