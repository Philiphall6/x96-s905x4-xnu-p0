#!/usr/bin/env python3
"""Lay out an X96SC2 Mach-O kernel, ADT and optional mockfs init for QEMU."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


MH_MAGIC_64 = 0xFEEDFACF
CPU_TYPE_ARM64 = 0x0100000C
MH_EXECUTE = 2
LC_SEGMENT_64 = 0x19
LC_UNIXTHREAD = 0x5
LC_DYLD_CHAINED_FIXUPS = 0x80000034
PAGE = 0x4000
BLOCK = 0x2000000
PHYS_BASE = 0x40000000
MEM_SIZE = 0x40000000
QEMU_LOAD_ADDRESS = 0x41000000
STUB_ADDRESS = 0x40200000
RAMDISK_ADDRESS = 0x44000000
FB_ADDRESS = 0x70000000
FB_WIDTH = 1920
FB_HEIGHT = 1080
FB_STRIDE = FB_WIDTH * 4
COMMAND_LINE_SIZE = 608


def align(value: int, amount: int = PAGE) -> int:
    return (value + amount - 1) & -amount


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def adt_ramdisk(blob: bytes) -> tuple[int, int] | None:
    """Return /chosen/memory-map/RAMDisk from a raw Apple Device Tree."""
    def parse_node(offset: int, path: tuple[str, ...]) -> tuple[int, tuple[int, int] | None]:
        if offset + 8 > len(blob):
            raise ValueError("truncated ADT node")
        properties, children = struct.unpack_from("<II", blob, offset)
        offset += 8
        name = "?"
        ramdisk = None
        ramdisk_value = None
        for _ in range(properties):
            if offset + 36 > len(blob):
                raise ValueError("truncated ADT property")
            property_name = blob[offset:offset + 32].split(b"\0", 1)[0].decode("ascii")
            encoded_size = struct.unpack_from("<I", blob, offset + 32)[0]
            size = encoded_size & 0x7FFFFFFF
            value_start = offset + 36
            value_end = value_start + size
            if value_end > len(blob):
                raise ValueError("ADT property extends beyond the input")
            value = blob[value_start:value_end]
            if property_name == "name":
                name = value.split(b"\0", 1)[0].decode("ascii")
            if property_name == "RAMDisk":
                if size != 16:
                    raise ValueError("ADT RAMDisk property has an invalid size")
                ramdisk_value = struct.unpack("<QQ", value)
            offset = value_start + ((size + 3) & ~3)
        node_path = path + (name,)
        if node_path == ("device-tree", "chosen", "memory-map"):
            ramdisk = ramdisk_value
        elif ramdisk_value is not None:
            raise ValueError("ADT RAMDisk property is outside /chosen/memory-map")
        for _ in range(children):
            offset, child_ramdisk = parse_node(offset, node_path)
            if child_ramdisk is not None:
                if ramdisk is not None:
                    raise ValueError("ADT contains multiple RAMDisk properties")
                ramdisk = child_ramdisk
        return offset, ramdisk

    consumed, ramdisk = parse_node(0, ())
    if consumed != len(blob):
        raise ValueError("ADT has trailing data")
    return ramdisk


def parse_kernel(blob: bytes) -> dict:
    magic, cpu, _, filetype, commands, _, _, _ = struct.unpack_from("<8I", blob)
    if (magic, cpu, filetype) != (MH_MAGIC_64, CPU_TYPE_ARM64, MH_EXECUTE):
        raise ValueError("kernel is not an ARM64 Mach-O executable")
    segments = []
    entry = None
    offset = 32
    for _ in range(commands):
        command, command_size = struct.unpack_from("<II", blob, offset)
        if command == LC_SEGMENT_64:
            name = blob[offset + 8:offset + 24].split(b"\0", 1)[0].decode("ascii")
            address, memory_size, file_offset, file_size = struct.unpack_from(
                "<4Q", blob, offset + 24
            )
            if memory_size:
                if file_offset + file_size > len(blob):
                    raise ValueError(f"segment {name} lies outside the kernel file")
                segments.append((name, address, memory_size, file_offset, file_size))
        elif command == LC_UNIXTHREAD:
            entry = struct.unpack_from("<Q", blob, offset + 16 + 32 * 8)[0]
        elif command == LC_DYLD_CHAINED_FIXUPS:
            _, size = struct.unpack_from("<II", blob, offset + 8)
            if size:
                raise ValueError("kernel contains unresolved chained fixups")
        offset += command_size
    if not segments or segments[0][0] != "__TEXT" or segments[0][3] != 0 or entry is None:
        raise ValueError("kernel has an unsupported Mach-O layout")
    virtual_base = segments[0][1] & -BLOCK
    return {"segments": segments, "entry": entry, "virtual_base": virtual_base}


def boot_args(virtual_base: int, top: int, adt_address: int, adt_size: int,
              command_line: str) -> bytes:
    encoded = command_line.encode("ascii")
    if len(encoded) >= COMMAND_LINE_SIZE:
        raise ValueError("kernel command line is too long")
    command = encoded + bytes(COMMAND_LINE_SIZE - len(encoded))
    delta = PHYS_BASE - virtual_base
    result = struct.pack(
        "<HH4x4Q6QI4xQI",
        2,
        2,
        virtual_base,
        PHYS_BASE,
        MEM_SIZE,
        top,
        FB_ADDRESS,
        1,
        FB_STRIDE,
        FB_WIDTH,
        FB_HEIGHT,
        32,
        0,
        adt_address - delta,
        adt_size,
    )
    result += command + bytes(4) + struct.pack("<QQ", 0, MEM_SIZE)
    if len(result) != 736:
        raise AssertionError("unexpected boot_args layout")
    return result


def make_stub(boot_args_address: int, entry_address: int) -> bytes:
    # ldr x0, literal; ldr x1, literal; br x1; nop; .quad values
    return struct.pack(
        "<4I2Q", 0x58000080, 0x580000A1, 0xD61F0020, 0xD503201F,
        boot_args_address, entry_address
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel", type=Path)
    parser.add_argument("adt", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ramdisk", type=Path)
    parser.add_argument(
        "--cmdline",
        default="debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress wdt=-1 rd=md0",
    )
    args = parser.parse_args()
    kernel = args.kernel.read_bytes()
    adt = args.adt.read_bytes()
    parsed = parse_kernel(kernel)
    virtual_base = parsed["virtual_base"]
    delta = PHYS_BASE - virtual_base
    kernel_end = align(max(address + memory_size + delta for _, address, memory_size, _, _
                           in parsed["segments"]))
    cursor = kernel_end
    ramdisk = None
    if args.ramdisk:
        ramdisk_blob = args.ramdisk.read_bytes()
        ramdisk_size = align(len(ramdisk_blob))
        if kernel_end > RAMDISK_ADDRESS:
            raise ValueError("kernel grew into the fixed QEMU RAMDisk reservation")
        if adt_ramdisk(adt) != (RAMDISK_ADDRESS, ramdisk_size):
            raise ValueError("ADT does not describe the exact requested RAMDisk range")
        cursor = RAMDISK_ADDRESS + ramdisk_size
        ramdisk = (ramdisk_blob, ramdisk_size)
    adt_address = align(cursor)
    boot_args_address = align(adt_address + len(adt))
    top = boot_args_address + PAGE
    if top > PHYS_BASE + MEM_SIZE:
        raise ValueError("prepared image exceeds the XNU managed RAM range")
    image = bytearray(top - PHYS_BASE)
    for name, address, memory_size, file_offset, file_size in parsed["segments"]:
        destination = address + delta - PHYS_BASE
        if destination < 0 or destination + memory_size > len(image):
            raise ValueError(f"segment {name} lies outside prepared RAM")
        image[destination:destination + file_size] = kernel[file_offset:file_offset + file_size]
    if ramdisk:
        image[RAMDISK_ADDRESS - PHYS_BASE:RAMDISK_ADDRESS - PHYS_BASE + len(ramdisk[0])] = ramdisk[0]
    image[adt_address - PHYS_BASE:adt_address - PHYS_BASE + len(adt)] = adt
    args_blob = boot_args(virtual_base, top, adt_address, len(adt), args.cmdline)
    image[boot_args_address - PHYS_BASE:boot_args_address - PHYS_BASE + len(args_blob)] = args_blob
    if QEMU_LOAD_ADDRESS < PHYS_BASE or QEMU_LOAD_ADDRESS >= top:
        raise ValueError("invalid QEMU load slice")
    load_blob = bytes(image[QEMU_LOAD_ADDRESS - PHYS_BASE:])
    entry_address = parsed["entry"] + delta
    stub_blob = make_stub(boot_args_address, entry_address)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ram-load.bin").write_bytes(load_blob)
    (args.output / "stub.bin").write_bytes(stub_blob)
    layout = {
        "kernel": str(args.kernel.resolve()),
        "kernel_sha256": sha256(kernel),
        "adt_sha256": sha256(adt),
        "ramdisk_sha256": sha256(ramdisk[0]) if ramdisk else None,
        "virtual_base": virtual_base,
        "physical_base": PHYS_BASE,
        "managed_memory_size": MEM_SIZE,
        "qemu_memory_size": 3 * 1024**3,
        "load_address": QEMU_LOAD_ADDRESS,
        "stub_address": STUB_ADDRESS,
        "entry_address": entry_address,
        "boot_args_address": boot_args_address,
        "adt_address": adt_address,
        "ramdisk_address": RAMDISK_ADDRESS if ramdisk else None,
        "ramdisk_size": ramdisk[1] if ramdisk else None,
        "top_of_kernel_data": top,
        "framebuffer_address": FB_ADDRESS,
        "early_framebuffer_address": 0xDFF80000,
        "framebuffer_size": FB_STRIDE * FB_HEIGHT,
        "ram_load_sha256": sha256(load_blob),
        "stub_sha256": sha256(stub_blob),
    }
    (args.output / "layout.json").write_text(json.dumps(layout, indent=2) + "\n")
    print(json.dumps(layout, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
