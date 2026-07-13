"""Immutable domain values for repomix attribution analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class FileSection:
    """A single file section extracted from repomix output.

    ``byte_count`` is the number of bytes this section contributes to the
    total output, including the ``## File: <path>`` marker and the trailing
    newline before the section content.
    """

    path: str
    byte_count: int


@dataclass(frozen=True)
class CategoryStats:
    """Aggregated byte and file counts for one attribution category."""

    name: str
    file_count: int
    byte_count: int


@dataclass(frozen=True)
class AnalysisResult:
    """Complete result of an attribution analysis run."""

    total_bytes: int
    preamble_bytes: int
    categories: Sequence[CategoryStats]
    unmatched: Sequence[FileSection]

    @property
    def total_files(self) -> int:
        return sum(c.file_count for c in self.categories)

    @property
    def matched_bytes(self) -> int:
        return sum(c.byte_count for c in self.categories)

    @property
    def unmatched_bytes(self) -> int:
        return sum(u.byte_count for u in self.unmatched)

    def verify_byte_accounting(self) -> bool:
        """Return True if every output byte is accounted for exactly once.

        Invariant:
            preamble_bytes + matched_bytes + unmatched_bytes == total_bytes
        """
        return (
            self.preamble_bytes + self.matched_bytes + self.unmatched_bytes
            == self.total_bytes
        )
