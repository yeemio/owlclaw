from __future__ import annotations

import ast
import keyword
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import ASTParser


def _identifier() -> st.SearchStrategy[str]:
    return st.from_regex(r"[a-z_][a-z0-9_]{0,7}", fullmatch=True).filter(lambda s: not keyword.iskeyword(s))


@settings(deadline=None, max_examples=25)
@given(fn_name=_identifier(), class_name=_identifier(), method_name=_identifier())
def test_property_valid_python_parsing(fn_name: str, class_name: str, method_name: str) -> None:
    parser = ASTParser()
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "sample.py"
        path.write_text(
            f"def {fn_name}():\n    return 1\n\nclass {class_name}:\n    def {method_name}(self):\n        return 2\n",
            encoding="utf-8",
        )
        tree = parser.parse_file(path)
        assert isinstance(tree, ast.Module)
        assert parser.extract_functions(tree)
        classes = parser.extract_classes(tree)
        assert classes
        assert parser.extract_methods(classes[0])


@settings(deadline=None, max_examples=25)
@given(bad_tail=st.text(min_size=1, max_size=20))
def test_property_syntax_error_resilience(bad_tail: str) -> None:
    parser = ASTParser()
    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "broken.py"
        path.write_text(f"def broken(:\n    pass\n{bad_tail}", encoding="utf-8")
        tree = parser.parse_file(path)
        assert tree is None
        assert parser.errors
        assert parser.errors[0]["error_type"] == "syntax_error"
