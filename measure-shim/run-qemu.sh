#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
QEMU_ROOT="$BASE/local-tools/qemu"
PROBE="$BASE/measure-shim/out/qemu/x96-measure-qemu.Image"
LOG="$BASE/measure-shim/out/qemu/run.log"
export LD_LIBRARY_PATH="$QEMU_ROOT/usr/lib/x86_64-linux-gnu:$QEMU_ROOT/lib/x86_64-linux-gnu"

set +e
timeout 5 "$QEMU_ROOT/usr/bin/qemu-system-aarch64" \
    -L "$QEMU_ROOT/usr/share/qemu" \
    -M virt,gic-version=2,virtualization=on \
    -cpu cortex-a55 -smp 1 -m 512M \
    -nographic -nodefaults -serial stdio -monitor none -no-reboot \
    -kernel "$PROBE" > "$LOG" 2>&1
RC=$?
set -e

# The probe intentionally remains in WFE after reporting; timeout 124 is the
# expected stop mechanism for this VM-only test.
test "$RC" -eq 124
grep -F 'X96 S905X4 P0 READ-ONLY MEASUREMENT' "$LOG" >/dev/null
grep -F 'FDT_MAGIC=0x00000000D00DFEED' "$LOG" >/dev/null
grep -F 'MEASUREMENT COMPLETE' "$LOG" >/dev/null
cat "$LOG"
