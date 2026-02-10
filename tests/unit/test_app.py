"""Basic tests for OwlClaw application."""

from owlclaw import OwlClaw, __version__


def test_version():
    assert __version__ == "0.1.0"


def test_app_creation():
    app = OwlClaw("test-app")
    assert app.name == "test-app"
