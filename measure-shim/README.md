# X96 S905X4 measurement shim — not flashable

This freestanding AArch64 Linux `Image` only reads architectural registers and
the FDT pointer supplied by U-Boot. It never accesses eMMC, partitions,
Ethernet, USB, clocks or GPIOs.

Outputs, using firmware state without reconfiguring hardware:

- Meson UART at provisional `0xfe07a000`;
- the U-Boot logo framebuffer at provisional `0xdf800000`;
- `CurrentEL`, `MPIDR_EL1`, `CNTFRQ_EL0`, `CNTPCT_EL0`, `SCTLR`, `HCR_EL2`;
- FDT pointer, magic and total size.

Safety status: **compiled engineering probe only**. It is not an Android boot
image and must not be loaded through USB Burn Tool or written to any partition.
Before a hardware run it needs a reviewed, RAM-only U-Boot/SD invocation and a
known recovery path. The display and UART addresses are still provisional.

The probe refuses all MMIO and FDT access unless it entered at EL1/EL2 with
both the MMU and data cache disabled. This is a fail-closed check: an invalid
entry state produces no output and remains in the local `WFE` loop.

The 64 KiB private stack is included in the raw file, and the build verifies
that the file length exactly matches the `image_size` advertised by the arm64
Linux Image header. The ELF also must contain no runtime relocations.

`build-qemu.sh` compiles the same register/FDT logic with only two deliberate
test substitutions: QEMU's PL011 UART replaces the Meson UART and framebuffer
writes are disabled. `run-qemu.sh` directly boots the resulting raw arm64
`Image` and requires a valid live FDT report before accepting the test.
