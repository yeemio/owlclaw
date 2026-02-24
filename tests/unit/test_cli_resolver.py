"""Unit tests for dependency resolver."""

from __future__ import annotations

from owlclaw.cli.resolver import DependencyResolver
from owlclaw.owlhub import SearchResult


def _result(name: str, version: str, deps: dict[str, str] | None = None) -> SearchResult:
    return SearchResult(
        name=name,
        publisher="acme",
        version=version,
        description=f"{name} description",
        tags=["demo"],
        version_state="released",
        download_url="",
        checksum="",
        dependencies=deps or {},
    )


def test_dependency_chain_resolution_order() -> None:
    catalog = {
        "root": [_result("root", "1.0.0", {"dep-a": "^1.0.0"})],
        "dep-a": [_result("dep-a", "1.2.0", {"dep-b": ">=1.0.0,<2.0.0"})],
        "dep-b": [_result("dep-b", "1.0.1")],
    }
    resolver = DependencyResolver(get_candidates=lambda name: catalog.get(name, []))
    plan = resolver.resolve(root=catalog["root"][0])
    assert [node.name for node in plan] == ["dep-b", "dep-a", "root"]


def test_circular_dependency_detection() -> None:
    catalog = {
        "root": [_result("root", "1.0.0", {"dep-a": "^1.0.0"})],
        "dep-a": [_result("dep-a", "1.0.0", {"root": "^1.0.0"})],
    }
    resolver = DependencyResolver(get_candidates=lambda name: catalog.get(name, []))
    try:
        resolver.resolve(root=catalog["root"][0])
        raise AssertionError("expected circular dependency error")
    except ValueError as exc:
        assert "circular" in str(exc)


def test_version_constraint_selection() -> None:
    catalog = {
        "root": [_result("root", "1.0.0", {"dep-a": "~1.2.0"})],
        "dep-a": [_result("dep-a", "1.1.9"), _result("dep-a", "1.2.1"), _result("dep-a", "1.3.0")],
    }
    resolver = DependencyResolver(get_candidates=lambda name: catalog.get(name, []))
    plan = resolver.resolve(root=catalog["root"][0])
    dep = next(node for node in plan if node.name == "dep-a")
    assert dep.version == "1.2.1"


def test_missing_dependency_error() -> None:
    catalog = {
        "root": [_result("root", "1.0.0", {"dep-missing": "^1.0.0"})],
    }
    resolver = DependencyResolver(get_candidates=lambda name: catalog.get(name, []))
    try:
        resolver.resolve(root=catalog["root"][0])
        raise AssertionError("expected missing dependency error")
    except ValueError as exc:
        assert "missing dependency" in str(exc)
