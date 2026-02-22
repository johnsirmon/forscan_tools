from pathlib import Path

import pytest

from forscan_tools import list_abt_files, parse_abt_bytes, read_abt_file, write_csv


def test_parse_abt_bytes_extracts_two_fields() -> None:
    payload = bytes([1, 0, 0, 0, 2, 0, 0, 0])

    records = parse_abt_bytes(payload)

    assert len(records) == 2
    assert records[0].name == "first_uint32"
    assert records[0].value == 1
    assert records[1].name == "second_uint32"
    assert records[1].value == 2


def test_parse_abt_bytes_requires_minimum_length() -> None:
    with pytest.raises(ValueError, match="at least 8 bytes"):
        parse_abt_bytes(b"1234")


def test_list_abt_files_sorts_descending(tmp_path: Path) -> None:
    old_file = tmp_path / "VIN123_ABS_20240101_010101.abt"
    new_file = tmp_path / "VIN123_ABS_20250101_010101.abt"
    old_file.write_bytes(b"\x00" * 8)
    new_file.write_bytes(b"\x00" * 8)

    files = list_abt_files(tmp_path)

    assert [item.file_name for item in files] == [new_file.name, old_file.name]


def test_read_abt_file_and_write_csv(tmp_path: Path) -> None:
    source = tmp_path / "VIN123_ABS_20250101_010101.abt"
    source.write_bytes(bytes([3, 0, 0, 0, 4, 0, 0, 0]))

    parsed = read_abt_file(source)
    output = tmp_path / "out.csv"
    write_csv(parsed, output)

    content = output.read_text(encoding="utf-8")
    assert "first_uint32" in content
    assert "second_uint32" in content
