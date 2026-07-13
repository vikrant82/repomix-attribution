"""Repomix output parser with exact byte accounting.

The parser operates on raw bytes so that every input byte is attributed
exactly once:

    preamble_bytes + sum(file_section.byte_count for all sections) == total_bytes
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from repomix_attribution.errors import OutputParseError
from repomix_attribution.models import FileSection

# The marker that separates file sections in repomix output.
# We split on the leading newline so the newline belongs to the previous
# section (or preamble), keeping byte accounting exact.
_FILE_MARKER = b"\n## File: "


def parse_repomix_bytes(content: bytes) -> Tuple[bytes, List[FileSection]]:
    """Parse repomix output given as raw bytes.

    Returns:
        A tuple of ``(preamble_bytes, file_sections)`` where every byte of
        ``content`` is accounted for exactly once:

        ``len(preamble_bytes) + sum(s.byte_count for s in file_sections) == len(content)``

    Raises:
        OutputParseError: if the output contains no file sections at all.
    """
    parts = content.split(_FILE_MARKER)
    preamble = parts[0]
    sections: List[FileSection] = []

    for part in parts[1:]:
        # ``part`` starts with ``## File: `` (without the leading newline,
        # which is part of the previous section).
        # Find the end of the path line (handle both CRLF and LF).
        newline_pos = part.find(b"\r\n")
        if newline_pos == -1:
            newline_pos = part.find(b"\n")

        if newline_pos >= 0:
            path_bytes = part[:newline_pos]
            section_body = part  # includes path + newline + content
        else:
            # No newline at all: the entire remainder is the path with no
            # content. This is unusual but handled gracefully.
            path_bytes = part
            section_body = part

        try:
            path = path_bytes.decode("utf-8")
        except UnicodeDecodeError:
            path = path_bytes.decode("utf-8", errors="replace")

        sections.append(
            FileSection(
                path=path,
                byte_count=len(_FILE_MARKER) + len(section_body),
            )
        )

    if not sections and len(content) == 0:
        # Empty file: no error, just no sections
        return preamble, sections

    if not sections:
        raise OutputParseError("Repomix output contains no '## File:' sections")

    return preamble, sections


def parse_repomix_file(path: Path) -> Tuple[bytes, List[FileSection]]:
    """Parse a repomix output file from disk.

    Reads in binary mode to preserve exact byte counts.

    Raises:
        OutputParseError: if the file cannot be read or contains no sections.
    """
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise OutputParseError(f"Cannot read output file {path}: {exc}") from exc

    return parse_repomix_bytes(content)
