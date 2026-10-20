#!/usr/bin/env python3
"""Cross-check the generated P0 ADTs against the X96 profile and XNU source."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parent.parent
REFERENCE_TOOLS = ROOT / "ios-sweet-reference" / "tools"
sys.path.insert(0, str(REFERENCE_TOOLS))
import adt  # type: ignore  # noqa: E402


def parse(path: Path):
    blob = path.read_bytes()
    tree, consumed = adt.parse(blob)
    assert consumed == len(blob), (path, consumed, len(blob))
    return tree


def child(node, name: str):
    matches = [item for item in node.children if item.name == name]
    assert len(matches) == 1, (node.name, name, len(matches))
    return matches[0]


def u32(value: bytes) -> int:
    assert len(value) == 4
    return struct.unpack("<I", value)[0]


def u64s(value: bytes) -> tuple[int, ...]:
    assert len(value) % 8 == 0
    return struct.unpack(f"<{len(value) // 8}Q", value)


def cstr(value: bytes) -> str:
    return value.split(b"\0", 1)[0].decode("ascii")


def check_common(tree) -> None:
    assert tree.name == "device-tree"
    assert cstr(tree.prop("target-type")) == "X96SC2"
    cpus = child(tree, "cpus")
    assert [item.name for item in cpus.children] == ["cpu0"]
    cpu0 = child(cpus, "cpu0")
    assert cstr(cpu0.prop("compatible")) == "arm,cortex-a55"
    assert u32(cpu0.prop("cpu-id")) == 0
    gic = child(child(tree, "arm-io"), "gic")
    assert u32(gic.prop("gic-version")) == 2
    assert u32(gic.prop("virtual-timer-intid")) == 27


def main() -> int:
    profile = json.loads((ROOT / "hardware/x96-s905x4.json").read_text())
    hardware = parse(ROOT / "out/x96-s905x4-hardware-provisional.adt")
    qemu = parse(ROOT / "out/x96-s905x4-qemu.adt")
    check_common(hardware)
    check_common(qemu)

    hw_uart = child(hardware, "x96-uart")
    assert u64s(hw_uart.prop("reg")) == (
        int(profile["uart"]["address"], 16),
        int(profile["uart"]["size"], 16),
    )
    assert cstr(hw_uart.prop("compatible")) == profile["uart"]["compatible"]

    qemu_uart = child(qemu, "x96-uart")
    assert u64s(qemu_uart.prop("reg")) == (0x09000000, 0x1000)
    assert cstr(qemu_uart.prop("compatible")) == "arm,pl011"

    hw_gic = child(child(hardware, "arm-io"), "gic")
    qemu_gic = child(child(qemu, "arm-io"), "gic")
    assert hw_gic.prop("x96,single-security") is None
    assert u32(qemu_gic.prop("x96,single-security")) == 1

    fb = child(hardware, "x96-fbcon")
    assert u64s(fb.prop("reg")) == (
        int(profile["framebuffer"]["address"], 16),
        int(profile["framebuffer"]["reserved_size"], 16),
    )
    assert u32(fb.prop("width")) == profile["framebuffer"]["width"]
    assert u32(fb.prop("height")) == profile["framebuffer"]["height"]
    assert u32(fb.prop("stride")) == profile["framebuffer"]["stride_bytes"]

    serial_source = (ROOT / "xnu-8796.141.3/pexpert/arm/pe_serial.c").read_text()
    for required in (
        'SecureDTFindEntry("name", "x96-uart"',
        '"amlogic,meson-uart"',
        '"arm,pl011"',
        "MESON_UART_TX_FULL",
        "PL011_UART_TX_FULL",
        "x96_uart_probe();",
    ):
        assert required in serial_source, required

    print("PASS: P0 ADT/source cross-check")
    print("hardware UART: amlogic,meson-uart @ 0xfe07a000")
    print("QEMU UART: arm,pl011 @ 0x09000000")
    print("CPU0-only, GICv2 and virtual timer INTID 27 confirmed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
