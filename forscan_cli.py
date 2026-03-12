from __future__ import annotations

import argparse
import json
import textwrap
from collections.abc import Callable, Iterable
from pathlib import Path

from forscan_core import (
    build_trust_report,
    decode_dtc,
    get_topic_explanation,
    list_topics,
    plan_change,
    read_abt_file,
    resolve_abt_file,
    trust_report_as_json,
    write_csv,
    write_json,
    write_jsonl,
)
from forscan_models import EXPLANATION_SEPARATOR, ChangePlan, DtcInfo, TopicExplanation, TrustReport


def print_bulleted_section(title: str, items: Iterable[str]) -> None:
    print(f"\n{title}:")
    for item in items:
        print(f"- {item}")


def print_dtc_report(entries: list[DtcInfo]) -> None:
    for entry in entries:
        print(f"Code: {entry.code}")
        print(f"Title: {entry.title}")
        print(f"System: {entry.system}")
        print(f"Severity: {entry.severity.value}")
        print_bulleted_section("Likely causes", entry.likely_causes)
        print_bulleted_section("Recommended steps", entry.recommended_steps)
        print()


def print_change_plan(plan: ChangePlan) -> None:
    print(f"Module: {plan.module}")
    print(f"Parameter: {plan.parameter}")
    print(f"Current -> Target: {plan.current_value} -> {plan.target_value}")
    print(f"Safety level: {plan.safety_level.value}")
    print_bulleted_section("Pre-checks", plan.pre_checks)
    print_bulleted_section("Execution steps", plan.execution_steps)
    print_bulleted_section("Rollback steps", plan.rollback_steps)
    print_bulleted_section("Warnings", plan.warnings)


def print_trust_report(report: TrustReport) -> None:
    print(f"Legitimacy score: {report.legitimacy_score}/100")
    print(f"Verdict: {report.verdict}")
    print_bulleted_section("Strengths", report.strengths)
    print_bulleted_section("Caveats", report.caveats)
    print("\nSources:")
    for source in report.sources:
        print(f"- [{source.category}] {source.title}: {source.url} (checked {source.last_checked})")


def print_topic_explanation(explanation: TopicExplanation) -> None:
    print(f"Topic: {explanation.topic}")
    print(f"Summary: {explanation.summary}")
    print_bulleted_section("Why it matters", explanation.why_it_matters)
    print_bulleted_section("Common mistakes", explanation.common_mistakes)
    print_bulleted_section("Best practices", explanation.best_practices)


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


def handle_parse_abt_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int:
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


def handle_decode_dtc_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int:
    try:
        entries = [decode_dtc(code) for code in args.code]
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    print_dtc_report(entries)
    return 0


def handle_plan_change_command(
    args: argparse.Namespace,
    _parser: argparse.ArgumentParser,
) -> int:
    plan = plan_change(
        module=args.module,
        parameter=args.parameter,
        current_value=args.current,
        target_value=args.target,
    )
    print_change_plan(plan)
    return 0


def handle_trust_report_command(
    args: argparse.Namespace,
    _parser: argparse.ArgumentParser,
) -> int:
    report = build_trust_report()
    print_trust_report(report)
    if args.json:
        args.json.write_text(
            json.dumps(trust_report_as_json(report), indent=2),
            encoding="utf-8",
        )
        print(f"JSON output: {args.json}")
    return 0


def handle_explain_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> int:
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
            print(EXPLANATION_SEPARATOR)
    return 0


COMMAND_HANDLERS: dict[str, Callable[[argparse.Namespace, argparse.ArgumentParser], int]] = {
    "parse-abt": handle_parse_abt_command,
    "decode-dtc": handle_decode_dtc_command,
    "plan-change": handle_plan_change_command,
    "trust-report": handle_trust_report_command,
    "explain": handle_explain_command,
}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    handler = COMMAND_HANDLERS.get(args.command)
    if handler is None:
        parser.error("Unknown command")
        return 2
    return handler(args, parser)
