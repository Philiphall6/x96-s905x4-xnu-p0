#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
NDK_BIN=/home/mint/Android/Sdk/ndk/29.0.14206865/toolchains/llvm/prebuilt/linux-x86_64/bin
OUT="$BASE/out"
mkdir -p "$OUT"

"$NDK_BIN/clang-21" --target=aarch64-none-elf -march=armv8.2-a \
    -O2 -Wall -Wextra -Werror -ffreestanding -fpie \
    -fno-stack-protector -fno-builtin -nostdlib \
    -fuse-ld=lld -Wl,-T,"$BASE/linker.ld" -Wl,--build-id=none \
    -Wl,-static -Wl,--no-dynamic-linker \
    -o "$OUT/x96-measure.elf" "$BASE/start.S" "$BASE/measure.c"
"$NDK_BIN/llvm-objcopy" -O binary "$OUT/x96-measure.elf" "$OUT/x96-measure.Image"
"$NDK_BIN/llvm-objdump" -d "$OUT/x96-measure.elf" > "$OUT/x96-measure.disasm.txt"
"$NDK_BIN/llvm-readelf" -h -l -r "$OUT/x96-measure.elf" > "$OUT/x96-measure.elf.txt"

# A Linux arm64 Image header must expose its magic at byte offset 56.
MAGIC=$(od -An -tx4 -j56 -N4 "$OUT/x96-measure.Image" | tr -d ' ')
test "$MAGIC" = 644d5241

# A RAM-only probe must be entirely self-contained at its load address.
if "$NDK_BIN/llvm-readelf" -r "$OUT/x96-measure.elf" | grep -Eq 'R_AARCH64_|Relocation section'; then
    echo "Unexpected runtime relocation in x96-measure.elf" >&2
    exit 1
fi

# The advertised Image size must be physically present in the raw file.
IMAGE_SIZE_HEX=$(od -An -tx8 -j16 -N8 "$OUT/x96-measure.Image" | tr -d ' ')
IMAGE_SIZE=$(printf '%d' "0x$IMAGE_SIZE_HEX")
ACTUAL_SIZE=$(wc -c < "$OUT/x96-measure.Image")
test "$IMAGE_SIZE" -eq "$ACTUAL_SIZE"

(cd "$OUT" && sha256sum x96-measure.elf x96-measure.Image > SHA256SUMS)
