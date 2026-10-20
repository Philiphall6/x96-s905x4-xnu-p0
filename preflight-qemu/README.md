# X96 P0 architecture preflight

This standalone image is a non-destructive QEMU-only test. It validates the
architecture shared by the eventual X96 shim/XNU path:

- entry at EL2 and controlled drop to AArch64 EL1;
- readable `CNTFRQ_EL0`;
- GICv2 distributor and memory-mapped CPU interface;
- architected virtual timer on PPI/INTID 27.

QEMU `virt` exposes GICv2 without security extensions, so the test assigns the
PPI to its single primary group. On the X96, BL31 keeps Group 0 and XNU runs
non-secure Group 1; the non-secure CPU interface uses the same IAR/EOIR MMIO
offsets. The hardware grouping is therefore kept separate in the XNU target.

It is not an Android boot image, does not contain XNU or Apple userland, and
must not be flashed to the X96.

Run `./build.sh`, then `./run.sh`. Success ends with:

`PASS: GICv2 virtual timer INTID 27`
