"""Terminal table and JSON serialization for attribution results.

All output is written to a provided text stream (defaults to ``sys.stdout``).
This module makes no business decisions; it only formats and prints the
data handed to it.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import IO, Sequence

from repomix_attribution.models import AnalysisResult, CategoryStats


def format_bytes(n: int) -> str:
    """Format a byte count as ``B``, ``KB``, or ``MB``."""
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------


def _sort_categories(
    categories: Sequence[CategoryStats], sort_by: str
) -> Sequence[CategoryStats]:
    """Return categories sorted by the given key."""
    if sort_by == "count":
        return sorted(categories, key=lambda c: c.file_count, reverse=True)
    if sort_by == "name":
        return sorted(categories, key=lambda c: c.name)
    # Default: bytes descending
    return sorted(categories, key=lambda c: c.byte_count, reverse=True)


def render_table(
    result: AnalysisResult,
    sort_by: str = "bytes",
    stream: IO[str] | None = None,
) -> None:
    """Print the attribution table to *stream* (default: ``sys.stdout``)."""
    out = stream or sys.stdout
    categories = _sort_categories(result.categories, sort_by)

    out.write("\n")
    out.write("{:<50} {:>6} {:>10} {:>8}\n".format("Category", "Files", "Bytes", "%"))
    out.write("-" * 78 + "\n")

    for cat in categories:
        pct = (cat.byte_count / result.total_bytes) * 100 if result.total_bytes else 0
        out.write(
            "{:<50} {:>6} {:>10} {:>7.1f}%\n".format(
                cat.name, cat.file_count, format_bytes(cat.byte_count), pct
            )
        )

    out.write("-" * 78 + "\n")
    out.write(
        "{:<50} {:>6} {:>10}\n".format(
            "Total", result.total_files, format_bytes(result.total_bytes)
        )
    )
    out.write("\n")

    if result.unmatched:
        out.write("Unmatched files (not covered by any include pattern):\n")
        for section in result.unmatched:
            out.write(f"  {section.path} ({format_bytes(section.byte_count)})\n")
        out.write("\n")


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------


def result_to_dict(result: AnalysisResult) -> dict:
    """Convert an :class:`AnalysisResult` to a JSON-serializable dict."""
    return {
        "total_bytes": result.total_bytes,
        "preamble_bytes": result.preamble_bytes,
        "total_files": result.total_files,
        "categories": [
            {
                "name": c.name,
                "file_count": c.file_count,
                "byte_count": c.byte_count,
                "percentage": round((c.byte_count / result.total_bytes) * 100, 2)
                if result.total_bytes
                else 0,
            }
            for c in result.categories
        ],
        "unmatched": [
            {"path": u.path, "byte_count": u.byte_count} for u in result.unmatched
        ],
    }


def render_json(
    result: AnalysisResult,
    output_path: str,
    stream: IO[str] | None = None,
) -> None:
    """Print a JSON summary to *stream* (default: ``sys.stdout``).

    The JSON contains only the summary data — no table, no diagnostics.
    """
    out = stream or sys.stdout
    summary = result_to_dict(result)
    summary["output_file"] = output_path
    json.dump(summary, out, indent=2)
    out.write("\n")
