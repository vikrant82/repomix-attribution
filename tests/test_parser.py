"""Tests for the repomix output parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from repomix_attribution.errors import OutputParseError
from repomix_attribution.parser import parse_repomix_bytes, parse_repomix_file


# ---------------------------------------------------------------------------
# parse_repomix_bytes
# ---------------------------------------------------------------------------


class TestParseRepomixBytes:
    def test_single_file(self):
        content = b"# Repomix Output\n\n## File: src/main.ts\nconsole.log('hi');\n"
        preamble, sections = parse_repomix_bytes(content)
        assert len(preamble) > 0
        assert len(sections) == 1
        assert sections[0].path == "src/main.ts"
        # Byte accounting: preamble + section == total
        assert len(preamble) + sections[0].byte_count == len(content)

    def test_multiple_files(self):
        content = (
            b"# Repomix Output\n\n"
            b"## File: src/a.ts\nconsole.log('a');\n"
            b"## File: src/b.ts\nconsole.log('b');\n"
        )
        preamble, sections = parse_repomix_bytes(content)
        assert len(sections) == 2
        assert sections[0].path == "src/a.ts"
        assert sections[1].path == "src/b.ts"
        assert len(preamble) + sections[0].byte_count + sections[1].byte_count == len(content)

    def test_crlf_line_endings(self):
        content = b"# Repomix Output\r\n\r\n## File: src/main.ts\r\nconsole.log('hi');\r\n"
        preamble, sections = parse_repomix_bytes(content)
        assert len(sections) == 1
        assert sections[0].path == "src/main.ts"
        assert len(preamble) + sections[0].byte_count == len(content)

    def test_crlf_multiple_files(self):
        content = b"# Output\r\n\r\n## File: a.ts\r\ncontent a\r\n## File: b.ts\r\ncontent b\r\n"
        preamble, sections = parse_repomix_bytes(content)
        assert len(sections) == 2
        assert sections[0].path == "a.ts"
        assert sections[1].path == "b.ts"
        total = len(preamble) + sum(s.byte_count for s in sections)
        assert total == len(content)

    def test_byte_accounting_invariant(self):
        """Every input byte must be accounted for exactly once."""
        content = (
            b"# Preamble with some content\n\n"
            b"## File: file1.ts\nline1\nline2\n"
            b"## File: file2.ts\nline3\n"
            b"## File: file3.ts\n"
        )
        preamble, sections = parse_repomix_bytes(content)
        total = len(preamble) + sum(s.byte_count for s in sections)
        assert total == len(content), f"Byte accounting failed: {total} != {len(content)}"

    def test_empty_content(self):
        preamble, sections = parse_repomix_bytes(b"")
        assert len(sections) == 0
        assert len(preamble) == 0

    def test_preamble_only_no_sections(self):
        content = b"# Just a preamble\nNo files here.\n"
        # This should raise because there are no ## File: sections
        with pytest.raises(OutputParseError):
            parse_repomix_bytes(content)

    def test_file_with_no_content_after_path(self):
        """A file section where the path line has no trailing newline."""
        content = b"# Output\n\n## File: empty.ts"
        preamble, sections = parse_repomix_bytes(content)
        assert len(sections) == 1
        assert sections[0].path == "empty.ts"
        assert len(preamble) + sections[0].byte_count == len(content)

    def test_path_with_spaces(self):
        content = b"# Output\n\n## File: my file.ts\ncontent\n"
        preamble, sections = parse_repomix_bytes(content)
        assert sections[0].path == "my file.ts"

    def test_path_with_special_chars(self):
        content = b"# Output\n\n## File: src/utils/helper.test.spec.ts\nx\n"
        preamble, sections = parse_repomix_bytes(content)
        assert sections[0].path == "src/utils/helper.test.spec.ts"

    def test_content_containing_file_marker_not_at_line_start(self):
        """A line like '## File:' in the middle of content should not
        be treated as a file boundary."""
        content = (
            b"# Output\n\n"
            b"## File: src/main.ts\n"
            b"// This is not a file marker: ## File: fake.ts\n"
            b"console.log('done');\n"
        )
        preamble, sections = parse_repomix_bytes(content)
        assert len(sections) == 1
        assert sections[0].path == "src/main.ts"
        assert "## File: fake.ts" in content.decode()

    def test_deeply_nested_paths(self):
        content = (
            b"# Output\n\n"
            b"## File: packages/foo/src/components/deep/nested/file.ts\n"
            b"export default {};\n"
        )
        preamble, sections = parse_repomix_bytes(content)
        assert sections[0].path == "packages/foo/src/components/deep/nested/file.ts"

    def test_large_content(self):
        """Ensure byte accounting holds for larger content."""
        preamble = b"# Large preamble\n" * 100
        file1 = b"## File: a.ts\n" + b"x" * 5000 + b"\n"
        file2 = b"## File: b.ts\n" + b"y" * 3000 + b"\n"
        content = preamble + file1 + file2
        parsed_preamble, sections = parse_repomix_bytes(content)
        total = len(parsed_preamble) + sum(s.byte_count for s in sections)
        assert total == len(content)


# ---------------------------------------------------------------------------
# parse_repomix_file
# ---------------------------------------------------------------------------


class TestParseRepomixFile:
    def test_reads_from_disk(self, tmp_path: Path):
        (tmp_path / "output.md").write_bytes(b"# Output\n\n## File: src/main.ts\nconsole.log(1);\n")
        preamble, sections = parse_repomix_file(tmp_path / "output.md")
        assert len(sections) == 1
        assert sections[0].path == "src/main.ts"

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(OutputParseError, match="Cannot read"):
            parse_repomix_file(tmp_path / "nonexistent.md")

    def test_byte_counts_match_read_bytes(self, tmp_path: Path):
        content = b"# Output\n\n## File: a.ts\nline1\n## File: b.ts\nline2\n"
        path = tmp_path / "output.md"
        path.write_bytes(content)
        preamble, sections = parse_repomix_file(path)
        total = len(preamble) + sum(s.byte_count for s in sections)
        assert total == len(content)
