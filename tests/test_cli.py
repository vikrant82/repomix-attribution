"""Tests for the CLI module."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from repomix_attribution.cli import main


def _write_repomix_output(
    path: Path, preamble: str = "# Output\n\n", files: dict[str, str] | None = None
):
    """Helper to create a synthetic repomix output file."""
    content = preamble
    for file_path, body in (files or {}).items():
        content += f"## File: {file_path}\n{body}\n"
    path.write_text(content)


def _write_config(path: Path, includes: list[str]):
    """Helper to create a minimal JSON config file."""
    path.write_text(json.dumps({"include": includes}))


class TestCLIBasic:
    def test_missing_output_file(self, tmp_path: Path):
        result = main(["-o", str(tmp_path / "missing.md")])
        assert result == 1

    def test_help(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0

    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_default_run(self, tmp_path: Path):
        output = tmp_path / "repomix-output.md"
        output.write_text(
            "# Output\n\n"
            "## File: src/main.ts\nconsole.log(1);\n"
            "## File: test/unit.ts\nassert(true);\n"
        )
        result = main(["-o", str(output)])
        assert result == 0

    def test_json_output(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: src/main.ts\nconsole.log(1);\n")
        result = main(["-o", str(output), "--json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "total_bytes" in data
        assert "categories" in data

    def test_json_is_pure_json(self, tmp_path: Path, capsys):
        """--json must produce only JSON on stdout, no table."""
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: src/main.ts\nconsole.log(1);\n")
        main(["-o", str(output), "--json"])
        captured = capsys.readouterr()
        # Must be valid JSON
        json.loads(captured.out)
        # Must not contain table markers
        assert "Category" not in captured.out
        assert "Files" not in captured.out


class TestCLISorting:
    def test_sort_by_bytes(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text(
            "# Output\n\n## File: src/big.ts\n" + "x" * 1000 + "\n## File: test/small.ts\nx\n"
        )
        main(["-o", str(output), "--sort", "bytes"])
        captured = capsys.readouterr()
        # src should appear before test (more bytes)
        assert captured.out.index("src") < captured.out.index("test")

    def test_sort_by_name(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: zeta.ts\nx\n## File: alpha.ts\nx\n")
        main(["-o", str(output), "--sort", "name"])
        captured = capsys.readouterr()
        assert captured.out.index("alpha") < captured.out.index("zeta")


class TestCLIConfig:
    def test_explicit_config(self, tmp_path: Path):
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: src/main.ts\nconsole.log(1);\n")
        config = tmp_path / "repomix.config.json"
        _write_config(config, ["src/**"])
        result = main(["-o", str(output), "-c", str(config)])
        assert result == 0

    def test_explicit_invalid_config_returns_nonzero(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: src/main.ts\nx\n")
        config = tmp_path / "bad.config.json"
        config.write_text("{invalid!!!")
        with pytest.raises(SystemExit) as exc_info:
            main(["-o", str(output), "-c", str(config)])
        assert exc_info.value.code == 2

    def test_auto_detect_when_no_config(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text(
            "# Output\n\n"
            "## File: src/main.ts\nconsole.log(1);\n"
            "## File: test/unit.ts\nassert(true);\n"
        )
        # No config file present
        result = main(["-o", str(output)])
        assert result == 0

    def test_no_config_flag_forces_auto_detect(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: src/main.ts\nconsole.log(1);\n")
        # Create a config file but force --no-config
        _write_config(tmp_path / "repomix.config.json", [])
        result = main(["-o", str(output), "--no-config"])
        assert result == 0

    def test_discovered_config_used(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text("# Output\n\n## File: src/main.ts\nconsole.log(1);\n")
        _write_config(tmp_path / "repomix.config.json", ["src/**"])
        result = main(["-o", str(output)])
        assert result == 0


class TestCLIByteAccounting:
    def test_byte_accounting_in_json(self, tmp_path: Path):
        """The JSON output should reflect accurate byte counts."""
        output = tmp_path / "repomix-output.md"
        preamble = "# Preamble\n\n"
        file1 = "## File: src/a.ts\n" + "x" * 100 + "\n"
        file2 = "## File: test/b.ts\n" + "y" * 50 + "\n"
        output.write_text(preamble + file1 + file2)

        result = main(["-o", str(output), "--json"])
        assert result == 0

        # Verify byte accounting via the parser directly
        from repomix_attribution.parser import parse_repomix_file

        preamble_bytes, sections = parse_repomix_file(output)
        total = len(preamble_bytes) + sum(s.byte_count for s in sections)
        assert total == output.read_bytes().__len__()


class TestCLIMultipleFiles:
    def test_many_files(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        content = "# Output\n\n"
        for i in range(20):
            content += f"## File: src/file{i}.ts\nconsole.log({i});\n"
        output.write_text(content)
        result = main(["-o", str(output)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Total" in captured.out


class TestCLIUnmatched:
    def test_unmatched_files_shown(self, tmp_path: Path, capsys):
        output = tmp_path / "repomix-output.md"
        output.write_text(
            "# Output\n\n## File: src/main.ts\nconsole.log(1);\n## File: docs/readme.md\n# Docs\n"
        )
        config = tmp_path / "repomix.config.json"
        _write_config(config, ["src/**"])
        result = main(["-o", str(output), "-c", str(config)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Unmatched files" in captured.out
        assert "docs/readme.md" in captured.out
