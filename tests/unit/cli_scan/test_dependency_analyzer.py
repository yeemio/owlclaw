from __future__ import annotations

import ast

from hypothesis import given, settings
from hypothesis import strategies as st

from owlclaw.cli.scan import CyclicDependencyDetector, Dependency, DependencyAnalyzer, ImportType


@settings(deadline=None, max_examples=25)
@given(name=st.from_regex(r"[a-z][a-z0-9_]{0,6}", fullmatch=True))
def test_property_function_call_detection(name: str) -> None:
    # Property 10: Function Call Detection
    source = f"def {name}():\n    return helper()\n\ndef helper():\n    return 1\n"
    module = ast.parse(source)
    fn = module.body[0]
    assert isinstance(fn, ast.FunctionDef)
    analyzer = DependencyAnalyzer()
    calls = analyzer.extract_calls(fn)
    assert "helper" in calls


@settings(deadline=None, max_examples=25)
@given(module_name=st.sampled_from(["json", "pathlib", "nonexistent_pkg_abc"]))
def test_property_import_classification(module_name: str) -> None:
    # Property 11: Import Classification
    analyzer = DependencyAnalyzer()
    classified = analyzer.classify_import(module_name)
    if module_name in {"json", "pathlib"}:
        assert classified is ImportType.STDLIB
    else:
        assert classified in {ImportType.THIRD_PARTY, ImportType.UNKNOWN}


@settings(deadline=None, max_examples=25)
@given(a=st.sampled_from(["a", "node_a"]), b=st.sampled_from(["b", "node_b"]))
def test_property_cycle_detection(a: str, b: str) -> None:
    # Property 12: Cycle Detection
    detector = CyclicDependencyDetector()
    nodes = [a, b]
    edges = [
        Dependency(source=a, target=b, import_type=ImportType.LOCAL),
        Dependency(source=b, target=a, import_type=ImportType.LOCAL),
    ]
    cycles = detector.detect(nodes, edges)
    assert cycles
    assert set(cycles[0]) == {a, b}


def test_dependency_analysis_unit_scenarios() -> None:
    source = (
        "from math import sqrt\n\n"
        "def alpha(x):\n"
        "    return beta(x)\n\n"
        "def beta(y):\n"
        "    return sqrt(y)\n\n"
        "class Worker:\n"
        "    def run(self, item):\n"
        "        return self.step(item)\n\n"
        "    def step(self, value):\n"
        "        return value\n"
    )
    tree = ast.parse(source)
    analyzer = DependencyAnalyzer()
    graph = analyzer.analyze(tree, module="pkg.mod")

    assert "pkg.mod.alpha" in graph.nodes
    assert "pkg.mod.beta" in graph.nodes
    assert any(edge.source == "pkg.mod.alpha" and edge.target == "pkg.mod.beta" for edge in graph.edges)
    assert any(imp.module == "math" and imp.import_type is ImportType.STDLIB for imp in graph.imports)

    worker_run = tree.body[3].body[0]
    assert isinstance(worker_run, ast.FunctionDef)
    calls = analyzer.extract_calls(worker_run)
    assert "self.step" in calls

    detector = CyclicDependencyDetector()
    cycles = detector.detect(
        ["pkg.a", "pkg.b"],
        [
            Dependency("pkg.a", "pkg.b", ImportType.LOCAL),
            Dependency("pkg.b", "pkg.a", ImportType.LOCAL),
        ],
    )
    assert cycles
