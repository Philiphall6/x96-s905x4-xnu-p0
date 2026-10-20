#!/usr/bin/env python3
"""Generate a minimal Apple Device Tree for XNU bring-up on X96/S905X4.

This is a kernel-only engineering tree. It deliberately contains no Apple
device identity, activation state, account data, SEP emulation or DRM data.

The serializer is imported from the locally pinned ios-sweet reference. The
hardware values are taken from the known-good SlimBOX device tree; provisional
values are kept out of physical testing until measured from U-Boot/the shim.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import struct
import sys


HERE = Path(__file__).resolve().parent
REFERENCE_TOOLS = HERE.parent / "ios-sweet-reference" / "tools"
sys.path.insert(0, str(REFERENCE_TOOLS))

try:
    import adt  # type: ignore
except ImportError as exc:
    raise SystemExit(
        f"missing ADT serializer in {REFERENCE_TOOLS}; fetch ios-sweet-reference first"
    ) from exc


PHYS_BASE = 0x40000000
MEM_SIZE = 0x20000000
SOC_BASE = 0xFE000000

GICD = 0xFFF01000
GICD_SIZE = 0x1000
GICC = 0xFFF02000
GICC_SIZE = 0x100
VTIMER_INTID = 27
TIMEBASE = 24_000_000

FB = 0xDF800000
FB_SIZE = 0x00800000
FB_WIDTH = 1920
FB_HEIGHT = 1080
FB_STRIDE = FB_WIDTH * 4

UART = 0xFE07A000
UART_SIZE = 0x18
EMMC = 0xFE08C000
EMMC_SIZE = 0x800
ETHERNET = 0xFDC00000
ETHERNET_SIZE = 0x10000

QEMU_PHYS_BASE = 0x40000000
QEMU_MEM_SIZE = 0x40000000
QEMU_GICD = 0x08000000
QEMU_GICC = 0x08010000
QEMU_TIMEBASE = 62_500_000
QEMU_FB = 0x70000000
QEMU_UART = 0x09000000
QEMU_UART_SIZE = 0x1000


def u32(*values: int) -> bytes:
    return struct.pack(f"<{len(values)}I", *values)


def u64(*values: int) -> bytes:
    return struct.pack(f"<{len(values)}Q", *values)


def cstr(value: str) -> bytes:
    return value.encode("ascii") + b"\0"


def node(name: str, props=(), children=()):
    result = adt.Node()
    result.props = [("name", 0, cstr(name))] + [(key, 0, value) for key, value in props]
    result.children = list(children)
    return result


def build(*, qemu: bool, seed: bytes):
    phandle_values = iter(range(1, 1000))

    def phandle():
        return "AAPL,phandle", u32(next(phandle_values))

    if qemu:
        phys_base, mem_size = QEMU_PHYS_BASE, QEMU_MEM_SIZE
        gicd, gicc, timebase, framebuffer, io_base, uart_base, uart_size, uart_compat = (
            QEMU_GICD,
            QEMU_GICC,
            QEMU_TIMEBASE,
            QEMU_FB,
            QEMU_GICD,
            QEMU_UART,
            QEMU_UART_SIZE,
            "arm,pl011",
        )
    else:
        phys_base, mem_size = PHYS_BASE, MEM_SIZE
        gicd, gicc, timebase, framebuffer, io_base, uart_base, uart_size, uart_compat = (
            GICD,
            GICC,
            TIMEBASE,
            FB,
            SOC_BASE,
            UART,
            UART_SIZE,
            "amlogic,meson-uart",
        )

    chosen = node(
        "chosen",
        [
            phandle(),
            ("dram-base", u64(phys_base)),
            ("dram-size", u64(mem_size)),
            ("random-seed", seed),
            ("debug-enabled", u32(1)),
            ("firmware-version", cstr("x96-xnu-shim-p0")),
            ("system-firmware-version", cstr("x96-xnu-shim-p0")),
        ],
        [node("memory-map", [phandle()])],
    )

    # P0 is deliberately single-core.  Publishing the three stopped cores
    # here makes XNU include them in its topology before PSCI secondary-start
    # support exists, so the CPU driver correctly refuses to continue.
    cpus = []
    for core in range(1):
        cpus.append(
            node(
                f"cpu{core}",
                [
                    phandle(),
                    ("device_type", cstr("cpu")),
                    ("compatible", cstr("arm,cortex-a55") + cstr("ARM,v8")),
                    ("reg", u32(core)),
                    ("cpu-id", u32(core)),
                    ("cluster-id", u32(0)),
                    ("cluster-core-id", u32(core)),
                    ("state", cstr("running" if core == 0 else "stopped")),
                    ("timebase-frequency", u32(timebase)),
                    ("fixed-frequency", u32(timebase)),
                ],
            )
        )
    cpu_root = node(
        "cpus",
        [phandle(), ("#address-cells", u32(1)), ("#size-cells", u32(0))],
        cpus,
    )

    gic_props = [
        phandle(),
        ("compatible", cstr("arm,gic-400") + cstr("arm,cortex-a15-gic")),
        ("interrupt-controller", b""),
        ("gic-version", u32(2)),
        ("virtual-timer-intid", u32(VTIMER_INTID)),
        ("reg", u64(gicd - io_base, GICD_SIZE, gicc - io_base, GICC_SIZE)),
    ]
    if qemu:
        # QEMU virt GICv2 has no security extensions: all IRQs use its one
        # primary group.  Physical X96 instead runs XNU in NS Group 1.
        gic_props.append(("x96,single-security", u32(1)))
    gic = node("gic", gic_props)
    arm_io = node(
        "arm-io",
        [
            phandle(),
            ("device_type", cstr("x96-io")),
            ("compatible", cstr("x96-io") + cstr("arm-io")),
            ("#address-cells", u32(2)),
            ("#size-cells", u32(2)),
            ("ranges", u64(0, io_base, 0x02000000)),
        ],
        [gic],
    )

    fbcon = node(
        "x96-fbcon",
        [
            phandle(),
            ("reg", u64(framebuffer, FB_SIZE)),
            ("width", u32(FB_WIDTH)),
            ("height", u32(FB_HEIGHT)),
            ("stride", u32(FB_STRIDE)),
            ("depth", u32(32)),
        ],
    )
    uart = node(
        "x96-uart",
        [phandle(), ("reg", u64(uart_base, uart_size)), ("compatible", cstr(uart_compat))],
    )
    emmc = node(
        "x96-emmc",
        [phandle(), ("reg", u64(EMMC, EMMC_SIZE)), ("compatible", cstr("amlogic,meson-axg-mmc"))],
    )
    ethernet = node(
        "x96-ethernet",
        [
            phandle(),
            ("reg", u64(ETHERNET, ETHERNET_SIZE)),
            ("compatible", cstr("snps,dwmac-3.70a")),
            ("interrupt", u32(74)),
        ],
    )
    defaults = node("defaults", [phandle(), ("no-effaceable-storage", u32(1))])

    return node(
        "device-tree",
        [
            phandle(),
            ("compatible", cstr("x96,max-plus-ultra") + cstr("amlogic,sc2") + cstr("ARM,v8")),
            ("model", cstr("X96 Max+ Ultra")),
            ("target-type", cstr("X96SC2")),
            ("manufacturer", cstr("Amlogic reference board")),
            ("#address-cells", u32(2)),
            ("#size-cells", u32(2)),
        ],
        [chosen, defaults, cpu_root, arm_io, fbcon, uart, emmc, ethernet],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--qemu", action="store_true")
    parser.add_argument("--dump", action="store_true")
    parser.add_argument(
        "--seed",
        default="x96-xnu-p0",
        help="deterministic engineering seed label",
    )
    args = parser.parse_args()

    seed = hashlib.sha512(args.seed.encode("utf-8")).digest()
    tree = build(qemu=args.qemu, seed=seed)
    blob = adt.serialize(tree)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(blob)

    parsed, consumed = adt.parse(blob)
    if consumed != len(blob):
        raise SystemExit(f"ADT validation consumed {consumed} of {len(blob)} bytes")
    if args.dump:
        adt.dump(parsed)
    print(f"{args.output}: {len(blob)} bytes")
    print(f"sha256={hashlib.sha256(blob).hexdigest()}")
    print(f"mode={'qemu-gicv2' if args.qemu else 'x96-hardware-provisional'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
