from __future__ import annotations

import ast

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import ComplexityCalculator, ComplexityLevel


@settings(deadline=None, max_examples=25)
@given(condition_count=st.integers(min_value=0, max_value=5), loop_count=st.integers(min_value=0, max_value=4))
def test_property_complexity_metrics_completeness(condition_count: int, loop_count: int) -> None:
    # Property 13: Complexity Metrics Completeness
    lines = ["def f(x):"]
    for index in range(condition_count):
        lines.append(f"    if x > {index}:")
        lines.append("        x += 1")
    for _ in range(loop_count):
        lines.append("    for i in range(2):")
        lines.append("        x += i")
    lines.append("    return x")
    source = "\n".join(lines) + "\n"
    fn = ast.parse(source).body[0]
    assert isinstance(fn, ast.FunctionDef)

    calculator = ComplexityCalculator()
    score = calculator.calculate(fn, source)

    assert score.cyclomatic >= 1
    assert score.cognitive >= 0
    assert score.loc >= 1
    assert score.sloc >= 1
    assert score.parameters == 1
    assert score.nesting_depth >= 0
    assert score.level in {ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX}


def test_complexity_simple_linear_function() -> None:
    source = "def linear(x):\n    y = x + 1\n    return y\n"
    fn = ast.parse(source).body[0]
    assert isinstance(fn, ast.FunctionDef)
    calculator = ComplexityCalculator()
    score = calculator.calculate(fn, source)
    assert score.cyclomatic == 1
    assert score.level is ComplexityLevel.SIMPLE


def test_complexity_nested_if_and_loops() -> None:
    source = (
        "def nested(v):\n"
        "    total = 0\n"
        "    for i in range(v):\n"
        "        if i % 2 == 0:\n"
        "            if i > 10:\n"
        "                total += i\n"
        "    return total\n"
    )
    fn = ast.parse(source).body[0]
    assert isinstance(fn, ast.FunctionDef)
    calculator = ComplexityCalculator()
    score = calculator.calculate(fn, source)
    assert score.cyclomatic >= 4
    assert score.nesting_depth >= 3


def test_complexity_level_assignment() -> None:
    source = (
        "def branchy(x):\n"
        "    if x > 0:\n"
        "        x += 1\n"
        "    if x > 1:\n"
        "        x += 1\n"
        "    if x > 2:\n"
        "        x += 1\n"
        "    if x > 3:\n"
        "        x += 1\n"
        "    if x > 4:\n"
        "        x += 1\n"
        "    if x > 5:\n"
        "        x += 1\n"
        "    return x\n"
    )
    fn = ast.parse(source).body[0]
    assert isinstance(fn, ast.FunctionDef)
    calculator = ComplexityCalculator()
    score = calculator.calculate(fn, source)
    assert score.cyclomatic > 5
    assert score.level in {ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX}
