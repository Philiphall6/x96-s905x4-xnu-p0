#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
OUT="${1:-$BASE/out/init}"
NDK_BIN="${X96_NDK_BIN:-/home/mint/Android/Sdk/ndk/29.0.14206865/toolchains/llvm/prebuilt/linux-x86_64/bin}"

mkdir -p "$OUT"
"$NDK_BIN/clang" -target arm64-apple-ios16.0 -c \
    "$BASE/init.S" -o "$OUT/x96-init.o"
python3 "$BASE/mk_mockfs_init.py" \
    "$OUT/x96-init.o" "$OUT/x96-init.macho"
"$NDK_BIN/llvm-objdump" --macho --private-header \
    "$OUT/x96-init.macho" > "$OUT/macho-header.txt"
(cd "$OUT" && sha256sum x96-init.o x96-init.macho > SHA256SUMS)
cat "$OUT/macho-header.txt"
