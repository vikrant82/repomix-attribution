"""Glob pattern compilation and auto-detect categorization rules.

The glob compiler handles the subset of glob syntax used by repomix:
``*`` (any characters except ``/``), ``**`` (any path segments), and ``?``
(any single character except ``/``). Bracket expressions (``[abc]``) and
brace expansion are **not** supported and are treated literally.

Auto-detect rules are data-driven: a list of ``(prefix, category)`` tuples
is checked in order against the file path's top-level segments.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Iterable, List, Optional, Pattern, Sequence, Tuple

# Ordered rules for auto-detection. The first matching rule wins.
# Each tuple is (top-level path prefix, category label).
AUTO_DETECT_RULES: Sequence[Tuple[str, str]] = (
    ("src", "src"),
    ("test", "test"),
    ("tests", "tests"),
    ("docs", "docs"),
    ("scripts", "scripts"),
    ("lib", "lib"),
    ("tools", "tools"),
    ("examples", "examples"),
    ("fixtures", "fixtures"),
    ("assets", "assets"),
    ("config", "config"),
    ("infra", "infra"),
    ("deploy", "deploy"),
    ("ci", "ci"),
    (".github", ".github"),
)

# Monorepo package prefixes. Files inside these directories use
# <prefix>/<name>/** as their category.
MONOREPO_PREFIXES: Sequence[str] = ("packages", "apps")


# ---------------------------------------------------------------------------
# Glob compilation
# ---------------------------------------------------------------------------


def _normalize_path(path: str) -> str:
    """Normalize a file path to POSIX separators for matching."""
    # Convert backslashes to forward slashes first
    posix_path = path.replace("\\", "/")
    return str(PurePosixPath(posix_path))


def pattern_to_regex(pattern: str) -> Pattern[str]:
    """Convert a repomix glob pattern to a compiled regex.

    Supported syntax:
    - ``*`` matches any characters except ``/``
    - ``**`` matches any number of path segments (including zero)
    - ``?`` matches any single character except ``/``
    - Literal characters are matched as-is; regex metacharacters are escaped.

    Bracket expressions (``[abc]``) and brace expansion are **not** supported
    and are matched literally.
    """
    i = 0
    n = len(pattern)
    parts: list[str] = []

    while i < n:
        c = pattern[i]

        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                # ** matches anything including /
                parts.append(".*")
                i += 2
                # Skip trailing / after **
                if i < n and pattern[i] == "/":
                    i += 1
            else:
                # * matches anything except /
                parts.append("[^/]*")
                i += 1
        elif c == "?":
            parts.append("[^/]")
            i += 1
        elif c in r".+^${}()|[]\\":
            parts.append("\\" + c)
            i += 1
        else:
            parts.append(c)
            i += 1

    return re.compile("^" + "".join(parts) + "$")


def compile_patterns(patterns: Iterable[str]) -> List[Tuple[str, Pattern[str]]]:
    """Compile a list of glob patterns into (original, regex) pairs."""
    return [(p, pattern_to_regex(p)) for p in patterns]


def match_category(file_path: str, compiled: Sequence[Tuple[str, Pattern[str]]]) -> Optional[str]:
    """Return the original pattern string for the first match, or ``None``."""
    normalized = _normalize_path(file_path)
    for pattern, regex in compiled:
        if regex.match(normalized):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Auto-detect
# ---------------------------------------------------------------------------


def auto_detect_category(file_path: str, _patterns=None) -> str:
    """Infer a category label from a file path when no config is available.

    Precedence:
    1. If the top-level segment is a monorepo prefix (``packages``/``apps``),
       the category is ``<prefix>/<name>`` (or just ``<prefix>`` if there is
       no second segment).
    2. Otherwise, the first entry in :data:`AUTO_DETECT_RULES` whose prefix
       matches the top-level segment wins.
    3. Fallback: the top-level path component itself.
    """
    parts = PurePosixPath(file_path).parts
    if not parts:
        return "root"

    top = parts[0]

    # Monorepo packages/apps take precedence
    if top in MONOREPO_PREFIXES and len(parts) > 1:
        return f"{top}/{parts[1]}"

    # Standard rules
    for prefix, category in AUTO_DETECT_RULES:
        if top == prefix:
            return category

    # Fallback to first path component
    if len(parts) > 1:
        return f"{parts[0]}/**"
    return parts[0]


# Re-export for backward compatibility
match_auto_category = auto_detect_category
