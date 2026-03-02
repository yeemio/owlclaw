"""Console CLI helpers."""

from __future__ import annotations

import webbrowser
from pathlib import Path

import typer


def console_command(*, port: int = 8000, open_browser: bool = True) -> str:
    """Open OwlClaw Console URL in browser and return URL."""
    static_index = Path(__file__).resolve().parents[1] / "web" / "static" / "index.html"
    url = f"http://localhost:{port}/console/"
    if not static_index.exists():
        typer.echo("Console static files not found. Install extras: pip install owlclaw[console]")
        return url

    typer.echo(f"Opening Console: {url}")
    if open_browser:
        webbrowser.open(url)
    return url

