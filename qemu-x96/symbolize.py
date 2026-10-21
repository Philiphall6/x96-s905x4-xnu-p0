#!/usr/bin/env python3
"""Resolve XNU panic addresses with the Mach-O kernel symbol table."""

import argparse
import bisect
import re
import struct
from pathlib import Path


MH_MAGIC_64 = 0xFEEDFACF
LC_SYMTAB = 0x2


def read_symbols(kernel: Path) -> list[tuple[int, str]]:
    blob = kernel.read_bytes()
    if len(blob) < 32:
        raise ValueError("kernel is too small to be a Mach-O image")

    magic, _, _, _, command_count, _, _, _ = struct.unpack_from("<8I", blob)
    if magic != MH_MAGIC_64:
        raise ValueError(f"unsupported Mach-O magic 0x{magic:08x}")

    command_offset = 32
    symtab = None
    for _ in range(command_count):
        command, command_size = struct.unpack_from("<II", blob, command_offset)
        if command_size < 8 or command_offset + command_size > len(blob):
            raise ValueError("invalid Mach-O load command")
        if command == LC_SYMTAB:
            symtab = struct.unpack_from("<4I", blob, command_offset + 8)
        command_offset += command_size

    if symtab is None:
        raise ValueError("kernel has no Mach-O symbol table")

    symbol_offset, symbol_count, strings_offset, strings_size = symtab
    symbols = []
    for index in range(symbol_count):
        entry_offset = symbol_offset + index * 16
        string_index, _, _, _, value = struct.unpack_from("<IBBHQ", blob, entry_offset)
        if value == 0 or string_index >= strings_size:
            continue
        name_offset = strings_offset + string_index
        name_end = blob.find(b"\0", name_offset, strings_offset + strings_size)
        if name_end < 0:
            continue
        name = blob[name_offset:name_end].decode("utf-8", "replace")
        if name:
            symbols.append((value, name))

    symbols.sort()
    if not symbols:
        raise ValueError("kernel symbol table is empty")
    return symbols


def serial_addresses(serial: Path) -> list[int]:
    text = serial.read_text(errors="replace")
    patterns = (
        r"caller\s+(0x[0-9a-fA-F]+)",
        r"\bat pc\s+(0x[0-9a-fA-F]+)",
        r"\blr:\s+(0x[0-9a-fA-F]+)",
    )
    addresses = []
    for pattern in patterns:
        addresses.extend(int(match, 16) for match in re.findall(pattern, text))
    return list(dict.fromkeys(addresses))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", type=Path)
    parser.add_argument("addresses", nargs="*")
    parser.add_argument("--serial", type=Path)
    args = parser.parse_args()

    addresses = [int(value, 0) for value in args.addresses]
    if args.serial is not None:
        addresses.extend(serial_addresses(args.serial))
    addresses = list(dict.fromkeys(addresses))
    if not addresses:
        parser.error("provide an address or a serial log containing a panic")

    symbols = read_symbols(args.kernel)
    values = [value for value, _ in symbols]
    for address in addresses:
        index = bisect.bisect_right(values, address) - 1
        if index < 0:
            print(f"0x{address:016x} <before first symbol>")
            continue
        value, name = symbols[index]
        print(f"0x{address:016x} {name}+0x{address - value:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
