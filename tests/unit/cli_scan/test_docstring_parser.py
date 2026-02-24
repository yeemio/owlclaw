from __future__ import annotations

import keyword

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import DocstringParser, DocstringStyle


def _identifier() -> st.SearchStrategy[str]:
    return st.from_regex(r"[a-z_][a-z0-9_]{0,7}", fullmatch=True).filter(lambda s: not keyword.iskeyword(s))


@settings(deadline=None, max_examples=25)
@given(raw=st.text(min_size=0, max_size=120))
def test_property_docstring_preservation(raw: str) -> None:
    # Property 6: Docstring Extraction Preservation
    parser = DocstringParser()
    parsed = parser.parse(raw)
    assert parsed.raw == raw


@settings(deadline=None, max_examples=25)
@given(
    param_name=_identifier(),
    exc_name=st.sampled_from(["ValueError", "RuntimeError"]),
    returns_text=st.from_regex(r"[A-Za-z0-9 _-]{1,30}", fullmatch=True).filter(lambda s: bool(s.strip())),
)
def test_property_structured_docstring_parsing(param_name: str, exc_name: str, returns_text: str) -> None:
    # Property 7: Structured Docstring Parsing
    parser = DocstringParser()
    docstring = (
        "Summary line.\n\n"
        "Args:\n"
        f"    {param_name} (int): input value\n\n"
        "Returns:\n"
        f"    {returns_text}\n\n"
        "Raises:\n"
        f"    {exc_name}: failure\n"
    )
    parsed = parser.parse(docstring)

    assert parsed.style is DocstringStyle.GOOGLE
    assert parsed.parameters.get(param_name) == "input value"
    assert parsed.returns == returns_text.strip()
    assert parsed.raises.get(exc_name) == "failure"


def test_docstring_parser_google_style() -> None:
    parser = DocstringParser()
    docstring = (
        "Do work.\n\n"
        "Args:\n"
        "    value (int): value to process\n"
        "    name (str): display name\n\n"
        "Returns:\n"
        "    bool: success flag\n\n"
        "Raises:\n"
        "    ValueError: invalid value\n"
    )
    parsed = parser.parse(docstring)
    assert parsed.style is DocstringStyle.GOOGLE
    assert parsed.summary == "Do work."
    assert parsed.parameters == {"value": "value to process", "name": "display name"}
    assert parsed.returns == "bool: success flag"
    assert parsed.raises == {"ValueError": "invalid value"}


def test_docstring_parser_numpy_style_with_examples() -> None:
    parser = DocstringParser()
    docstring = (
        "Compute value.\n\n"
        "Parameters\n"
        "----------\n"
        "x : int\n"
        "    First value.\n\n"
        "Returns\n"
        "-------\n"
        "int\n"
        "    Computed result.\n\n"
        "Examples\n"
        "--------\n"
        ">>> compute(1)\n"
        "2\n"
    )
    parsed = parser.parse(docstring)
    assert parsed.style is DocstringStyle.NUMPY
    assert parsed.parameters["x"] == "First value."
    assert parsed.returns == "int Computed result."
    assert parsed.examples == [">>> compute(1)"]


def test_docstring_parser_restructuredtext_and_missing_docstring() -> None:
    parser = DocstringParser()
    docstring = (
        "Execute action.\n\n"
        ":param item: item id\n"
        ":returns: True on success\n"
        ":raises RuntimeError: remote failure\n"
    )
    parsed = parser.parse(docstring)
    assert parsed.style is DocstringStyle.RESTRUCTUREDTEXT
    assert parsed.parameters == {"item": "item id"}
    assert parsed.returns == "True on success"
    assert parsed.raises == {"RuntimeError": "remote failure"}

    empty = parser.parse(None)
    assert empty.style is DocstringStyle.UNKNOWN
    assert empty.raw == ""
