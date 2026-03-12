from __future__ import annotations

import argparse
import csv
import json
import re
import struct
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class AbtFileMeta:
    file_name: str
    vin: str
    system: str
    captured_at: datetime


@dataclass(frozen=True)
class ParsedRecord:
    offset: int
    name: str
    value: int
    interpretation: str


class SafetyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class DtcInfo:
    code: str
    title: str
    system: str
    severity: SafetyLevel
    likely_causes: tuple[str, ...]
    recommended_steps: tuple[str, ...]


@dataclass(frozen=True)
class ChangePlan:
    module: str
    parameter: str
    current_value: str
    target_value: str
    safety_level: SafetyLevel
    pre_checks: tuple[str, ...]
    execution_steps: tuple[str, ...]
    rollback_steps: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SourceEvidence:
    title: str
    url: str
    category: str
    last_checked: str
    notes: str


@dataclass(frozen=True)
class TrustReport:
    legitimacy_score: int
    verdict: str
    strengths: tuple[str, ...]
    caveats: tuple[str, ...]
    sources: tuple[SourceEvidence, ...]


@dataclass(frozen=True)
class TopicExplanation:
    topic: str
    summary: str
    why_it_matters: tuple[str, ...]
    common_mistakes: tuple[str, ...]
    best_practices: tuple[str, ...]


GENERIC_DTC_SYSTEM = {
    "P": "Powertrain",
    "B": "Body",
    "C": "Chassis",
    "U": "Network",
}


KNOWN_DTCS: dict[str, DtcInfo] = {
    "P0420": DtcInfo(
        code="P0420",
        title="Catalyst System Efficiency Below Threshold (Bank 1)",
        system="Powertrain",
        severity=SafetyLevel.MEDIUM,
        likely_causes=(
            "Aging catalytic converter",
            "Exhaust leak upstream of catalyst",
            "O2 sensor drift or wiring issue",
        ),
        recommended_steps=(
            "Confirm no exhaust leaks before replacing parts",
            "Capture live O2 sensor data before and after catalyst",
            "Address fuel trim or misfire issues first",
        ),
    ),
    "P0171": DtcInfo(
        code="P0171",
        title="System Too Lean (Bank 1)",
        system="Powertrain",
        severity=SafetyLevel.HIGH,
        likely_causes=(
            "Vacuum leak",
            "Low fuel pressure",
            "MAF sensor contamination",
        ),
        recommended_steps=(
            "Inspect intake and vacuum hoses",
            "Check fuel pressure against Ford spec",
            "Review STFT/LTFT under idle and load",
        ),
    ),
    "U0121": DtcInfo(
        code="U0121",
        title="Lost Communication With Anti-Lock Brake System Module",
        system="Network",
        severity=SafetyLevel.HIGH,
        likely_causes=(
            "ABS module power/ground issue",
            "CAN bus wiring fault",
            "Intermittent module failure",
        ),
        recommended_steps=(
            "Run network test with ignition state noted",
            "Verify ABS module power and grounds under load",
            "Check CAN high/low resistance and continuity",
        ),
    ),
    "B10D7": DtcInfo(
        code="B10D7",
        title="Key Transponder Signal Fault",
        system="Body",
        severity=SafetyLevel.MEDIUM,
        likely_causes=(
            "Weak key battery",
            "Antenna ring issue",
            "PATS programming mismatch",
        ),
        recommended_steps=(
            "Test with a second known-good key",
            "Inspect PATS antenna connector",
            "Check recent key programming history",
        ),
    ),
}


SAFETY_CRITICAL_MODULES = {
    "pcm",
    "tcm",
    "abs",
    "rcm",
    "eps",
    "srs",
}


OFFICIAL_SOURCES: tuple[SourceEvidence, ...] = (
    SourceEvidence(
        title="FORScan Home",
        url="https://forscan.org/home.html",
        category="official",
        last_checked="2026-02-21",
        notes="Core feature, adapter, and platform support statements.",
    ),
    SourceEvidence(
        title="FORScan Products and Release Notes",
        url="https://forscan.org/download.html",
        category="official",
        last_checked="2026-02-21",
        notes="Current versions and recent release history.",
    ),
    SourceEvidence(
        title="FORScan Documentation Hub",
        url="https://forscan.org/documentation.html",
        category="official",
        last_checked="2026-02-21",
        notes="Docs entrypoint; notes that v2 docs are in progress.",
    ),
    SourceEvidence(
        title="FORScan HowTo",
        url="https://forscan.org/howto.html",
        category="official",
        last_checked="2026-02-21",
        notes="Legacy links and redirects to forum-based procedures.",
    ),
    SourceEvidence(
        title="FORScan Supported Modules",
        url="https://forscan.org/modules_list.html",
        category="official",
        last_checked="2026-02-21",
        notes="Large module abbreviation reference useful for tooling.",
    ),
    SourceEvidence(
        title="FORScan Forum Configuration Guidance",
        url="https://forscan.org/forum/viewtopic.php?f=16&t=17208",
        category="official-community",
        last_checked="2026-02-21",
        notes="Pinned practical guidance for module configuration workflows.",
    ),
)


TOPIC_EXPLANATIONS: dict[str, TopicExplanation] = {
    "asbuilt": TopicExplanation(
        topic="As-Built",
        summary=(
            "As-Built is factory configuration data for modules. Once you edit values,"
            " it is no longer factory As-Built."
        ),
        why_it_matters=(
            "Used to restore modules to known factory-state values.",
            "Critical when replacing modules or recovering from bad edits.",
            "Many forum spreadsheets and comparisons are based on As-Built lines.",
        ),
        common_mistakes=(
            "Treating As-Built as universal between different trims/years/modules.",
            "Editing raw hex without a backup and rollback plan.",
            "Assuming every visible block is safe user configuration data.",
        ),
        best_practices=(
            "Export backup before any write and keep timestamped copies.",
            "Prefer human-readable Module Configuration over raw As-Built edits.",
            "Write one change at a time and rescan DTCs after each step.",
        ),
    ),
    "abt": TopicExplanation(
        topic="ABT Files",
        summary=(
            "ABT is FORScan's module configuration backup/export format."
            " Newer FORScan versions use an updated encoding for large block/line values."
        ),
        why_it_matters=(
            "ABT is your practical restore point before risky changes.",
            "Compatibility differs between old and new FORScan versions.",
            "Useful for offline comparison and change audits.",
        ),
        common_mistakes=(
            "Opening old ABT tools against new-encoding ABT content without conversion.",
            "Confusing Motorcraft .AB files with FORScan .ABT backups.",
            "Relying on one backup copy only.",
        ),
        best_practices=(
            "Keep both module-level ABT backups and a whole-session export.",
            "Version your ABT backups by VIN/module/date.",
            "Verify your restore path before making complex edits.",
        ),
    ),
    "ecc": TopicExplanation(
        topic="Economized Central Configuration (ECC)",
        summary=(
            "ECC stores shared vehicle data used across multiple modules"
            " (for example VIN/tire size/axle ratio in newer platforms)."
        ),
        why_it_matters=(
            "ECC changes can affect many modules at once.",
            "Post-change relearn/initialization may be required.",
            "Missed synchronization can trigger U2100/U2101-style faults.",
        ),
        common_mistakes=(
            "Updating ECC values but skipping module initialization/relearn.",
            "Assuming only the edited module is impacted.",
            "Applying values copied from a different platform without validation.",
        ),
        best_practices=(
            "Use official procedure notes for your exact platform and year.",
            "Run relearn synchronization after ECC writes if applicable.",
            "Baseline scan before change and compare DTC deltas after.",
        ),
    ),
    "vid": TopicExplanation(
        topic="PCM VID",
        summary=(
            "VID (Vehicle Identification block) contains crucial PCM-related configuration"
            " and may require checksum-aware/special handling."
        ),
        why_it_matters=(
            "Incorrect VID edits can affect drivability and calibration behavior.",
            "Some older platforms may need special programming/update flow.",
            "Adapter capabilities and stable power become even more critical.",
        ),
        common_mistakes=(
            "Treating VID like ordinary As-Built text edits.",
            "Using low-quality adapters for firmware-related operations.",
            "Attempting VID work without a fully verified fallback plan.",
        ),
        best_practices=(
            "Use dedicated FORScan VID-related procedures where provided.",
            "Confirm adapter requirements before attempting changes.",
            "Do not proceed without power stabilization and complete backups.",
        ),
    ),
    "trid": TopicExplanation(
        topic="TCM TRID",
        summary=("TRID is transmission characterization data and is safety/drivability sensitive."),
        why_it_matters=(
            "Checksum/protection and format constraints can apply.",
            "Bad changes can cause shifting or transmission behavior issues.",
            "Dedicated procedures are safer than raw block edits.",
        ),
        common_mistakes=(
            "Editing TRID through generic As-Built workflows.",
            "Applying copied values without matching hardware/firmware context.",
            "Skipping post-operation validation drive cycles.",
        ),
        best_practices=(
            "Use FORScan Transmission Characterization Update when applicable.",
            "Avoid experimentation in this area unless you have a clear recovery path.",
            "Validate with DTC checks and controlled test drive afterward.",
        ),
    ),
}


def list_abt_files(directory: Path) -> list[AbtFileMeta]:
    if not directory.exists() or not directory.is_dir():
        return []

    abt_files: list[AbtFileMeta] = []
    for file_path in directory.glob("*.abt"):
        parts = file_path.name.split("_")
        if len(parts) < 4:
            continue

        vin = parts[0]
        system = parts[1]
        date_str = parts[2]
        time_str = parts[3].split(".")[0]

        try:
            captured_at = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        except ValueError:
            continue

        abt_files.append(
            AbtFileMeta(
                file_name=file_path.name,
                vin=vin,
                system=system,
                captured_at=captured_at,
            )
        )

    return sorted(abt_files, key=lambda item: item.captured_at, reverse=True)


def prompt_user_to_select_file(abt_files: list[AbtFileMeta]) -> str:
    print("Please select a file to parse:")
    for idx, file_meta in enumerate(abt_files, start=1):
        print(
            f"{idx}: {file_meta.file_name} "
            f"(VIN: {file_meta.vin}, System: {file_meta.system}, "
            f"Date: {file_meta.captured_at:%Y-%m-%d %H:%M:%S})"
        )

    choice = input("Enter the number of the file you want to parse: ")
    try:
        choice_idx = int(choice) - 1
    except ValueError as exc:
        raise ValueError("Selection must be a valid integer.") from exc

    if 0 <= choice_idx < len(abt_files):
        return abt_files[choice_idx].file_name
    raise ValueError("Selection is out of range.")


def parse_abt_bytes(payload: bytes) -> list[ParsedRecord]:
    if len(payload) < 8:
        raise ValueError("ABT payload must contain at least 8 bytes.")

    fields = [
        (0, "first_uint32", "Primary sample value"),
        (4, "second_uint32", "Secondary sample value"),
    ]

    records: list[ParsedRecord] = []
    for offset, name, interpretation in fields:
        value = struct.unpack_from("<I", payload, offset)[0]
        records.append(
            ParsedRecord(
                offset=offset,
                name=name,
                value=value,
                interpretation=interpretation,
            )
        )

    return records


def read_abt_file(file_path: Path) -> list[ParsedRecord]:
    with file_path.open("rb") as handle:
        return parse_abt_bytes(handle.read())


def write_csv(parsed_data: Iterable[ParsedRecord], csv_file_path: Path) -> None:
    with csv_file_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["offset", "name", "value", "interpretation"])
        for record in parsed_data:
            writer.writerow([record.offset, record.name, record.value, record.interpretation])


def write_json(parsed_data: Iterable[ParsedRecord], json_file_path: Path) -> None:
    serializable = [record.__dict__ for record in parsed_data]
    with json_file_path.open("w", encoding="utf-8") as json_file:
        json.dump(serializable, json_file, indent=2)


def write_jsonl(parsed_data: Iterable[ParsedRecord], jsonl_file_path: Path) -> None:
    with jsonl_file_path.open("w", encoding="utf-8") as jsonl_file:
        for record in parsed_data:
            jsonl_file.write(json.dumps(record.__dict__))
            jsonl_file.write("\n")


def normalize_dtc(code: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", code).upper()


def infer_system_from_dtc(code: str) -> str:
    if not code:
        return "Unknown"
    return GENERIC_DTC_SYSTEM.get(code[0], "Unknown")


def decode_dtc(code: str) -> DtcInfo:
    normalized = normalize_dtc(code)
    known = KNOWN_DTCS.get(normalized)
    if known:
        return known

    if re.fullmatch(r"[PBCU][0-9A-F]{4}", normalized):
        return DtcInfo(
            code=normalized,
            title="Unknown/Unmapped DTC",
            system=infer_system_from_dtc(normalized),
            severity=SafetyLevel.MEDIUM,
            likely_causes=("Code not yet mapped in local knowledge base",),
            recommended_steps=(
                "Capture freeze frame data",
                "Use FORScan service function tests for affected module",
                "Consult Ford service documentation for this exact code",
            ),
        )

    raise ValueError(f"Invalid DTC format: {code}")


def plan_change(
    module: str,
    parameter: str,
    current_value: str,
    target_value: str,
) -> ChangePlan:
    module_key = module.strip().lower()
    safety_level = SafetyLevel.HIGH if module_key in SAFETY_CRITICAL_MODULES else SafetyLevel.MEDIUM

    pre_checks = (
        "Connect stable battery maintainer before any write",
        "Save full module backup (As-Built and plain-text export)",
        "Scan all modules and export baseline DTC report",
        "Verify ignition state and network stability",
    )
    execution_steps = (
        f"Open {module} in FORScan Configuration and Programming",
        f"Locate parameter '{parameter}' and confirm current value '{current_value}'",
        f"Apply target value '{target_value}'",
        "Perform module reset/relearn if prompted by FORScan",
        "Rescan DTCs and validate no new faults",
    )
    rollback_steps = (
        "If behavior regresses, restore previous value immediately",
        "If communication faults appear, write original As-Built backup",
        "Clear DTCs only after root cause is addressed and repair is verified",
    )

    warnings = (
        "This tool does not perform writes to the vehicle.",
        "Always validate against official Ford service data before programming.",
    )
    if safety_level is SafetyLevel.HIGH:
        warnings = warnings + (
            "Safety-critical module detected: use OEM procedure and do not proceed"
            " without backup power.",
        )

    return ChangePlan(
        module=module,
        parameter=parameter,
        current_value=current_value,
        target_value=target_value,
        safety_level=safety_level,
        pre_checks=pre_checks,
        execution_steps=execution_steps,
        rollback_steps=rollback_steps,
        warnings=warnings,
    )


def print_dtc_report(entries: list[DtcInfo]) -> None:
    for entry in entries:
        print(f"Code: {entry.code}")
        print(f"Title: {entry.title}")
        print(f"System: {entry.system}")
        print(f"Severity: {entry.severity.value}")
        print("Likely causes:")
        for item in entry.likely_causes:
            print(f"- {item}")
        print("Recommended steps:")
        for step in entry.recommended_steps:
            print(f"- {step}")
        print()


def print_change_plan(plan: ChangePlan) -> None:
    print(f"Module: {plan.module}")
    print(f"Parameter: {plan.parameter}")
    print(f"Current -> Target: {plan.current_value} -> {plan.target_value}")
    print(f"Safety level: {plan.safety_level.value}")
    print("\nPre-checks:")
    for item in plan.pre_checks:
        print(f"- {item}")
    print("\nExecution steps:")
    for item in plan.execution_steps:
        print(f"- {item}")
    print("\nRollback steps:")
    for item in plan.rollback_steps:
        print(f"- {item}")
    print("\nWarnings:")
    for item in plan.warnings:
        print(f"- {item}")


def build_trust_report() -> TrustReport:
    score = 100

    strengths = [
        "Primary project website and long-term publication history are available.",
        "Current release notes show active maintenance (v2.3.70 referenced).",
        "Support, documentation, and forum channels are clearly linked.",
    ]
    caveats = [
        "Documentation for FORScan v2 is incomplete on static docs pages.",
        "Some HowTo material has moved to forum posts, so procedures can fragment.",
        "Vehicle support for newest model years is marked best-effort.",
    ]

    score -= 10
    score -= 5
    score -= 5

    if score >= 85:
        verdict = "high-confidence with normal technical caution"
    elif score >= 70:
        verdict = "moderate-confidence, verify per-vehicle before writes"
    else:
        verdict = "low-confidence, do not use without independent validation"

    return TrustReport(
        legitimacy_score=score,
        verdict=verdict,
        strengths=tuple(strengths),
        caveats=tuple(caveats),
        sources=OFFICIAL_SOURCES,
    )


def print_trust_report(report: TrustReport) -> None:
    print(f"Legitimacy score: {report.legitimacy_score}/100")
    print(f"Verdict: {report.verdict}")
    print("\nStrengths:")
    for item in report.strengths:
        print(f"- {item}")
    print("\nCaveats:")
    for item in report.caveats:
        print(f"- {item}")
    print("\nSources:")
    for source in report.sources:
        print(f"- [{source.category}] {source.title}: {source.url} (checked {source.last_checked})")


def trust_report_as_json(report: TrustReport) -> dict[str, object]:
    return {
        "legitimacy_score": report.legitimacy_score,
        "verdict": report.verdict,
        "strengths": list(report.strengths),
        "caveats": list(report.caveats),
        "sources": [source.__dict__ for source in report.sources],
    }


def normalize_topic(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def list_topics() -> list[str]:
    return sorted(TOPIC_EXPLANATIONS.keys())


def get_topic_explanation(topic: str) -> TopicExplanation:
    normalized = normalize_topic(topic)
    found = TOPIC_EXPLANATIONS.get(normalized)
    if not found:
        available = ", ".join(list_topics())
        raise ValueError(f"Unknown topic '{topic}'. Available: {available}")
    return found


def print_topic_explanation(explanation: TopicExplanation) -> None:
    print(f"Topic: {explanation.topic}")
    print(f"Summary: {explanation.summary}")
    print("\nWhy it matters:")
    for item in explanation.why_it_matters:
        print(f"- {item}")
    print("\nCommon mistakes:")
    for item in explanation.common_mistakes:
        print(f"- {item}")
    print("\nBest practices:")
    for item in explanation.best_practices:
        print(f"- {item}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "FORScan helper for ABT parsing, Ford DTC interpretation, and safe change planning."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Examples:
              python forscan_tools.py parse-abt --file .\\abt\\sample.abt --out out.csv
              python forscan_tools.py decode-dtc --code P0171 --code U0121
              python forscan_tools.py plan-change --module ABS --parameter TireSize \\
                --current 235/65R17 --target 245/65R17
              python forscan_tools.py explain --topic asbuilt --topic ecc
            """
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_abt = subparsers.add_parser("parse-abt", help="Parse .abt binary payloads")
    parse_abt.add_argument(
        "--abt-dir",
        type=Path,
        default=Path("abt"),
        help="Directory containing .abt files (default: ./abt)",
    )
    parse_abt.add_argument(
        "--file",
        type=Path,
        help="Direct path to an .abt file. If omitted, interactive selection is used.",
    )
    parse_abt.add_argument(
        "--out",
        type=Path,
        default=Path("output_file.csv"),
        help="CSV output path (default: output_file.csv)",
    )
    parse_abt.add_argument("--json", type=Path, help="Optional JSON output path.")
    parse_abt.add_argument(
        "--jsonl",
        type=Path,
        help="Optional JSONL output path (useful for AI/LLM pipelines).",
    )

    decode = subparsers.add_parser("decode-dtc", help="Decode one or more Ford/OBD-II DTC codes")
    decode.add_argument(
        "--code",
        action="append",
        required=True,
        help="Diagnostic code, repeat flag for multiple (example: --code P0171 --code U0121)",
    )

    plan = subparsers.add_parser(
        "plan-change",
        help="Generate a safety-first FORScan change checklist",
    )
    plan.add_argument("--module", required=True, help="Target module (example: ABS, PCM, BCM)")
    plan.add_argument("--parameter", required=True, help="Setting/parameter to modify")
    plan.add_argument("--current", required=True, help="Current value")
    plan.add_argument("--target", required=True, help="Target value")

    trust = subparsers.add_parser(
        "trust-report",
        help="Show legitimacy/confidence report based on official FORScan sources",
    )
    trust.add_argument(
        "--json",
        type=Path,
        help="Optional JSON output path for automation.",
    )

    explain = subparsers.add_parser(
        "explain",
        help="Explain FORScan concepts in plain language (asbuilt, abt, ecc, vid, trid)",
    )
    explain.add_argument(
        "--topic",
        action="append",
        help="Topic to explain; repeat flag for multiple topics.",
    )
    explain.add_argument(
        "--list-topics",
        action="store_true",
        help="List supported explanation topics.",
    )

    return parser


def resolve_abt_file(args: argparse.Namespace) -> Path:
    if args.file:
        return args.file

    abt_files = list_abt_files(args.abt_dir)
    if not abt_files:
        raise FileNotFoundError(f"No .abt files found in directory: {args.abt_dir}")

    selected = prompt_user_to_select_file(abt_files)
    return args.abt_dir / selected


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parse-abt":
        try:
            abt_file_path = resolve_abt_file(args)
            parsed_data = read_abt_file(abt_file_path)
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
            return 2

        write_csv(parsed_data, args.out)
        if args.json:
            write_json(parsed_data, args.json)
        if args.jsonl:
            write_jsonl(parsed_data, args.jsonl)

        print(f"Processed {abt_file_path.name}")
        print(f"CSV output: {args.out}")
        if args.json:
            print(f"JSON output: {args.json}")
        if args.jsonl:
            print(f"JSONL output: {args.jsonl}")
        return 0

    if args.command == "decode-dtc":
        try:
            entries = [decode_dtc(code) for code in args.code]
        except ValueError as exc:
            parser.error(str(exc))
            return 2
        print_dtc_report(entries)
        return 0

    if args.command == "plan-change":
        plan = plan_change(
            module=args.module,
            parameter=args.parameter,
            current_value=args.current,
            target_value=args.target,
        )
        print_change_plan(plan)
        return 0

    if args.command == "trust-report":
        report = build_trust_report()
        print_trust_report(report)
        if args.json:
            args.json.write_text(
                json.dumps(trust_report_as_json(report), indent=2),
                encoding="utf-8",
            )
            print(f"JSON output: {args.json}")
        return 0

    if args.command == "explain":
        if args.list_topics:
            print("Supported topics:")
            for topic in list_topics():
                print(f"- {topic}")
            return 0

        if not args.topic:
            parser.error("explain requires --topic or --list-topics")
            return 2

        try:
            explanations = [get_topic_explanation(topic) for topic in args.topic]
        except ValueError as exc:
            parser.error(str(exc))
            return 2

        for idx, explanation in enumerate(explanations):
            print_topic_explanation(explanation)
            if idx < len(explanations) - 1:
                print("\n" + "=" * 72 + "\n")
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
