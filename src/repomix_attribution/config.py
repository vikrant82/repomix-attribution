"""Configuration discovery and loading.

This module never calls ``sys.exit()`` or prints to stderr. It raises
:class:`repomix_attribution.errors.ConfigError` on any failure so the CLI
can decide how to surface the message.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from repomix_attribution.errors import ConfigError

# Ordered list of config file names to search when no explicit path is given.
CONFIG_CANDIDATES: tuple[str, ...] = (
    "repomix.config.json5",
    "repomix.config.json",
    "repomix.config.yaml",
    "repomix.config.yml",
)


# ---------------------------------------------------------------------------
# JSON5 helpers
# ---------------------------------------------------------------------------


def _strip_json5_comments(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments and trailing commas from JSON5 text.

    Handles comment markers and escaped characters inside string literals
    correctly by tracking string state character-by-character.
    """
    result: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    string_char: str | None = None

    while i < n:
        ch = text[i]

        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < n:
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
            elif ch == "/" and i + 1 < n:
                next_ch = text[i + 1]
                if next_ch == "/":
                    # Line comment: skip to end of line
                    while i < n and text[i] != "\n":
                        i += 1
                    continue
                if next_ch == "*":
                    # Block comment: skip to */
                    i += 2
                    while i + 1 < n:
                        if text[i] == "*" and text[i + 1] == "/":
                            i += 2
                            break
                        i += 1
                    else:
                        i = n
                    continue
                result.append(ch)
            else:
                result.append(ch)
        i += 1

    cleaned = "".join(result)
    # Remove trailing commas before } or ]
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def discover_config(cwd: Path | None = None) -> Path | None:
    """Return the first existing config candidate under *cwd*, or ``None``."""
    base = cwd or Path.cwd()
    for name in CONFIG_CANDIDATES:
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def load_config(config_path: str | Path) -> List[str]:
    """Load the ``include`` array from a repomix config file.

    Raises:
        ConfigError: if the file is missing, unreadable, in an unsupported
            format, or missing a valid ``include`` field.
    """
    path = Path(config_path)

    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc

    suffix = path.suffix.lower()

    if suffix == ".json5":
        raw = _strip_json5_comments(raw)

    try:
        if suffix in (".json", ".json5"):
            config = json.loads(raw)
        elif suffix in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore[import-not-found, unused-ignore]
            except ImportError as exc:
                raise ConfigError(
                    "PyYAML is required to load .yaml/.yml configs. "
                    "Install with: pip install pyyaml"
                ) from exc
            config = yaml.safe_load(raw)
        else:
            raise ConfigError(f"Unsupported config format: {suffix}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigError(f"Config file {path} must contain a JSON object at top level")

    include = config.get("include")
    if include is None:
        raise ConfigError(f"Config file {path} is missing the required 'include' field")
    if not isinstance(include, list) or not all(isinstance(p, str) for p in include):
        raise ConfigError(f"Config file {path} 'include' must be an array of strings")

    return list(include)
