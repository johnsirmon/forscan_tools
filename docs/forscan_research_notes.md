# FORScan Research Notes (2026-02-21)

This file captures source-backed guidance for building a modern, trustworthy assistant around FORScan.

## Official Sources Reviewed

- Home: https://forscan.org/home.html
- Products and versions: https://forscan.org/download.html
- Documentation hub: https://forscan.org/documentation.html
- HowTo hub: https://forscan.org/howto.html
- Supported modules list: https://forscan.org/modules_list.html
- Support routing: https://forscan.org/support.html
- Forum (configuration guidance): https://forscan.org/forum/viewtopic.php?f=16&t=17208

## Key Findings

- FORScan targets Ford/Mazda/Lincoln/Mercury and supports advanced module-level diagnostics not available in generic OBD-II apps.
- Configuration/programming functions are Windows-focused and tied to Extended License.
- Adapter quality is critical; official docs warn against low-quality ELM327 clones.
- Official docs explicitly state v2 documentation is still in progress, with many practical procedures moved to forum posts.
- Supported module list is extensive and useful for module normalization/alias mapping in tooling.

## Product/Tech Constraints to Respect in Our Tool

- Never claim the tool can safely auto-program ECUs without OEM procedure checks.
- Always require backup/export + battery maintainer + DTC baseline before any configuration change.
- Surface confidence levels and source citations with every recommendation.
- Distinguish clearly between:
  - Official source-backed guidance
  - Heuristic/common diagnostic patterns

## Proposed Architecture Direction

- Core CLI + library in Python 3.11+
- Structured knowledge model:
  - DTC dictionary
  - module aliases (PCM/ABS/APIM/etc.)
  - service procedure checklists
  - risk labels (low/medium/high)
- Source trust subsystem:
  - curated official URLs
  - date checked
  - confidence score and caveats
- Optional AI layer:
  - retrieval over local source corpus
  - answer must include evidence links and confidence

## Immediate Next Enhancements

- Expand DTC database with Ford-specific codes and symptom trees.
- Add module capability matrix (read-only actions vs service functions vs programming required).
- Add importers for FORScan exports (CSV/log) for automated triage.
- Add rule engine for change safety (block risky operations without prerequisites).
