#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PROJECT="$(CDPATH= cd -- "$BASE/.." && pwd)"
RUN_SECONDS="${X96_QEMU_SECONDS:-150}"

if [ "$#" -ne 2 ]; then
    echo "usage: $0 KERNEL_MACHO NEW_RUN_DIRECTORY" >&2
    exit 2
fi

KERNEL="$1"
RUN="$2"
test -f "$KERNEL"
test ! -e "$RUN"
mkdir -p "$RUN/prepared"

"$BASE/build-init.sh" "$RUN/prepared/init"
INIT="$RUN/prepared/init/x96-init.macho"
INIT_SIZE=$(wc -c < "$INIT")
RAMDISK_SIZE=$(( (INIT_SIZE + 16383) / 16384 * 16384 ))

python3 "$PROJECT/tools/mkadt_x96.py" "$RUN/prepared/x96-qemu.adt" \
    --qemu --ramdisk-address 0x44000000 --ramdisk-size "$RAMDISK_SIZE"
python3 "$BASE/prepare.py" "$KERNEL" "$RUN/prepared/x96-qemu.adt" \
    "$RUN/prepared" --ramdisk "$INIT"
set +e
python3 "$BASE/run.py" "$RUN/prepared" "$RUN/runtime" --seconds "$RUN_SECONDS"
RUN_STATUS=$?
set -e
if grep -q 'panic(' "$RUN/runtime/serial.txt"; then
    python3 "$BASE/symbolize.py" "$KERNEL" \
        --serial "$RUN/runtime/serial.txt" > "$RUN/runtime/symbols.txt"
fi
exit "$RUN_STATUS"
