"""Command-line interface for repomix-attribution.

Owns argument parsing, file I/O, error handling, and exit codes.
Delegates all business logic to the other modules in this package.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from repomix_attribution import __version__
from repomix_attribution.analysis import analyze, Categorizer
from repomix_attribution.config import discover_config, load_config
from repomix_attribution.errors import (
    ConfigError,
    InputError,
    OutputParseError,
)
from repomix_attribution.matcher import compile_patterns, match_category
from repomix_attribution.parser import parse_repomix_file
from repomix_attribution.reporting import render_json, render_table


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repomix-attribution",
        description="Compute byte attribution of files in a repomix output by include-pattern category.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="repomix-output.md",
        help="Path to the repomix output file (default: repomix-output.md)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help=(
            "Path to repomix config file. "
            "If omitted, the first existing repomix.config.{json5,json,yaml,yml} "
            "in the current directory is used. If no config is found or loading fails, "
            "categories are auto-detected from file paths."
        ),
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip config discovery and use auto-detected categories only.",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Print JSON summary to stdout (replaces the table).",
    )
    parser.add_argument(
        "--sort",
        "-s",
        choices=["bytes", "count", "name"],
        default="bytes",
        help='Sort order: "bytes" (default, largest first), "count", or "name"',
    )
    return parser


def _resolve_config(
    args: argparse.Namespace,
) -> tuple[list[str], bool]:
    """Return (compiled_patterns, using_auto_detect).

    Raises ConfigError when --config was given explicitly and loading fails.
    Raises InputError when the output file is missing.
    """
    if args.no_config:
        return [], True

    if args.config:
        # Explicit config: fail loudly on any error
        try:
            patterns = load_config(args.config)
        except ConfigError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)
        return patterns, False

    # Auto-discover
    config_path = discover_config()
    if config_path is None:
        return [], True

    try:
        patterns = load_config(config_path)
        return patterns, False
    except ConfigError as exc:
        print(
            f"Warning: Could not load config {config_path}: {exc}",
            file=sys.stderr,
        )
        print(
            "Falling back to auto-detected categories from file paths.",
            file=sys.stderr,
        )
        return [], True


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    if not output_path.is_file():
        print(f"Error: Output file not found: {output_path}", file=sys.stderr)
        return 1

    # Load config or fall back to auto-detect
    patterns, using_auto_detect = _resolve_config(args)
    compiled = compile_patterns(patterns)

    if using_auto_detect and not patterns:
        # Use auto-detect categorizer (wraps to match expected signature)
        from repomix_attribution.matcher import auto_detect_category

        categorizer: Categorizer = lambda path, _compiled: auto_detect_category(path)
    else:
        categorizer = match_category

    # Parse output
    try:
        preamble, file_sections = parse_repomix_file(output_path)
    except OutputParseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Analyze
    result = analyze(preamble, file_sections, categorizer, compiled_patterns=compiled)

    # Render
    if args.json:
        render_json(result, str(output_path))
    else:
        render_table(result, sort_by=args.sort)

    return 0


if __name__ == "__main__":
    sys.exit(main())
