# FORScan Tools

`forscan_tools` provides modern, scriptable utilities for parsing FORScan `.abt` files and exporting structured outputs for analysis and AI workflows.

## Highlights

- Modern Python 3.11+ codebase with type hints and dataclasses
- CLI-first workflow with optional interactive file selection
- Structured exports to CSV, JSON, and JSONL
- JSONL output for easy downstream LLM/RAG ingestion
- Test suite with `pytest`
- Linting/formatting setup with `ruff`

## Project Structure

- `forscan_tools.py` - Main parser and CLI entry point
- `tests/test_forscan_tools.py` - Unit tests
- `pyproject.toml` - Packaging and tooling configuration

## Quick Start

### 1) Create environment and install dev dependencies

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .[dev]
```

### 2) Parse a specific `.abt` file

```bash
python forscan_tools.py --file .\\abt\\VIN123_ABS_20250101_010101.abt --out output.csv
```

### 3) Parse with additional machine-friendly outputs

```bash
python forscan_tools.py \
	--file .\\abt\\VIN123_ABS_20250101_010101.abt \
	--out output.csv \
	--json output.json \
	--jsonl output.jsonl
```

### 4) Run tests and lint checks

```bash
pytest
ruff check .
ruff format .
```

## CLI Options

- `--abt-dir` Directory containing `.abt` files (default: `./abt`)
- `--file` Direct path to a specific `.abt` file
- `--out` CSV output path (default: `output_file.csv`)
- `--json` Optional JSON output path
- `--jsonl` Optional JSONL output path

If `--file` is omitted, the tool lists files from `--abt-dir` and prompts for selection.

## Notes

- Current parser reads two little-endian unsigned integers from the payload as a safe baseline structure.
- Extend `parse_abt_bytes(...)` as you map additional FORScan record fields.

## License

MIT
