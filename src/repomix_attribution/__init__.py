"""repomix-attribution: compute byte attribution of repomix output by category.

Public programmatic API:

- :func:`load_config` — load include patterns from a config file
- :func:`compile_patterns` — compile glob patterns to regexes
- :func:`parse_repomix_file` — parse a repomix output file
- :func:`analyze` — categorize file sections and produce a result
- :func:`render_table`, :func:`render_json` — format results for output
- :class:`AnalysisResult`, :class:`CategoryStats`, :class:`FileSection` — domain models
- :class:`ConfigError`, :class:`OutputParseError`, :class:`InputError` — exceptions
"""

from repomix_attribution.__about__ import __version__
from repomix_attribution.analysis import analyze
from repomix_attribution.config import load_config
from repomix_attribution.errors import ConfigError, InputError, OutputParseError
from repomix_attribution.matcher import compile_patterns, match_category
from repomix_attribution.models import AnalysisResult, CategoryStats, FileSection
from repomix_attribution.parser import parse_repomix_bytes, parse_repomix_file
from repomix_attribution.reporting import render_json, render_table

__all__ = [
    "__version__",
    "analyze",
    "compile_patterns",
    "ConfigError",
    "InputError",
    "load_config",
    "match_category",
    "OutputParseError",
    "parse_repomix_bytes",
    "parse_repomix_file",
    "render_json",
    "render_table",
    "AnalysisResult",
    "CategoryStats",
    "FileSection",
]
