# FORScan Tools

`forscan_tools` is a safety-first helper toolkit for FORScan users working on Ford, Lincoln, Mercury, and Mazda diagnostics/configuration.

The goal is simple:

- Help you understand what you are doing before changing anything
- Reduce risk when interpreting DTCs and planning module edits
- Keep recommendations grounded in official source guidance

This project does **not** write to your vehicle directly.

## Why This Exists

FORScan is powerful, but information is spread across official pages, sticky forum posts, and community threads.

This repo consolidates that into a practical workflow:

1. Validate trust and source quality
2. Learn key concepts (As-Built, ABT, ECC, VID, TRID)
3. Parse and inspect configuration artifacts
4. Plan changes with rollback and safety checks

## Feature Overview

- `parse-abt`: parse ABT data and export CSV/JSON/JSONL
- `decode-dtc`: interpret DTCs with severity and triage steps
- `plan-change`: build pre-check, execution, and rollback checklist
- `trust-report`: confidence report with official-source citations
- `explain`: plain-language concept guide for As-Built and related topics

## Safety Principles

- Always backup before writing
- Always use stable power during configuration/programming
- Make one change at a time
- Rescan DTCs after every write
- Prefer human-readable FORScan module configuration over raw hex edits

## Glossary (Quick)

- `As-Built`: factory module configuration values
- `.AB`: factory file download format from Ford/Motorcraft
- `.ABT`: FORScan backup/export format for module configuration
- `ECC`: economized central configuration shared by multiple modules
- `VID`: PCM vehicle identification/configuration block
- `TRID`: transmission characterization data block

## Installation

### Prerequisites

- Python `3.11+`
- Windows PowerShell or any shell with Python access

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Beginner Workflow (Recommended)

### Step 1: Check trust and source quality

```bash
python forscan_tools.py trust-report --json trust_report.json
```

### Step 2: Learn the concept before touching settings

```bash
python forscan_tools.py explain --list-topics
python forscan_tools.py explain --topic asbuilt --topic abt --topic ecc
```

### Step 3: Decode existing DTCs

```bash
python forscan_tools.py decode-dtc --code P0171 --code U0121
```

### Step 4: Build a safe change plan

```bash
python forscan_tools.py plan-change \
	--module ABS \
	--parameter TireSize \
	--current 235/65R17 \
	--target 245/65R17
```

### Step 5: Parse ABT backups for analysis

```bash
python forscan_tools.py parse-abt \
	--file .\abt\VIN123_ABS_20250101_010101.abt \
	--out output.csv \
	--json output.json \
	--jsonl output.jsonl
```

## Command Reference

### `parse-abt`

Parse ABT payloads and export to machine-friendly formats.

```bash
python forscan_tools.py parse-abt --file .\abt\sample.abt --out output.csv
```

Options:

- `--abt-dir`: directory for interactive selection (default `./abt`)
- `--file`: direct ABT file path
- `--out`: CSV output path
- `--json`: optional JSON output path
- `--jsonl`: optional JSONL output path

### `decode-dtc`

Decode one or more DTCs.

```bash
python forscan_tools.py decode-dtc --code P0420 --code B10D7
```

### `plan-change`

Generate a checklist before you perform any FORScan write.

```bash
python forscan_tools.py plan-change \
	--module BCM \
	--parameter AutoLock \
	--current Disabled \
	--target Enabled
```

### `trust-report`

Summarize legitimacy/confidence and evidence sources.

```bash
python forscan_tools.py trust-report --json trust_report.json
```

### `explain`

Explain key concepts in plain language.

```bash
python forscan_tools.py explain --list-topics
python forscan_tools.py explain --topic asbuilt --topic vid
```

Supported topics currently include:

- `asbuilt`
- `abt`
- `ecc`
- `vid`
- `trid`

## Best Practices for Real Vehicle Work

1. Export baseline DTC report before any coding.
2. Save ABT backups with VIN/module/date in filename.
3. Keep a battery maintainer connected for any write/programming session.
4. Change one parameter at a time and validate behavior.
5. If a change fails, rollback immediately using known-good backup.
6. Treat community spreadsheets as hints, not truth.
7. Prefer official FORScan admin guidance when conflicts exist.

## Project Layout

- `forscan_tools.py`: main CLI and core logic
- `tests/test_forscan_tools.py`: unit tests
- `docs/forscan_research_notes.md`: official-source research synthesis
- `docs/community_intelligence_2026-02-21.md`: forum/Reddit intelligence brief
- `pyproject.toml`: Python project and tooling config

## Development

```bash
pytest
ruff check .
ruff format .
```

## Current Limitations

- ABT parsing logic is currently a safe baseline parser and not a full ABT decoder.
- DTC knowledge base is intentionally small and should be expanded.
- Change plans are advisory and should be validated against official model-specific procedures.

## Roadmap (Suggested)

1. Full ABT line parser with old/new format detection.
2. Model/year-aware DTC knowledge packs.
3. Rule engine that blocks high-risk changes unless prerequisites are confirmed.
4. Structured import of FORScan logs and scan reports.

## License

MIT
