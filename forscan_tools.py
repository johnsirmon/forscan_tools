from __future__ import annotations

import argparse
import csv
import json
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


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
            writer.writerow(
                [record.offset, record.name, record.value, record.interpretation]
            )


def write_json(parsed_data: Iterable[ParsedRecord], json_file_path: Path) -> None:
    serializable = [record.__dict__ for record in parsed_data]
    with json_file_path.open("w", encoding="utf-8") as json_file:
        json.dump(serializable, json_file, indent=2)


def write_jsonl(parsed_data: Iterable[ParsedRecord], jsonl_file_path: Path) -> None:
    with jsonl_file_path.open("w", encoding="utf-8") as jsonl_file:
        for record in parsed_data:
            jsonl_file.write(json.dumps(record.__dict__))
            jsonl_file.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse FORScan .abt files and export structured results."
    )
    parser.add_argument(
        "--abt-dir",
        type=Path,
        default=Path("abt"),
        help="Directory containing .abt files (default: ./abt)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Direct path to an .abt file. If omitted, interactive selection is used.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output_file.csv"),
        help="CSV output path (default: output_file.csv)",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        help="Optional JSONL output path (useful for AI/LLM pipelines).",
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


if __name__ == "__main__":
    raise SystemExit(main())
