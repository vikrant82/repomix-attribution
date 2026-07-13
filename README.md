# repomix-attribution

A reusable CLI tool to compute byte attribution of files in a repomix output by include-pattern category.

## Installation

```bash
cd /path/to/repomix-attribution
pip3 install .
```

Or for development (editable mode):

```bash
pip3 install -e .
```

## Usage

```bash
# Basic usage (auto-detects config and output files in current directory)
repomix-attribution

# Specify custom paths
repomix-attribution -c repomix.config.json5 -o repomix-output.md

# Without config (auto-detects categories from file paths)
repomix-attribution -o /path/to/repomix-output.md

# Output JSON summary (useful for automation)
repomix-attribution --json

# Sort by different criteria
repomix-attribution --sort bytes    # default, largest first
repomix-attribution --sort count    # by file count
repomix-attribution --sort name     # alphabetically
```

**Note:** The repomix config file is optional. If not found, categories are auto-detected from common directory patterns (src/, test/, docs/, packages/, etc.).

## Options

- `-o, --output FILE` - Path to repomix output file (default: `repomix-output.md`)
- `-c, --config FILE` - Path to repomix config file (default: auto-detect)
- `-j, --json` - Also print JSON summary to stdout
- `-s, --sort {bytes,count,name}` - Sort order (default: bytes)

## Features

- Reads `include` patterns from repomix config files (`.json5`, `.json`, `.yaml`, `.yml`)
- Properly handles JSON5 comments (including `//` and `/* */` inside strings)
- Correctly matches glob patterns with `**` across path separators
- Reports per-category file count, bytes, and percentage
- JSON output for programmatic use
- Works from any directory

## Example Output

```
Category                                            Files      Bytes        %
------------------------------------------------------------------------------
packages/qtk-plugin/src/**/*                           39   225.7 KB    34.2%
docs/**/*                                              13   146.0 KB    22.1%
packages/qtk-plugin/test/**/*                          13   105.8 KB    16.0%
...
------------------------------------------------------------------------------
Total                                                  91   659.6 KB
```

## Requirements

- Python 3.7+
- No external dependencies (uses only standard library)

## Development

```bash
# Install in editable mode
pip3 install -e .

# Run tests
python3 -m pytest tests/

# Lint
python3 -m ruff check src/
```

## License

MIT
