#!/bin/sh
set -eu

NDK_BIN=/home/mint/Android/Sdk/ndk/29.0.14206865/toolchains/llvm/prebuilt/linux-x86_64/bin
OUT="$(dirname "$0")/out"
mkdir -p "$OUT"

"$NDK_BIN/clang-21" --target=aarch64-none-elf -march=armv8.2-a \
    -nostdlib -fuse-ld=lld -Wl,-T,"$(dirname "$0")/linker.ld" \
    -Wl,--build-id=none -o "$OUT/x96-preflight.elf" "$(dirname "$0")/start.S"
"$NDK_BIN/llvm-objcopy" -O binary "$OUT/x96-preflight.elf" "$OUT/x96-preflight.bin"
"$NDK_BIN/llvm-objdump" -d "$OUT/x96-preflight.elf" > "$OUT/x96-preflight.disasm.txt"
"$NDK_BIN/llvm-readelf" -h -l "$OUT/x96-preflight.elf" > "$OUT/x96-preflight.elf.txt"
sha256sum "$OUT/x96-preflight.elf" "$OUT/x96-preflight.bin" > "$OUT/SHA256SUMS"

