# repomix-attribution - Project Specification

## Overview

A CLI tool that computes byte attribution of files in a repomix output by include-pattern category. Helps developers understand which parts of their codebase contribute most to the packed repomix output size.

**Repository:** https://github.com/vikrant82/repomix-attribution  
**Install:** `pip3 install -e .` (from source) or `pip3 install .` (released)

---

## Core Requirements

### 1. Input Handling

#### 1.1 Repomix Output File
- **Required:** Path to repomix-generated markdown file
- **Default:** `repomix-output.md` (auto-detected in current directory)
- **Format:** Markdown with `## File: path/to/file` headers marking each file's content
- **Validation:** Must exist and be readable; error if missing

#### 1.2 Repomix Config File (Optional)
- **Supported formats:** `.json5`, `.json`, `.yaml`, `.yml`
- **Default:** Auto-detects `repomix.config.json5/.json/.yaml/.yml` in current directory
- **Purpose:** Provides `include` patterns for precise file categorization
- **Fallback:** If missing, uses auto-detect from file paths (see Section 4)
- **JSON5 Support:** Handles comments (`//` and `/* */`) including those inside strings

### 2. File Parsing

#### 2.1 Output Structure
- Splits content by `## File: ` markers
- First section is preamble (summary/structure) - treated as separate category
- Each subsequent section represents one file with its path and content

#### 2.2 Size Calculation
- Measures each file section in bytes (UTF-8 encoded)
- Calculates percentage of total output size
- Formats bytes as B/KB/MB for display

### 3. Categorization

#### 3.1 Config-Based (Primary)
- Reads `include` array from repomix config
- Matches each file against glob patterns
- Groups files by matching include pattern
- **Pattern support:** `**` matches any path segments, `*` matches within segment

#### 3.2 Auto-Detect (Fallback)
When no config is available, infers categories from file paths:

| Path Pattern | Category |
|--------------|----------|
| `src/**` | `src/**` |
| `test/**`, `*.test.*` | `test/**` |
| `tests/**` | `tests/**` |
| `docs/**` | `docs/**` |
| `scripts/**` | `scripts/**` |
| `lib/**` | `lib/**` |
| `packages/<name>/**` | `packages/<name>/**` |
| `apps/<name>/**` | `apps/<name>/**` |
| `tools/**` | `tools/**` |
| `examples/**` | `examples/**` |
| `fixtures/**` | `fixtures/**` |
| `assets/**` | `assets/**` |
| `config/**` | `config/**` |
| `infra/**` | `infra/**` |
| `deploy/**` | `deploy/**` |
| `ci/**` | `ci/**` |
| `.github/**` | `.github/**` |
| Root files | `<filename>` |

### 4. Output Formats

#### 4.1 Table Output (Default)
```
Category                                            Files      Bytes        %
------------------------------------------------------------------------------
packages/qtk-plugin/src/**/*                           39   225.7 KB    34.2%
docs/**/*                                              13   146.0 KB    22.1%
...
------------------------------------------------------------------------------
Total                                                  91   659.6 KB
```

**Features:**
- Sorted by bytes (largest first) by default
- Shows file count, bytes, and percentage per category
- Includes "Preamble (summary/structure)" as separate category
- Lists unmatched files (not covered by any pattern) separately

#### 4.2 JSON Output
```json
{
  "output_file": "repomix-output.md",
  "total_bytes": 675412,
  "total_files": 91,
  "categories": {
    "docs/**/*": {
      "count": 13,
      "bytes": 149553,
      "percentage": 22.14
    },
    ...
  }
}
```

**Features:**
- Machine-readable for automation
- Includes total counts and per-category breakdown
- Percentages rounded to 2 decimal places

### 5. Sorting

#### 5.1 Sort Options
- `--sort bytes` (default): Largest byte contribution first
- `--sort count`: Most files first
- `--sort name`: Alphabetical by category name

#### 5.2 Implementation
- Applied to table output only
- JSON output preserves insertion order (config order or auto-detect order)

### 6. CLI Interface

#### 6.1 Commands
```bash
repomix-attribution [OPTIONS]
```

#### 6.2 Options
| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Path to repomix output file | `repomix-output.md` |
| `--config` | `-c` | Path to repomix config | Auto-detect |
| `--json` | `-j` | Also print JSON summary | Off |
| `--sort` | `-s` | Sort order: bytes\|count\|name | `bytes` |
| `--help` | `-h` | Show help message | - |

#### 6.3 Exit Codes
- `0`: Success
- `1`: Error (missing output file, config parse error, etc.)

### 7. Error Handling

#### 7.1 Missing Output File
- **Error:** Clear message with path
- **Action:** Exit with code 1

#### 7.2 Missing Config
- **Warning:** "No repomix config found. Using auto-detected categories from file paths."
- **Action:** Continue with auto-detect (not an error)

#### 7.3 Config Parse Error
- **Warning:** "Could not load config {path}: {error}"
- **Action:** Fall back to auto-detect

#### 7.4 Unmatched Files
- **Info:** Listed separately after table
- **Message:** "Unmatched files (not covered by any include pattern):"

### 8. Technical Requirements

#### 8.1 Language & Dependencies
- **Language:** Python 3.7+
- **Dependencies:** None (standard library only)
  - `argparse` - CLI parsing
  - `json` - Config and JSON output
  - `re` - Regex for parsing and pattern matching
  - `pathlib` - Path manipulation
  - `sys` - System operations
  - `typing` - Type hints

#### 8.2 Package Structure
```
src/
  repomix_attribution/
    __init__.py    # Main implementation (all logic)
    cli.py         # CLI entry point
pyproject.toml     # Package configuration
README.md          # Documentation
```

#### 8.3 Installation
- **Editable:** `pip3 install -e .`
- **Released:** `pip3 install .`
- **Entry point:** `repomix-attribution` command available globally

### 9. Feature Matrix

| Feature | Status | Notes |
|---------|--------|-------|
| Parse repomix output | ✅ Implemented | Splits by `## File: ` markers |
| Load JSON5 config | ✅ Implemented | Handles comments in strings |
| Load JSON config | ✅ Implemented | Standard JSON parsing |
| Load YAML config | ✅ Implemented | Requires PyYAML if used |
| Glob pattern matching | ✅ Implemented | Supports `**` across paths |
| Auto-detect categories | ✅ Implemented | 15+ common patterns |
| Config optional | ✅ Implemented | Falls back to auto-detect |
| Table output | ✅ Implemented | Formatted with alignment |
| JSON output | ✅ Implemented | Machine-readable |
| Sort by bytes | ✅ Implemented | Default, largest first |
| Sort by count | ✅ Implemented | Most files first |
| Sort by name | ✅ Implemented | Alphabetical |
| Byte formatting | ✅ Implemented | B/KB/MB with 1 decimal |
| Percentage calculation | ✅ Implemented | Of total output size |
| Preamble category | ✅ Implemented | Separate from files |
| Unmatched files | ✅ Implemented | Listed after table |
| Error handling | ✅ Implemented | Clear messages, exit codes |
| Help text | ✅ Implemented | Descriptive for each option |
| No external deps | ✅ Implemented | Standard library only |

### 10. Future Enhancements (Not Implemented)

- [ ] Config file modification (add/remove include patterns)
- [ ] Interactive mode with category selection
- [ ] Export to CSV/Excel
- [ ] Historical comparison (track changes over time)
- [ ] Visual charts (bar graph, pie chart)
- [ ] Filter by file type/extension
- [ ] Exclude specific files from analysis
- [ ] Multi-output comparison
- [ ] Web dashboard for visualization

---

## Usage Examples

### Basic Usage
```bash
# From project root with config and output present
repomix-attribution

# Specify paths explicitly
repomix-attribution -o my-output.md -c my-config.json5
```

### Without Config
```bash
# Auto-detect categories from file paths
repomix-attribution -o /path/to/output.md
```

### JSON Output
```bash
# For automation or further processing
repomix-attribution --json | jq '.categories'

# Save to file
repomix-attribution --json > attribution.json
```

### Sorting
```bash
# By file count (most files first)
repomix-attribution --sort count

# Alphabetically
repomix-attribution --sort name
```

---

## Testing

### Manual Testing
```bash
# Test with QTK project
cd /Users/chauv/vibe-tools/QTK
repomix-attribution

# Test without config
cd /tmp
repomix-attribution -o /Users/chauv/vibe-tools/QTK/repomix-output.md

# Test JSON output
repomix-attribution --json
```

### Expected Behavior
1. **With config:** Precise categorization by include patterns
2. **Without config:** Auto-detect groups by directory structure
3. **Missing output:** Clear error message, exit code 1
4. **Invalid config:** Warning, fallback to auto-detect

---

## Version History

### v1.0.0 (Current)
- Initial release
- Config-based categorization
- Auto-detect fallback
- Table and JSON output
- Three sort modes
- JSON5/JSON/YAML support

---

## Maintenance

### Updating
```bash
cd /Users/chauv/vibe-tools/repomix-attribution
# Make changes
git add -A
git commit -m "Description"
git push
```

### Reinstalling
```bash
pip3 install -e . --force-reinstall
```

### Checking Installation
```bash
which repomix-attribution
repomix-attribution --version
```

---

## Contact & Support

- **Repository:** https://github.com/vikrant82/repomix-attribution
- **Issues:** https://github.com/vikrant82/repomix-attribution/issues
- **Author:** vikrant82

---

*Last updated: 2026-07-13*
