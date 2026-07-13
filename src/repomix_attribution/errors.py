"""Project-specific exception types.

Library and domain modules raise these exceptions; they never print and never
call ``sys.exit()``. The CLI owns messages, fallback policy, and return codes.
"""


class RepomixAttributionError(Exception):
    """Base class for all repomix-attribution errors."""


class ConfigError(RepomixAttributionError):
    """Unreadable, unsupported, malformed, or semantically invalid configuration."""


class OutputParseError(RepomixAttributionError):
    """Malformed repomix output when strict parsing is selected."""


class InputError(RepomixAttributionError):
    """Missing or unreadable input file."""
