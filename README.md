# FORScan Tools

`forscan_tools` provides modern, scriptable utilities for FORScan workflows:

- Parse `.abt` files into structured output
- Interpret Ford/OBD-II diagnostic trouble codes (DTCs)
- Generate safe, repeatable checklists before making FORScan changes

## Highlights

- Modern Python 3.11+ codebase with type hints and dataclasses
- CLI-first workflow with optional interactive file selection
- Structured exports to CSV, JSON, and JSONL
- JSONL output for easy downstream LLM/RAG ingestion
- DTC decoding with severity and troubleshooting guidance
- Safety-first change planning for FORScan module edits
- Built-in legitimacy scoring with official-source citations (`trust-report`)
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
python forscan_tools.py parse-abt --file .\\abt\\VIN123_ABS_20250101_010101.abt --out output.csv
```

### 3) Parse with additional machine-friendly outputs

```bash
python forscan_tools.py \
	parse-abt \
	--file .\\abt\\VIN123_ABS_20250101_010101.abt \
	--out output.csv \
	--json output.json \
	--jsonl output.jsonl
```

### 4) Decode DTCs

```bash
python forscan_tools.py decode-dtc --code P0171 --code U0121
```

### 5) Build a safe change checklist before writing in FORScan

```bash
python forscan_tools.py plan-change \
	--module ABS \
	--parameter TireSize \
	--current 235/65R17 \
	--target 245/65R17
```

### 6) Run tests and lint checks

```bash
pytest
ruff check .
ruff format .
```

### 7) Check source legitimacy/confidence

```bash
python forscan_tools.py trust-report --json trust_report.json
```

## CLI Options

- `parse-abt` Parse `.abt` payloads and export CSV/JSON/JSONL
- `decode-dtc` Decode one or more DTCs with severity and troubleshooting steps
- `plan-change` Produce a pre-check + rollback checklist for a planned FORScan edit
- `trust-report` Show confidence score, caveats, and official FORScan sources

For `parse-abt`, if `--file` is omitted, the tool lists files from `--abt-dir` and prompts for selection.

## Notes

- Current parser reads two little-endian unsigned integers from the payload as a safe baseline structure.
- Extend `parse_abt_bytes(...)` as you map additional FORScan record fields.
- This tool does not write to a vehicle. It is designed to improve interpretation quality and reduce coding risk before you use FORScan.
- Research references are tracked in `docs/forscan_research_notes.md`.
- Forum/Reddit intelligence summary is tracked in `docs/community_intelligence_2026-02-21.md`.

## License

MIT
