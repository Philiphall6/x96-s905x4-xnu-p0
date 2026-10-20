#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
NDK_BIN=/home/mint/Android/Sdk/ndk/29.0.14206865/toolchains/llvm/prebuilt/linux-x86_64/bin
OUT="$BASE/out/qemu"
mkdir -p "$OUT"

"$NDK_BIN/clang-21" --target=aarch64-none-elf -march=armv8.2-a \
    -DMEASURE_QEMU=1 -O2 -Wall -Wextra -Werror -ffreestanding -fpie \
    -fno-stack-protector -fno-builtin -nostdlib \
    -fuse-ld=lld -Wl,-T,"$BASE/linker.ld" -Wl,--build-id=none \
    -Wl,-static -Wl,--no-dynamic-linker \
    -o "$OUT/x96-measure-qemu.elf" "$BASE/start.S" "$BASE/measure.c"
"$NDK_BIN/llvm-objcopy" -O binary \
    "$OUT/x96-measure-qemu.elf" "$OUT/x96-measure-qemu.Image"
"$NDK_BIN/llvm-objdump" -d "$OUT/x96-measure-qemu.elf" \
    > "$OUT/x96-measure-qemu.disasm.txt"
"$NDK_BIN/llvm-readelf" -h -l -r "$OUT/x96-measure-qemu.elf" \
    > "$OUT/x96-measure-qemu.elf.txt"

MAGIC=$(od -An -tx4 -j56 -N4 "$OUT/x96-measure-qemu.Image" | tr -d ' ')
test "$MAGIC" = 644d5241
if "$NDK_BIN/llvm-readelf" -r "$OUT/x96-measure-qemu.elf" | grep -Eq 'R_AARCH64_|Relocation section'; then
    echo "Unexpected runtime relocation in QEMU probe" >&2
    exit 1
fi
IMAGE_SIZE_HEX=$(od -An -tx8 -j16 -N8 "$OUT/x96-measure-qemu.Image" | tr -d ' ')
IMAGE_SIZE=$(printf '%d' "0x$IMAGE_SIZE_HEX")
test "$IMAGE_SIZE" -eq "$(wc -c < "$OUT/x96-measure-qemu.Image")"
(cd "$OUT" && sha256sum x96-measure-qemu.elf x96-measure-qemu.Image > SHA256SUMS)
