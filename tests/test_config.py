"""Tests for the config loading module."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from repomix_attribution.config import (
    _strip_json5_comments,
    discover_config,
    load_config,
)
from repomix_attribution.errors import ConfigError


# ---------------------------------------------------------------------------
# JSON5 comment stripping
# ---------------------------------------------------------------------------


class TestStripJson5Comments:
    def test_line_comment_removed(self):
        text = '/* block */\n"key": "value" // trailing comment\n'
        # Block comment removed, line comment removed, but newline before block comment remains
        assert _strip_json5_comments(text) == '\n"key": "value" \n'

    def test_block_comment_removed(self):
        text = '/* line1\nline2 */"key": "value"'
        assert _strip_json5_comments(text) == '"key": "value"'

    def test_comment_inside_string_preserved(self):
        text = '"url": "https://example.com // not a comment"'
        assert _strip_json5_comments(text) == text

    def test_block_comment_inside_string_preserved(self):
        text = '"path": "/* not a comment */"'
        assert _strip_json5_comments(text) == text

    def test_escaped_quote_in_string(self):
        text = '"msg": "he\\"llo" // comment'
        assert _strip_json5_comments(text) == '"msg": "he\\"llo" '

    def test_trailing_comma_before_brace(self):
        text = '{"a": 1, "b": 2,}'
        assert _strip_json5_comments(text) == '{"a": 1, "b": 2}'

    def test_trailing_comma_before_bracket(self):
        text = "[1, 2, 3,]"
        assert _strip_json5_comments(text) == "[1, 2, 3]"

    def test_no_comments_unchanged(self):
        text = '{"a": 1, "b": [1, 2]}'
        assert _strip_json5_comments(text) == text

    def test_nested_block_comment(self):
        # Block comments do NOT nest in JSON5
        text = '/* outer /* inner */ "key": 1'
        result = _strip_json5_comments(text)
        assert result == ' "key": 1'

    def test_url_with_slashes_not_treated_as_comment(self):
        text = '"url": "https://github.com/user/repo"'
        assert _strip_json5_comments(text) == text


# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------


class TestDiscoverConfig:
    def test_finds_json5_first(self, tmp_path: Path):
        (tmp_path / "repomix.config.json5").write_text("{}")
        (tmp_path / "repomix.config.json").write_text("{}")
        result = discover_config(tmp_path)
        assert result == tmp_path / "repomix.config.json5"

    def test_falls_back_to_json(self, tmp_path: Path):
        (tmp_path / "repomix.config.json").write_text("{}")
        result = discover_config(tmp_path)
        assert result == tmp_path / "repomix.config.json"

    def test_returns_none_when_missing(self, tmp_path: Path):
        assert discover_config(tmp_path) is None

    def test_empty_directory(self, tmp_path: Path):
        assert discover_config(tmp_path) is None


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_json5_with_comments(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json5"
        cfg.write_text(
            textwrap.dedent("""\
            {
                // This is a comment
                "include": [
                    "src/**", /* another comment */
                    "test/**",
                ],
            }
            """)
        )
        result = load_config(cfg)
        assert result == ["src/**", "test/**"]

    def test_loads_plain_json(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json"
        cfg.write_text('{"include": ["docs/**"]}')
        result = load_config(cfg)
        assert result == ["docs/**"]

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "nonexistent.json5")

    def test_invalid_json_raises(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json"
        cfg.write_text("{invalid json!!!")
        with pytest.raises(ConfigError, match="Invalid JSON"):
            load_config(cfg)

    def test_missing_include_field_raises(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json"
        cfg.write_text('{"other": "field"}')
        with pytest.raises(ConfigError, match="missing"):
            load_config(cfg)

    def test_include_not_a_list_raises(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json"
        cfg.write_text('{"include": "src/**"}')
        with pytest.raises(ConfigError, match="array"):
            load_config(cfg)

    def test_include_with_non_string_raises(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json"
        cfg.write_text('{"include": [123]}')
        with pytest.raises(ConfigError, match="array of strings"):
            load_config(cfg)

    def test_yaml_without_pyyaml_raises(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.yaml"
        cfg.write_text("include:\n  - src/**\n")
        # Patch yaml import to raise ImportError
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("No module named 'yaml'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            with pytest.raises(ConfigError, match="PyYAML"):
                load_config(cfg)
        finally:
            builtins.__import__ = real_import

    def test_unsupported_format_raises(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.toml"
        cfg.write_text("[project]\n")
        with pytest.raises(ConfigError, match="Unsupported"):
            load_config(cfg)

    def test_returns_copy_of_list(self, tmp_path: Path):
        cfg = tmp_path / "repomix.config.json"
        cfg.write_text('{"include": ["src/**"]}')
        result = load_config(cfg)
        result.append("extra")
        # Modifying the returned list should not affect subsequent loads
        result2 = load_config(cfg)
        assert result2 == ["src/**"]
