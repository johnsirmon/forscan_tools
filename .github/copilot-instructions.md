# Copilot Instructions

## Build, test, and lint commands

The project is a single-file Python CLI/library with tooling defined in `pyproject.toml`.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

```powershell
python -m pytest -q
python -m pytest tests\test_forscan_tools.py -k parse_abt_bytes
python -m ruff check .
python -m ruff format .
```

`pytest` is configured with `pythonpath = ["."]`, so tests import directly from the top-level `forscan_tools.py` module.

## High-level architecture

- `forscan_tools.py` is both the reusable library module and the CLI entrypoint. The public functions are imported directly in `tests\test_forscan_tools.py`, and `main()` only wires argparse subcommands to those functions.
- The CLI is organized around five flows:
  - `parse-abt`: resolve an `.abt` file, parse bytes into `ParsedRecord` dataclasses, then export CSV and optional JSON/JSONL.
  - `decode-dtc`: normalize user input, map known DTCs from the in-module knowledge base, and fall back to a generic unmapped DTC response for valid codes.
  - `plan-change`: produce a safety checklist from module/parameter/current/target inputs, with risk elevation for modules listed in `SAFETY_CRITICAL_MODULES`.
  - `trust-report`: build a report from curated `OFFICIAL_SOURCES` and optionally serialize it to JSON.
  - `explain`: normalize topic names and return structured explanations from `TOPIC_EXPLANATIONS`.
- The module-level dictionaries and tuples in `forscan_tools.py` are the knowledge base. The docs in `docs\` are not runtime inputs, but they explain the source-backed safety posture and the official/community evidence model that the CLI content mirrors.

## Key conventions

- Preserve the safety-first product boundary from `README.md`: this tool analyzes, explains, and plans, but it does not write to a vehicle directly. New guidance should keep backup, stable power, one-change-at-a-time, and rescan messaging consistent with the existing commands.
- Keep business logic in pure helper functions that return frozen dataclasses (`ParsedRecord`, `DtcInfo`, `ChangePlan`, `TrustReport`, `TopicExplanation`). The CLI layer should stay thin and mostly handle argument parsing, printing, and file output.
- Extend the in-module knowledge tables instead of scattering hardcoded behavior through `main()`. DTC decoding, topic explanations, safety-critical modules, and trust sources are all driven by module-level constants.
- Normalize user input before lookup. `decode_dtc()` depends on `normalize_dtc()`, and topic handling depends on `normalize_topic()`. Follow that pattern when adding any new user-facing lookup.
- Keep helper functions responsible for validation and raise explicit exceptions such as `ValueError` or `FileNotFoundError`; `main()` converts those into `argparse` errors. Do not move error messaging down into lower-level helpers.
- ABT discovery is filename-driven. `list_abt_files()` expects `VIN_MODULE_YYYYMMDD_HHMMSS.abt`-style names, skips anything that does not match, and sorts newest-first by parsed timestamp.
- Tests are intentionally direct and compact: they import public functions from `forscan_tools.py` instead of shelling out to the CLI. When behavior changes, update or add function-level tests in `tests\test_forscan_tools.py`.
- Ruff is configured for a 100-character line length, double quotes, and the `E`, `F`, `I`, `UP`, `B`, and `SIM` rule sets. Check the existing baseline before assuming lint is clean.
