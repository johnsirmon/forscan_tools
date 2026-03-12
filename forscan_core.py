from __future__ import annotations

import argparse
import csv
import json
import re
import struct
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from forscan_data import (
    GENERIC_DTC_SYSTEM,
    KNOWN_DTCS,
    OFFICIAL_SOURCES,
    SAFETY_CRITICAL_MODULES,
    TOPIC_EXPLANATIONS,
)
from forscan_models import (
    ABT_CAPTURED_AT_FORMAT,
    ABT_FIELDS,
    AbtFileMeta,
    ChangePlan,
    DtcInfo,
    ParsedRecord,
    SafetyLevel,
    TopicExplanation,
    TrustReport,
)


def parse_abt_file_meta(file_path: Path) -> AbtFileMeta | None:
    parts = file_path.name.split("_")
    if len(parts) < 4:
        return None

    date_str = parts[2]
    time_str = parts[3].split(".")[0]

    try:
        captured_at = datetime.strptime(date_str + time_str, ABT_CAPTURED_AT_FORMAT)
    except ValueError:
        return None

    return AbtFileMeta(
        file_name=file_path.name,
        vin=parts[0],
        system=parts[1],
        captured_at=captured_at,
    )


def list_abt_files(directory: Path) -> list[AbtFileMeta]:
    if not directory.exists() or not directory.is_dir():
        return []

    abt_files = [
        meta
        for file_path in directory.glob("*.abt")
        if (meta := parse_abt_file_meta(file_path)) is not None
    ]
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

    records: list[ParsedRecord] = []
    for offset, name, interpretation in ABT_FIELDS:
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


def serialize_records(parsed_data: Iterable[ParsedRecord]) -> list[dict[str, object]]:
    return [asdict(record) for record in parsed_data]


def write_json(parsed_data: Iterable[ParsedRecord], json_file_path: Path) -> None:
    with json_file_path.open("w", encoding="utf-8") as json_file:
        json.dump(serialize_records(parsed_data), json_file, indent=2)


def write_jsonl(parsed_data: Iterable[ParsedRecord], jsonl_file_path: Path) -> None:
    with jsonl_file_path.open("w", encoding="utf-8") as jsonl_file:
        for record in serialize_records(parsed_data):
            jsonl_file.write(json.dumps(record))
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


def trust_report_as_json(report: TrustReport) -> dict[str, object]:
    return {
        "legitimacy_score": report.legitimacy_score,
        "verdict": report.verdict,
        "strengths": list(report.strengths),
        "caveats": list(report.caveats),
        "sources": [asdict(source) for source in report.sources],
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


def resolve_abt_file(args: argparse.Namespace) -> Path:
    if args.file:
        return args.file

    abt_files = list_abt_files(args.abt_dir)
    if not abt_files:
        raise FileNotFoundError(f"No .abt files found in directory: {args.abt_dir}")

    selected = prompt_user_to_select_file(abt_files)
    return args.abt_dir / selected
