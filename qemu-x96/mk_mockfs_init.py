#!/usr/bin/env python3
"""Wrap one relocation-free ARM64 Mach-O object in a static signed executable."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct


MH_MAGIC_64 = 0xFEEDFACF
CPU_TYPE_ARM64 = 0x0100000C
MH_OBJECT = 1
MH_EXECUTE = 2
MH_NOUNDEFS = 1
LC_SEGMENT_64 = 0x19
LC_SYMTAB = 0x2
LC_UNIXTHREAD = 0x5
LC_CODE_SIGNATURE = 0x1D
ARM_THREAD_STATE64 = 6
ARM_THREAD_STATE64_COUNT = 68
VM_PROT_READ = 1
VM_PROT_EXECUTE = 4
TEXT_ATTRIBUTES = 0x80000400
BASE = 0x100000000
SEGMENT_SIZE = 0x4000
CODE_OFFSET = 0x400
IDENTIFIER = b"org.x96.p0.init\0"


def object_text(blob: bytes) -> tuple[bytes, int]:
    magic, cpu, _, filetype, ncmds, _, _, _ = struct.unpack_from("<8I", blob)
    if (magic, cpu, filetype) != (MH_MAGIC_64, CPU_TYPE_ARM64, MH_OBJECT):
        raise ValueError("input is not an ARM64 Mach-O object")
    command_offset = 32
    text = None
    text_address = 0
    symbols = None
    for _ in range(ncmds):
        command, command_size = struct.unpack_from("<II", blob, command_offset)
        if command == LC_SEGMENT_64:
            section_count = struct.unpack_from("<I", blob, command_offset + 64)[0]
            for index in range(section_count):
                section_offset = command_offset + 72 + index * 80
                values = struct.unpack_from("<16s16sQQIIIIIIII", blob, section_offset)
                section = values[0].split(b"\0", 1)[0]
                segment = values[1].split(b"\0", 1)[0]
                address, size, file_offset, relocations = values[2], values[3], values[4], values[7]
                if size and (segment, section) != (b"__TEXT", b"__text"):
                    raise ValueError(f"unexpected non-empty section {segment!r},{section!r}")
                if (segment, section) == (b"__TEXT", b"__text"):
                    if relocations:
                        raise ValueError("init text contains relocations")
                    text = blob[file_offset:file_offset + size]
                    text_address = address
        elif command == LC_SYMTAB:
            symbols = struct.unpack_from("<4I", blob, command_offset + 8)
        command_offset += command_size
    if text is None or symbols is None:
        raise ValueError("object has no __text section or symbol table")
    symbol_offset, symbol_count, strings_offset, _ = symbols
    for index in range(symbol_count):
        string_index, symbol_type, _, _, value = struct.unpack_from(
            "<IBBHQ", blob, symbol_offset + index * 16
        )
        name = blob[strings_offset + string_index:].split(b"\0", 1)[0]
        if name == b"_start" and symbol_type & 1:
            return text, value - text_address
    raise ValueError("object has no global _start symbol")


def segment_command(name: str, address: int, memory_size: int, file_offset: int,
                    file_size: int, protection: int, sections: bytes = b"") -> bytes:
    section_count = len(sections) // 80
    return struct.pack(
        "<II16sQQQQIIII",
        LC_SEGMENT_64,
        72 + len(sections),
        name.encode("ascii"),
        address,
        memory_size,
        file_offset,
        file_size,
        protection,
        protection,
        section_count,
        0,
    ) + sections


def code_signature(image: bytes) -> bytes:
    page_size = 0x1000
    hashes = b"".join(
        hashlib.sha256(image[offset:offset + page_size]).digest()
        for offset in range(0, SEGMENT_SIZE, page_size)
    )
    header_size = 88
    identifier_offset = header_size
    hash_offset = identifier_offset + len(IDENTIFIER)
    directory_size = hash_offset + len(hashes)
    directory = struct.pack(
        ">9I4BI",
        0xFADE0C02,
        directory_size,
        0x20400,
        0x2,
        hash_offset,
        identifier_offset,
        0,
        len(hashes) // 32,
        SEGMENT_SIZE,
        32,
        2,
        0,
        12,
        0,
    )
    directory += struct.pack(">IIIQQQQ", 0, 0, 0, 0, 0, SEGMENT_SIZE, 1)
    directory += IDENTIFIER + hashes
    superblob_header = 20
    return (
        struct.pack(">III", 0xFADE0CC0, superblob_header + len(directory), 1)
        + struct.pack(">II", 0, superblob_header)
        + directory
    )


def verify_executable(image: bytes) -> None:
    """Reject malformed output or a CodeDirectory that does not cover __TEXT."""
    if len(image) <= SEGMENT_SIZE:
        raise ValueError("executable has no embedded code signature")
    magic, cpu, _, filetype, commands, _, flags, _ = struct.unpack_from("<8I", image)
    if (magic, cpu, filetype) != (MH_MAGIC_64, CPU_TYPE_ARM64, MH_EXECUTE):
        raise ValueError("output is not an ARM64 Mach-O executable")
    if not flags & MH_NOUNDEFS:
        raise ValueError("output does not declare MH_NOUNDEFS")
    offset = 32
    signature = None
    for _ in range(commands):
        command, command_size = struct.unpack_from("<II", image, offset)
        if command == LC_CODE_SIGNATURE:
            signature = struct.unpack_from("<II", image, offset + 8)
        offset += command_size
    if signature is None:
        raise ValueError("output has no LC_CODE_SIGNATURE")
    signature_offset, signature_size = signature
    if signature_offset != SEGMENT_SIZE or signature_offset + signature_size != len(image):
        raise ValueError("code signature has an unexpected file range")
    blob = image[signature_offset:]
    magic, length, count = struct.unpack_from(">III", blob)
    if magic != 0xFADE0CC0 or length != len(blob) or count != 1:
        raise ValueError("invalid embedded signature SuperBlob")
    slot_type, directory_offset = struct.unpack_from(">II", blob, 12)
    if slot_type != 0:
        raise ValueError("embedded signature does not contain a CodeDirectory")
    directory = blob[directory_offset:]
    values = struct.unpack_from(">9I4BI", directory)
    (directory_magic, directory_size, _, _, hash_offset, identifier_offset, special_slots,
     code_slots, code_limit, hash_size, hash_type, _, page_shift, _) = values
    if directory_magic != 0xFADE0C02 or directory_size != len(directory):
        raise ValueError("invalid CodeDirectory")
    if (special_slots, code_limit, hash_size, hash_type, page_shift) != (
        0, SEGMENT_SIZE, 32, 2, 12
    ):
        raise ValueError("unsupported CodeDirectory parameters")
    identifier = directory[identifier_offset:].split(b"\0", 1)[0] + b"\0"
    if identifier != IDENTIFIER:
        raise ValueError("unexpected CodeDirectory identifier")
    page_size = 1 << page_shift
    expected_slots = (code_limit + page_size - 1) // page_size
    if code_slots != expected_slots:
        raise ValueError("CodeDirectory has an unexpected number of code slots")
    for index in range(code_slots):
        start = index * page_size
        expected = hashlib.sha256(image[start:min(start + page_size, code_limit)]).digest()
        actual_start = hash_offset + index * hash_size
        actual = directory[actual_start:actual_start + hash_size]
        if actual != expected:
            raise ValueError(f"CodeDirectory hash mismatch for page {index}")


def build(object_blob: bytes) -> bytes:
    text, entry_offset = object_text(object_blob)
    if CODE_OFFSET + len(text) > SEGMENT_SIZE:
        raise ValueError("init code does not fit in one 16 KiB text segment")
    section = struct.pack(
        "<16s16sQQIIIIIIII",
        b"__text",
        b"__TEXT",
        BASE + CODE_OFFSET,
        len(text),
        CODE_OFFSET,
        2,
        0,
        0,
        TEXT_ATTRIBUTES,
        0,
        0,
        0,
    )
    provisional = bytes(SEGMENT_SIZE)
    signature_size = len(code_signature(provisional))
    thread_state = [0] * 33
    thread_state[32] = BASE + CODE_OFFSET + entry_offset
    thread = struct.pack(
        "<IIII33QII",
        LC_UNIXTHREAD,
        16 + ARM_THREAD_STATE64_COUNT * 4,
        ARM_THREAD_STATE64,
        ARM_THREAD_STATE64_COUNT,
        *thread_state,
        0,
        0,
    )
    commands = b"".join(
        (
            segment_command("__PAGEZERO", 0, BASE, 0, 0, 0),
            segment_command("__TEXT", BASE, SEGMENT_SIZE, 0, SEGMENT_SIZE,
                            VM_PROT_READ | VM_PROT_EXECUTE, section),
            segment_command("__LINKEDIT", BASE + SEGMENT_SIZE, SEGMENT_SIZE,
                            SEGMENT_SIZE, signature_size, VM_PROT_READ),
            thread,
            struct.pack("<4I", LC_CODE_SIGNATURE, 16, SEGMENT_SIZE, signature_size),
        )
    )
    header = struct.pack(
        "<8I", MH_MAGIC_64, CPU_TYPE_ARM64, 0, MH_EXECUTE, 5, len(commands), MH_NOUNDEFS, 0
    )
    if len(header) + len(commands) > CODE_OFFSET:
        raise ValueError("Mach-O load commands overlap init code")
    image = bytearray(SEGMENT_SIZE)
    image[:len(header) + len(commands)] = header + commands
    image[CODE_OFFSET:CODE_OFFSET + len(text)] = text
    result = bytes(image) + code_signature(bytes(image))
    verify_executable(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("object", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = build(args.object.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"{args.output}: {len(result)} bytes")
    print(f"sha256={hashlib.sha256(result).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
