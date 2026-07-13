"""Tests for the reporting module."""

from __future__ import annotations

import io
import json

from repomix_attribution.analysis import analyze
from repomix_attribution.matcher import compile_patterns
from repomix_attribution.models import FileSection
from repomix_attribution.reporting import (
    format_bytes,
    render_json,
    render_table,
    result_to_dict,
)


def _make_result(
    total_bytes: int = 1000,
    preamble_bytes: int = 100,
    categories=None,
    unmatched=None,
):
    """Helper to create a minimal AnalysisResult for testing."""
    from repomix_attribution.models import CategoryStats

    cats = categories or [
        CategoryStats(name="src/**", file_count=5, byte_count=600),
        CategoryStats(name="test/**", file_count=3, byte_count=200),
    ]
    un = unmatched or []
    return type(
        "Result",
        (),
        {
            "total_bytes": total_bytes,
            "preamble_bytes": preamble_bytes,
            "categories": cats,
            "unmatched": un,
            "total_files": sum(c.file_count for c in cats),
            "matched_bytes": sum(c.byte_count for c in cats),
            "unmatched_bytes": sum(u.byte_count for u in un),
        },
    )()


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(0) == "0 B"
        assert format_bytes(512) == "512 B"

    def test_kilobytes(self):
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(2048) == "2.0 KB"

    def test_megabytes(self):
        assert format_bytes(1_048_576) == "1.0 MB"
        assert format_bytes(2_097_152) == "2.0 MB"


class TestRenderTable:
    def test_writes_to_stream(self, capsys):
        result = _make_result()
        stream = io.StringIO()
        render_table(result, sort_by="bytes", stream=stream)
        output = stream.getvalue()
        assert "Category" in output
        assert "Files" in output
        assert "Bytes" in output
        assert "%" in output
        assert "src/**" in output
        assert "test/**" in output
        assert "Total" in output

    def test_sort_by_count(self):
        result = _make_result(
            categories=[
                type("C", (), {"name": "alpha", "file_count": 1, "byte_count": 900})(),
                type("C", (), {"name": "beta", "file_count": 5, "byte_count": 100})(),
            ]
        )
        stream = io.StringIO()
        render_table(result, sort_by="count", stream=stream)
        output = stream.getvalue()
        # beta (5 files) should appear before alpha (1 file)
        assert output.index("beta") < output.index("alpha")

    def test_sort_by_name(self):
        result = _make_result(
            categories=[
                type("C", (), {"name": "zeta", "file_count": 1, "byte_count": 100})(),
                type("C", (), {"name": "alpha", "file_count": 1, "byte_count": 100})(),
            ]
        )
        stream = io.StringIO()
        render_table(result, sort_by="name", stream=stream)
        output = stream.getvalue()
        assert output.index("alpha") < output.index("zeta")

    def test_unmatched_section(self):
        result = _make_result(
            unmatched=[
                FileSection("unknown/file.ts", 50),
            ]
        )
        stream = io.StringIO()
        render_table(result, stream=stream)
        output = stream.getvalue()
        assert "Unmatched files" in output
        assert "unknown/file.ts" in output

    def test_zero_total_bytes(self):
        result = _make_result(total_bytes=0, categories=[])
        stream = io.StringIO()
        render_table(result, stream=stream)
        # Should not divide by zero
        output = stream.getvalue()
        assert "%" in output


class TestRenderJson:
    def test_json_structure(self):
        result = _make_result()
        stream = io.StringIO()
        render_json(result, "test.md", stream=stream)
        data = json.loads(stream.getvalue())
        assert "total_bytes" in data
        assert "preamble_bytes" in data
        assert "total_files" in data
        assert "categories" in data
        assert "output_file" in data
        assert data["output_file"] == "test.md"

    def test_json_category_fields(self):
        result = _make_result()
        stream = io.StringIO()
        render_json(result, "test.md", stream=stream)
        data = json.loads(stream.getvalue())
        for cat in data["categories"]:
            assert "name" in cat
            assert "file_count" in cat
            assert "byte_count" in cat
            assert "percentage" in cat

    def test_json_unmatched(self):
        result = _make_result(unmatched=[FileSection("x.ts", 10)])
        stream = io.StringIO()
        render_json(result, "test.md", stream=stream)
        data = json.loads(stream.getvalue())
        assert len(data["unmatched"]) == 1
        assert data["unmatched"][0]["path"] == "x.ts"

    def test_json_no_table(self):
        """--json output must be pure JSON, no table mixed in."""
        result = _make_result()
        stream = io.StringIO()
        render_json(result, "test.md", stream=stream)
        output = stream.getvalue()
        # Should parse as valid JSON
        json.loads(output)
        # Should not contain table headers
        assert "Category" not in output
        assert "Files" not in output


class TestResultToDict:
    def test_serializable(self):
        result = _make_result()
        data = result_to_dict(result)
        # Must be JSON-serializable
        json.dumps(data)
        assert isinstance(data["categories"], list)
        assert isinstance(data["unmatched"], list)
