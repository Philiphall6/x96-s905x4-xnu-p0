#!/usr/bin/env python3
"""Run one prepared X96SC2 XNU image on QEMU virt/GICv2 and capture evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time


def qmp_call(stream, execute: str, arguments=None):
    request = {"execute": execute}
    if arguments is not None:
        request["arguments"] = arguments
    stream.write(json.dumps(request) + "\n")
    stream.flush()
    while True:
        response = json.loads(stream.readline())
        if "return" in response or "error" in response:
            if "error" in response:
                raise RuntimeError(response["error"])
            return response["return"]


def capture(monitor: Path, output: Path, layout: dict) -> None:
    connection = socket.socket(socket.AF_UNIX)
    connection.connect(str(monitor))
    stream = connection.makefile("rw")
    json.loads(stream.readline())
    qmp_call(stream, "qmp_capabilities")
    qmp_call(stream, "stop")
    registers = qmp_call(
        stream, "human-monitor-command", {"command-line": "info registers"}
    )
    (output / "registers.txt").write_text(registers, encoding="utf-8")
    registers_all = qmp_call(
        stream, "human-monitor-command", {"command-line": "info registers -a"}
    )
    (output / "registers-all.txt").write_text(registers_all, encoding="utf-8")
    for name, address, size in (
        ("gic-distributor.raw", 0x08000000, 0x1000),
        ("gic-cpu-interface.raw", 0x08010000, 0x1000),
    ):
        qmp_call(
            stream,
            "pmemsave",
            {"val": address, "size": size, "filename": str(output / name)},
        )
    for name, address in (
        ("framebuffer.raw", layout["framebuffer_address"]),
        ("early-framebuffer.raw", layout["early_framebuffer_address"]),
    ):
        qmp_call(
            stream,
            "pmemsave",
            {"val": address, "size": layout["framebuffer_size"], "filename": str(output / name)},
        )
    stream.close()
    connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=float, default=30)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"refusing to overwrite existing output directory: {args.output}")
    args.output.mkdir(parents=True)
    layout = json.loads((args.prepared / "layout.json").read_text())
    project = Path(__file__).resolve().parent.parent
    qemu_root = project / "local-tools/qemu"
    qemu = qemu_root / "usr/bin/qemu-system-aarch64"
    monitor = args.output / "monitor.sock"
    command = [
        str(qemu), "-L", str(qemu_root / "usr/share/qemu"),
        "-M", "virt,gic-version=2", "-cpu", "cortex-a55", "-smp", "1", "-m", "3G",
        "-nographic", "-nodefaults", "-serial", f"file:{args.output / 'serial.txt'}",
        "-qmp", f"unix:{monitor},server=on,wait=off",
        "-d", "guest_errors,unimp", "-D", str(args.output / "qemu.log"), "-no-reboot",
        "-device", f"loader,file={args.prepared / 'ram-load.bin'},addr={layout['load_address']:#x},force-raw=on",
        "-device", f"loader,file={args.prepared / 'stub.bin'},addr={layout['stub_address']:#x},force-raw=on",
        "-device", f"loader,addr={layout['stub_address']:#x},cpu-num=0",
    ]
    environment = os.environ.copy()
    libraries = [qemu_root / "usr/lib/x86_64-linux-gnu", qemu_root / "lib/x86_64-linux-gnu"]
    environment["LD_LIBRARY_PATH"] = ":".join(map(str, libraries))
    with (args.output / "qemu.stderr.txt").open("wb") as errors:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=errors,
                                   stderr=subprocess.STDOUT, env=environment)
        deadline = time.monotonic() + 5
        while not monitor.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if not monitor.exists() or process.poll() is not None:
            raise RuntimeError("QEMU exited before its monitor became available")
        run_deadline = time.monotonic() + args.seconds
        while process.poll() is None and time.monotonic() < run_deadline:
            time.sleep(0.2)
        if process.poll() is None:
            capture(monitor, args.output, layout)
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    serial = (args.output / "serial.txt").read_text(errors="replace")
    result = {
        "qemu_returncode": process.returncode,
        "seconds": args.seconds,
        "serial_bytes": len(serial.encode()),
        "panic_observed": "panic(cpu " in serial or "EARLY PANIC" in serial,
        "userspace_init_observed": "X96SC2 userspace: init running as PID 1" in serial,
        "userspace_heartbeat_observed": "X96SC2 init: still alive" in serial,
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 2 if result["panic_observed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
