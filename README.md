# XNU/tvOS bring-up for X96 Max+ Ultra (Amlogic S905X4)

This workspace is an experimental, non-destructive bring-up project. It does
not modify the stable Android image and must not be flashed to eMMC during the
early milestones.

## Scope of the first milestone

1. Describe the real X96 hardware from the known-good SlimBOX device tree.
2. Generate a minimal Apple Device Tree (ADT) for an open-source XNU kernel.
3. Add an Amlogic SC2 machine target and GICv2 interrupt path to XNU 8796.
4. Boot the kernel under QEMU with a test ramdisk.
5. Only after QEMU validation, package a temporary SD/USB test image that
   leaves the Android bootloader and partitions untouched.

No Apple account, activation, DRM, FairPlay, SEP or signing bypass is part of
this milestone. The target is a kernel console, not a usable tvOS system.

## Baselines

- Hardware DT: `slimboxtv-4g.dts` from the working Android 11 firmware.
- Reference port: `dipa-studio/ios-sweet`, commit
  `11da58bd050672960c0a83b5bef2176047eea479`.
- Initial XNU generation: 8796 (iOS/tvOS 16 generation).

The reference repository currently has no license file. It is kept as a local
read-only engineering reference; no derived source will be redistributed
without explicit licensing permission.

## Safety gates

- QEMU first.
- Hardware payload must use a temporary boot path (SD/USB or an equivalent
  RAM-only loader).
- Never overwrite `bootloader`, `boot_a`, `vendor_boot_a`, `vbmeta*`, DTB or
  Android data during bring-up.
- Confirm the execution level and the live RAM map before jumping into XNU.
- Preserve the known-good Android/Burn Tool recovery image.

## Current state

- Reference project pinned locally.
- S905X4 hardware profile recorded in `hardware/x96-s905x4.json`.
- Minimal single-core ADT generator implemented and round-trip validated in
  `tools/mkadt_x96.py`.
- XNU 8796 target `X96SC2` added on local branch `x96-s905x4`, commit
  `1dcd589464c104b63c131128359e52a000f179cf`, followed by UART console commit
  `91851b1261ba7b78366bd0909322953dc892f33e`.
- The S905X4 has four Cortex-A55 cores. P0 intentionally starts CPU0 only;
  P1 will enable all four through PSCI/SMP after the single-core interrupt and
  timer path has booted reliably.
- GIC-400/GICv2 timer, EOI and SGI paths implemented for XNU. QEMU's
  single-security GIC mode and the X96 non-secure Group 1 mode are selected
  independently by the ADT.
- Early framebuffer constants are board-specific. X96 values remain
  provisional until read back from the live boot environment.
- Normal XNU logging can use the firmware-configured Meson UART on hardware
  and PL011 under QEMU, selected exclusively by each ADT.
- `tools/verify_p0.py` cross-checks both ADTs, the hardware profile and the
  serial backend without requiring access to the X96.
- Local QEMU 8.2.2 installed without changing the host system.
- Standalone EL2-to-EL1/GICv2/timer preflight passes on Cortex-A55 QEMU with
  exit code 0; see `preflight-qemu/`.
- A standalone S905X4 measurement shim now builds as a self-contained arm64
  Linux `Image`; see `measure-shim/`. It has not been run on the box and is
  deliberately not an Android/Burn Tool image.
- The probe's register/FDT path also boots as a raw arm64 Image under QEMU,
  receives the live FDT in `x0` and reports `MEASUREMENT COMPLETE`.
- `fastboot-ram-probe/` wraps that probe in a reproducible Android boot v3
  container for a future RAM-only `fastboot boot`. Its kernel round-trip and
  unsigned AVB hash footer pass; no hardware command has been sent.
- Full XNU compilation now succeeds on GitHub Actions with the Intel macOS 15
  runner and Xcode 16.2. Run `39470717273` produced the ARM64 Mach-O executable
  `kernel.development.x96sc2` (16,432,688 bytes). This is a development kernel,
  not a bootable Android image and not a Burn Tool image.
- The next gate is to package only the test dependencies needed to start this
  compiled kernel under QEMU with the QEMU ADT. No X96 hardware boot is
  authorized by this compilation result alone.
- The real Amlogic Android-boot shim is not implemented yet. No hardware boot
  will be attempted before live RAM, `CNTFRQ_EL0` and framebuffer measurements.

## Reproducible P0 checks

```sh
./preflight-qemu/build.sh
./preflight-qemu/run.sh
./measure-shim/build.sh
./measure-shim/build-qemu.sh
./measure-shim/run-qemu.sh
./fastboot-ram-probe/build.sh
python3 tools/verify_p0.py
python3 tools/mkadt_x96.py out/x96-s905x4-qemu.adt --qemu --dump
python3 tools/mkadt_x96.py out/x96-s905x4-hardware-provisional.adt --dump
```

Expected QEMU result:

```text
X96 P0 preflight CurrentEL=0x0000000000000008
EL1 entered
CNTFRQ_EL0=0x0000000003b9aca0
GICC_IAR=0x000000000000001b
PASS: GICv2 virtual timer INTID 27
```
