#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
QEMU_ROOT="$BASE/local-tools/qemu"
export LD_LIBRARY_PATH="$QEMU_ROOT/usr/lib/x86_64-linux-gnu:$QEMU_ROOT/lib/x86_64-linux-gnu"

exec "$QEMU_ROOT/usr/bin/qemu-system-aarch64" \
    -L "$QEMU_ROOT/usr/share/qemu" \
    -M virt,gic-version=2,virtualization=on \
    -cpu cortex-a55 -smp 1 -m 512M \
    -nographic -nodefaults -serial stdio -monitor none -no-reboot \
    -semihosting-config enable=on,target=native \
    -kernel "$BASE/preflight-qemu/out/x96-preflight.elf"
