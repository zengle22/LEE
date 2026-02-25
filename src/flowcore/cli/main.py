"""Backward-compatible entrypoint for stale ``lee`` console scripts."""

from lee.cli.main import cli, main

__all__ = ["cli", "main"]

