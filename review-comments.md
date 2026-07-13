# Code Quality and Architecture Review

This document is an implementation map for improving `repomix-attribution` into a maintainable, testable Python utility. It is intentionally action-oriented so a follow-up agent can implement it in small, reviewable commits.

## Current assessment

The tool has a useful, deliberately small scope, but nearly all application behavior currently lives in `src/repomix_attribution/__init__.py` (about 450 lines). The thin `cli.py` wrapper delegates immediately into that module. This makes the first version easy to inspect, but it couples command-line handling, filesystem access, parsing, matching, aggregation, rendering, and error policy in one place.

There is no test suite, no CI configuration, and no lint/type-check configuration. As a result, behavior changes are difficult to validate and the documented development commands do not work.

The project should remain lightweight: standard-library-first, no framework, no dependency injection container, and no class hierarchy unless it creates a meaningful boundary. Prefer small modules, immutable data structures, explicit exceptions, and pure functions.

---

## Priority 1 — Establish safe change control

### 1. Add a real test suite before or alongside refactoring

**Create**

```text
tests/
  test_config.py
  test_matcher.py
  test_parser.py
  test_analysis.py
  test_reporting.py
  test_cli.py
```

**Add coverage for:**

- JSON5 comments, escaped quotes, comment markers in strings, and trailing commas.
- Supported config suffixes, malformed configs, empty/missing `include`, and explicit versus discovered config failures.
- Glob semantics: `*`, `**`, `?`, literal dots, path separators, and any advertised character-class/brace behavior.
- LF and CRLF repomix output parsing.
- Preamble-only, empty, malformed, and multiple-file output.
- Exact byte-accounting invariant: every emitted input byte is attributed exactly once, or a deliberately documented excluded-byte bucket explains the difference.
- Config and automatic categorization, including nested test filenames.
- Table output, JSON-only output, sorting, long category names, exit codes, and stderr/stdout separation.

**Implementation notes:**

- Use `pytest` and `tmp_path`; fixtures should create tiny synthetic config/output files rather than depend on QTK artifacts.
- Put development dependencies in an optional dependency group, e.g. `[project.optional-dependencies] dev = ["pytest", "ruff"]`.
- Do not claim a test command in README until the suite exists and passes.

**Done when:** `python -m pytest` passes from a clean checkout and protects each public behavior above.

---

## Priority 2 — Separate responsibilities into small modules

### 2. Replace the monolithic package module with a deliberate layout

**Target layout**

```text
src/repomix_attribution/
  __init__.py          # Version and intentionally public programmatic API only
  __main__.py          # `python -m repomix_attribution` support
  cli.py               # argparse setup, process orchestration, exit-code mapping
  models.py            # Typed immutable domain values
  config.py            # Config discovery and JSON/JSON5/YAML decoding
  matcher.py           # Include-pattern compilation and auto-detect rules
  parser.py            # Repomix output parser and byte accounting
  analysis.py          # Categorization and aggregation orchestration
  reporting.py         # Terminal and JSON serialization; no business decisions
  errors.py            # Project-specific exception types
```

**Responsibilities**

- `models.py`: dataclasses such as `FileSection`, `CategoryStats`, and `AnalysisResult`. Store numeric byte counts as integers. Prefer `@dataclass(frozen=True)` for parsed records.
- `config.py`: discover configuration candidates; load one config; validate the `include` value; provide format-specific parsing. It must never call `sys.exit()`.
- `matcher.py`: compile only validated patterns and expose one consistent matcher abstraction. Keep automatic category rules data-driven where feasible.
- `parser.py`: convert a repomix output stream or byte string into typed parsed sections. It must preserve enough information for exact byte accounting.
- `analysis.py`: accept parsed sections plus a categorizer and return an `AnalysisResult`. It must not print or read files.
- `reporting.py`: consume `AnalysisResult`; write table or JSON to a supplied text stream. JSON generation should be separately callable as a data object/string.
- `cli.py`: parse args, choose config behavior, open files, select output streams, catch expected errors, and return an integer exit status.

**API compatibility:** retain `repomix_attribution.cli:main` as the console-script target. Re-export only documented programmatic functions from `__init__.py`; do not preserve every current internal helper as public API.

**Avoid:** introducing a controller class just to hold functions. A small functional pipeline plus typed values is simpler for this CLI.

---

## Priority 3 — Define a clear domain model and error contract

### 3. Use typed result values instead of nested untyped dictionaries

The current `dict[str, dict]` shape lets misspelled keys and incomplete values survive until rendering. Replace it with explicit types.

**Suggested models**

```python
@dataclass(frozen=True)
class FileSection:
    path: str
    byte_count: int

@dataclass(frozen=True)
class CategoryStats:
    name: str
    file_count: int
    byte_count: int

@dataclass(frozen=True)
class AnalysisResult:
    total_bytes: int
    preamble_bytes: int
    categories: Sequence[CategoryStats]
    unmatched: Sequence[FileSection]
```

The final implementation may include raw section content only if truly needed. For attribution, path and byte count should be enough after parsing.

### 4. Define explicit exception types and ownership

**Create `errors.py`:**

- `ConfigError`: unreadable, unsupported, malformed, or semantically invalid configuration.
- `OutputParseError`: malformed repomix output when strict parsing is selected.
- `InputError`: missing/unreadable output input.

**Rules:**

- Library/domain modules raise exceptions; they never print and never call `sys.exit()`.
- The CLI owns messages, fallback policy, and return codes.
- If `--config PATH` was provided explicitly, an error loading it should return non-zero. Auto-detection fallback applies only when no config was supplied or discovered.

---

## Priority 4 — Improve parsing and byte-accounting design

### 5. Make byte attribution an explicit invariant

The report must make clear whether it attributes the entire packed output or only file body content. The useful industry-grade default is:

```text
preamble bytes + all file-section bytes + unmatched bytes == total output bytes
```

Include the `## File: ` marker and path/header newline in each file section, or introduce an explicit `File section headers` category. Do not silently omit delimiters while calculating percentages against the whole file.

### 6. Parse defensively and be newline-independent

- Normalize only for identifying headers; do not accidentally change the byte count used for attribution.
- Support LF and CRLF.
- Decide and document whether only headers beginning exactly at line start are valid.
- Include tests for content that contains `## File:` away from a line start so it is not treated as a file boundary.
- Use a dedicated parser rather than a broad `re.split` if retaining delimiters or streaming is simpler.

### 7. Consider streaming for large packed outputs

The current code reads the full output into memory and re-encodes each text section. That is acceptable for small inputs but scales with the packed file size.

**Preferred implementation:** read in binary mode, detect header lines, and aggregate byte counts as sections are completed. This naturally preserves original bytes and avoids repeated UTF-8 encoding.

If streaming makes the initial refactor excessively complex, retain whole-file parsing temporarily but:

- document the memory behavior,
- use `encoding="utf-8"` explicitly when text decoding is needed,
- calculate sections from bytes or avoid repeated `.encode("utf-8")`, and
- create a benchmark/large-fixture regression test before optimizing later.

---

## Priority 5 — Make matching maintainable and explicit

### 8. Treat glob semantics as a contract, not an ad-hoc regex

Before changing implementation, document the supported repomix include syntax. Then choose one of these paths:

1. Implement exactly the required subset (`*`, `**`, `?`) with unit tests and reject unsupported syntax clearly; or
2. Use a mature matcher compatible with repomix semantics, adding and documenting the dependency.

Do not imply full glob support if bracket expressions, negation, brace expansion, or ordering are unsupported. Normalize paths to POSIX separators before matching so reports are platform-consistent.

### 9. Make auto-category rules declarative

`auto_detect_categories()` is a growing conditional chain. Move the simple top-level rules into ordered data, e.g. an ordered tuple of `(prefix, category)` values. Keep specialized monorepo rules (`packages/<name>`, `apps/<name>`) as small dedicated handlers.

Also define precedence. For example, decide whether `packages/foo/test/unit.py` is grouped by package, test status, or both. The implementation and `SPEC.md` must agree.

---

## Priority 6 — Give the CLI a reliable Unix interface

### 10. Separate human and machine output

The documented `--json | jq` workflow requires stdout to contain only JSON. Adopt one of these contracts:

- `--json`: JSON-only on stdout; diagnostics to stderr. This is recommended.
- `--format {table,json}`: one selected representation on stdout.
- `--json-output PATH`: table remains stdout and JSON is written to a specified file.

Do not emit a table followed by JSON on stdout.

### 11. Complete command-line ergonomics

- Add `--version`, backed by one authoritative package version.
- Add `__main__.py` so `python -m repomix_attribution` works.
- Use `pathlib.Path` consistently rather than mixing `os.path` and `Path`.
- Explicitly use UTF-8 for config and text input; provide a concise decoding error with a path.
- Keep warnings/errors on stderr and return predictable non-zero statuses.
- Consider `--no-config` to force automatic categorization when a config exists in the working directory.

---

## Priority 7 — Modernize package and repository hygiene

### 12. Make `pyproject.toml` publication-ready

Add standard metadata:

- `readme = "README.md"`
- SPDX license declaration and a tracked `LICENSE` file
- authors/maintainers, keywords, classifiers, and project URLs
- optional `dev` and `yaml` dependency groups if those capabilities remain
- tool configuration for pytest, Ruff, and a type checker

Choose one compatibility policy and apply it consistently:

- **Python 3.9+**: permits builtin generic annotations such as `list[str]`; or
- **Python 3.7+**: use `typing.List`, `typing.Dict`, etc., and test on all claimed versions.

### 13. Add automated quality gates

Create GitHub Actions (or equivalent) that runs for supported Python versions:

```text
python -m pytest
python -m ruff check .
python -m build
```

Add type checking after the model/module split is stable. `mypy` or `pyright` is sufficient; choose one and keep its configuration minimal.

### 14. Keep docs accurate and layered

- `README.md`: installation, 2–3 accurate usage examples, format contract, supported Python versions, and link to the detailed spec.
- `SPEC.md`: product requirements and feature status only—remove machine-specific paths, stale commands, and unimplemented claims.
- `review-comments.md`: temporary remediation plan; remove or archive after all work is incorporated into the spec/changelog.
- Add `CHANGELOG.md` only when releases begin; do not create release ceremony prematurely.

---

## Suggested implementation sequence

1. Correct documented compatibility target and add a minimal pytest harness.
2. Add failing regression tests for byte accounting, CRLF, explicit invalid config, JSON-only output, and JSON5 string handling.
3. Introduce `models.py`, `errors.py`, and pure `analysis.py`; keep CLI behavior stable where intended.
4. Extract config, parser, matcher, and reporting modules one at a time with tests passing after each move.
5. Decide/fix parser byte accounting, glob contract, YAML packaging, and CLI output contract.
6. Add metadata, `--version`, `__main__.py`, lint/type/build tooling, and CI.
7. Update README and SPEC to match verified behavior exactly.

## Definition of done

- No application module directly exits the process or prints except the CLI/reporting boundary.
- Every important behavior is covered by automated tests, including cross-platform newline handling.
- Every input byte is accounted for, or excluded bytes are explicitly reported and documented.
- `--json` produces valid JSON without filtering.
- Package metadata and supported Python versions match the code and CI matrix.
- Documentation contains only executable, verified commands.
