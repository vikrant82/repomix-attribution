"""Tests for the analysis module."""

from __future__ import annotations

from repomix_attribution.analysis import analyze
from repomix_attribution.matcher import compile_patterns, match_category
from repomix_attribution.models import FileSection


def _categorizer_none(_path: str, _patterns) -> None:
    return None


def _categorizer_always_src(path: str, _patterns) -> str | None:
    if path.startswith("src/"):
        return "src/**"
    return None


class TestAnalyze:
    def test_basic_categorization(self):
        preamble = b"# Preamble\n"
        sections = [
            FileSection("src/main.ts", 100),
            FileSection("src/utils.ts", 50),
            FileSection("test/unit.ts", 30),
        ]
        compiled = compile_patterns(["src/**"])
        result = analyze(preamble, sections, _categorizer_always_src, compiled)

        assert result.total_bytes == len(preamble) + 100 + 50 + 30
        assert result.preamble_bytes == len(preamble)
        assert result.total_files == 2
        assert result.unmatched_bytes == 30

    def test_byte_accounting(self):
        preamble = b"# Preamble\n"
        sections = [
            FileSection("src/a.ts", 100),
            FileSection("test/b.ts", 50),
        ]
        result = analyze(preamble, sections, _categorizer_none, [])
        assert result.verify_byte_accounting()

    def test_all_matched(self):
        preamble = b""
        sections = [
            FileSection("src/a.ts", 10),
            FileSection("src/b.ts", 20),
        ]
        result = analyze(preamble, sections, _categorizer_always_src, [])
        assert len(result.unmatched) == 0
        assert result.matched_bytes == 30

    def test_all_unmatched(self):
        preamble = b"# Only preamble\n"
        sections = [
            FileSection("docs/readme.md", 100),
        ]
        result = analyze(preamble, sections, _categorizer_none, [])
        assert len(result.categories) == 0
        assert len(result.unmatched) == 1
        assert result.unmatched[0].path == "docs/readme.md"

    def test_empty_sections(self):
        preamble = b""
        result = analyze(preamble, [], _categorizer_none, [])
        assert result.total_bytes == 0
        assert result.total_files == 0
        assert result.verify_byte_accounting()

    def test_category_grouping(self):
        preamble = b""
        sections = [
            FileSection("src/a.ts", 10),
            FileSection("src/b.ts", 20),
            FileSection("src/c.ts", 30),
        ]
        result = analyze(preamble, sections, _categorizer_always_src, [])
        assert len(result.categories) == 1
        assert result.categories[0].name == "src/**"
        assert result.categories[0].file_count == 3
        assert result.categories[0].byte_count == 60

    def test_multiple_categories(self):
        preamble = b""
        sections = [
            FileSection("src/a.ts", 10),
            FileSection("test/b.ts", 20),
        ]

        def two_cat(path, _patterns):
            if path.startswith("src/"):
                return "src/**"
            if path.startswith("test/"):
                return "test/**"
            return None

        result = analyze(preamble, sections, two_cat, [])
        assert len(result.categories) == 2
        names = {c.name for c in result.categories}
        assert names == {"src/**", "test/**"}

    def test_unmatched_preserves_sections(self):
        preamble = b""
        sections = [
            FileSection("src/a.ts", 10),
            FileSection("random/file.ts", 50),
        ]
        result = analyze(preamble, sections, _categorizer_none, [])
        # Both sections are unmatched since categorizer returns None for all
        assert len(result.unmatched) == 2
        assert result.unmatched[0].path == "src/a.ts"
        assert result.unmatched[0].byte_count == 10
        assert result.unmatched[1].path == "random/file.ts"
        assert result.unmatched[1].byte_count == 50
