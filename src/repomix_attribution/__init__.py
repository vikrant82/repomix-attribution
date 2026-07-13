#!/usr/bin/env python3
"""Compute byte attribution of files in a repomix output by include-pattern category.

Reads the `include` array from repomix.config.json5 (or .json/.yaml/.yml) and
matches each file in the packed output against those patterns. Produces a
terminal table and optionally a JSON summary.

Usage:
    python scripts/repomix-attribution.py
    python scripts/repomix-attribution.py --output repomix-output.md
    python scripts/repomix-attribution.py --config repomix.config.json5
    python scripts/repomix-attribution.py --json   # also print JSON summary
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def strip_json5_comments(text: str) -> str:
    """Remove // and /* */ comments, and trailing commas, from JSON5 text.

    Handles // and /* */ inside string literals correctly by tracking string state.
    """
    result = []
    i = 0
    in_string = False
    string_char = None

    while i < len(text):
        ch = text[i]

        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < len(text):
                result.append(text[i + 1])
                i += 2
                continue
            if ch == string_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                string_char = ch
                result.append(ch)
            elif ch == "/" and i + 1 < len(text):
                next_ch = text[i + 1]
                if next_ch == "/":
                    # Line comment: skip to end of line
                    while i < len(text) and text[i] != "\n":
                        i += 1
                    continue
                elif next_ch == "*":
                    # Block comment: skip to */
                    i += 2
                    while i + 1 < len(text):
                        if text[i] == "*" and text[i + 1] == "/":
                            i += 2
                            break
                        i += 1
                    else:
                        i = len(text)
                    continue
                else:
                    result.append(ch)
            else:
                result.append(ch)
        i += 1

    text = "".join(result)

    # Remove trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def load_config(config_path: str) -> list[str]:
    """Load the `include` array from a repomix config file."""
    path = Path(config_path)
    text = path.read_text()

    if path.suffix == ".json5":
        text = strip_json5_comments(text)

    if path.suffix in (".json", ".json5"):
        config = json.loads(text)
    elif path.suffix in (".yaml", ".yml"):
        try:
            import yaml

            config = yaml.safe_load(text)
        except ImportError:
            print(
                "Error: PyYAML required for .yaml/.yml configs. Install with: pip install pyyaml",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(f"Error: Unsupported config format: {path.suffix}", file=sys.stderr)
        sys.exit(1)

    return config.get("include", [])


# ---------------------------------------------------------------------------
# Pattern matching
# ---------------------------------------------------------------------------


def pattern_to_regex(pattern: str) -> re.Pattern:
    """Convert a repomix glob pattern to a regex that matches file paths.

    Handles ** to match any number of path segments (including none).
    """
    i = 0
    n = len(pattern)
    result = []

    while i < n:
        c = pattern[i]

        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # ** matches anything including /
                result.append(".*")
                i += 2
                # Skip trailing / after **
                if i < n and pattern[i] == "/":
                    i += 1
            else:
                # * matches anything except /
                result.append("[^/]*")
                i += 1
        elif c == "?":
            result.append("[^/]")
            i += 1
        elif c in r".+^${}()|[]\\":
            result.append("\\" + c)
            i += 1
        else:
            result.append(c)
            i += 1

    return re.compile("^" + "".join(result) + "$")


def match_category(file_path: str, patterns: list) -> Optional[str]:
    """Return the first matching include pattern for a file path, or None."""
    for pattern, regex in patterns:
        if regex.match(file_path):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


def parse_repomix_output(content: str) -> Tuple[list, int]:
    """Parse repomix output and return list of (file_path, section_text)."""
    sections = re.split(r"^## File: ", content, flags=re.MULTILINE)
    preamble = sections[0]
    file_sections = sections[1:]

    result = []
    for section in file_sections:
        first_line = section.split("\n")[0]
        result.append((first_line, section))

    return result, len(preamble.encode("utf-8"))


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def format_bytes(n: int) -> str:
    """Format bytes as KB or MB for display."""
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    elif n >= 1024:
        return f"{n / 1024:.1f} KB"
    else:
        return f"{n} B"


def print_table(
    categories: dict[str, dict], total_bytes: int, sort_by: str = "bytes"
) -> None:
    """Print a formatted attribution table.

    Args:
        categories: Dictionary of category names to {count, bytes}
        total_bytes: Total bytes in the output file
        sort_by: Sort order - "bytes" (default), "count", or "name"
    """
    print()
    print("{:<50} {:>6} {:>10} {:>8}".format("Category", "Files", "Bytes", "%"))
    print("-" * 78)

    # Sort categories
    if sort_by == "bytes":
        sorted_cats = sorted(
            categories.items(), key=lambda x: x[1]["bytes"], reverse=True
        )
    elif sort_by == "count":
        sorted_cats = sorted(
            categories.items(), key=lambda x: x[1]["count"], reverse=True
        )
    elif sort_by == "name":
        sorted_cats = sorted(categories.items(), key=lambda x: x[0])
    else:
        sorted_cats = list(categories.items())

    for cat, info in sorted_cats:
        count = info["count"]
        size = info["bytes"]
        pct = (size / total_bytes) * 100 if total_bytes else 0
        print(
            "{:<50} {:>6} {:>10} {:>7.1f}%".format(cat, count, format_bytes(size), pct)
        )

    print("-" * 78)
    total_files = sum(info["count"] for info in categories.values())
    print("{:<50} {:>6} {:>10}".format("Total", total_files, format_bytes(total_bytes)))
    print()


def print_json_summary(
    categories: dict[str, dict], total_bytes: int, output_path: str
) -> None:
    """Print JSON summary to stdout."""
    summary = {
        "output_file": output_path,
        "total_bytes": total_bytes,
        "total_files": sum(info["count"] for info in categories.values()),
        "categories": {
            cat: {
                "count": info["count"],
                "bytes": info["bytes"],
                "percentage": round((info["bytes"] / total_bytes) * 100, 2)
                if total_bytes
                else 0,
            }
            for cat, info in categories.items()
        },
    }
    print(json.dumps(summary, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute byte attribution of files in a repomix output by include-pattern category."
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
        help="Path to repomix config file (default: auto-detect repomix.config.json5/.json/.yaml/.yml)",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Also print a JSON summary to stdout",
    )
    parser.add_argument(
        "--sort",
        "-s",
        choices=["bytes", "count", "name"],
        default="bytes",
        help='Sort order: "bytes" (default, largest first), "count", or "name"',
    )
    args = parser.parse_args(argv)

    # Resolve config path
    if args.config:
        config_path = args.config
    else:
        config_path = None
        for name in (
            "repomix.config.json5",
            "repomix.config.json",
            "repomix.config.yaml",
            "repomix.config.yml",
        ):
            if os.path.exists(name):
                config_path = name
                break
        if not config_path:
            print(
                "Error: No repomix config found. Use --config to specify one.",
                file=sys.stderr,
            )
            return 1

    # Load include patterns
    try:
        include_patterns = load_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    compiled = [(p, pattern_to_regex(p)) for p in include_patterns]

    # Parse output
    output_path = args.output
    if not os.path.exists(output_path):
        print(f"Error: Output file not found: {output_path}", file=sys.stderr)
        return 1

    content = Path(output_path).read_text()
    file_sections, preamble_size = parse_repomix_output(content)
    total_bytes = len(content.encode("utf-8"))

    # Categorize
    categories: dict[str, dict] = {}
    unmatched = []
    for file_path, section in file_sections:
        size = len(section.encode("utf-8"))
        cat = match_category(file_path, compiled)
        if cat:
            if cat not in categories:
                categories[cat] = {"count": 0, "bytes": 0}
            categories[cat]["count"] += 1
            categories[cat]["bytes"] += size
        else:
            unmatched.append((file_path, size))

    # Add preamble as its own category
    categories["Preamble (summary/structure)"] = {"count": 0, "bytes": preamble_size}

    # Print table
    print_table(categories, total_bytes, sort_by=args.sort)

    # Print unmatched files if any
    if unmatched:
        print("Unmatched files (not covered by any include pattern):")
        for fp, sz in unmatched:
            print(f"  {fp} ({format_bytes(sz)})")
        print()

    # JSON output
    if args.json:
        print_json_summary(categories, total_bytes, output_path)

    return 0


if __name__ == "__main__":
    main()
