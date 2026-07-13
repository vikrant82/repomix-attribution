"""Categorization and aggregation orchestration.

Accepts parsed file sections and a categorizer function; returns an
:class:`~repomix_attribution.models.AnalysisResult`. This module performs
no I/O and produces no output.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence

from repomix_attribution.models import (
    AnalysisResult,
    CategoryStats,
    FileSection,
)


Categorizer = Callable[[str, Sequence], Optional[str]]


def analyze(
    preamble: bytes,
    file_sections: Sequence[FileSection],
    categorizer: Categorizer,
    compiled_patterns: Sequence = (),
) -> AnalysisResult:
    """Categorize file sections and produce an :class:`AnalysisResult`.

    Args:
        preamble: Raw bytes of the preamble (everything before the first
            ``## File: `` marker). Its length is the ``preamble_bytes`` of
            the result.
        file_sections: Parsed file sections from the parser.
        categorizer: A callable ``(file_path, compiled_patterns) -> str | None``
            that returns the category label for a matched file, or ``None``
            if the file is unmatched.
        compiled_patterns: Patterns passed through to the categorizer.

    Returns:
        An :class:`AnalysisResult` with exact byte accounting.
    """
    total_bytes = len(preamble) + sum(s.byte_count for s in file_sections)
    preamble_bytes = len(preamble)

    category_map: dict[str, list[FileSection]] = {}
    unmatched: List[FileSection] = []

    for section in file_sections:
        cat = categorizer(section.path, compiled_patterns)
        if cat is not None:
            category_map.setdefault(cat, []).append(section)
        else:
            unmatched.append(section)

    categories = [
        CategoryStats(
            name=cat,
            file_count=len(sections),
            byte_count=sum(s.byte_count for s in sections),
        )
        for cat, sections in category_map.items()
    ]

    return AnalysisResult(
        total_bytes=total_bytes,
        preamble_bytes=preamble_bytes,
        categories=categories,
        unmatched=unmatched,
    )
