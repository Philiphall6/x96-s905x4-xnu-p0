#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PROJECT="$(CDPATH= cd -- "$BASE/.." && pwd)"
MEASURE="$PROJECT/measure-shim/out/x96-measure.Image"
BASE_BOOT=/home/mint/x96-portage-sources/build/x96-stable-compact-work/v5/level1-v5/boot_a.PARTITION
MAGISKBOOT=/home/mint/t653t01-android14-root-compare/04_MAGISK_PATCHED/V643-Magisk29/magiskboot
AVBTOOL=/home/mint/bin/avbtool
OUT="$BASE/out"
OUTPUT="$OUT/X96_P0_FASTBOOT_BOOT_ONLY_NE_JAMAIS_FLASHER.img"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM

test -f "$MEASURE"
test -f "$BASE_BOOT"
test -x "$MAGISKBOOT"
test -x "$AVBTOOL"
mkdir -p "$OUT"

cp "$BASE_BOOT" "$WORK/original-boot.img"
(
    cd "$WORK"
    "$MAGISKBOOT" unpack -h original-boot.img > original-unpack.log 2>&1
    grep -F 'HEADER_VER      [3]' original-unpack.log >/dev/null
    grep -F 'KERNEL_FMT      [gzip]' original-unpack.log >/dev/null
    cp "$MEASURE" kernel
    "$MAGISKBOOT" repack original-boot.img "$OUTPUT" > repack.log 2>&1
)

# MagiskBoot preserves the original AVB descriptor, including its old Android
# kernel digest. Rebuild the unsigned (Algorithm NONE) hash footer so the
# descriptor authenticates the actual probe container instead.
PARTITION_SIZE=$(wc -c < "$BASE_BOOT")
"$AVBTOOL" erase_footer --image "$OUTPUT"
"$AVBTOOL" add_hash_footer \
    --image "$OUTPUT" \
    --partition_size "$PARTITION_SIZE" \
    --partition_name boot \
    --hash_algorithm sha256 \
    --salt db00761f6203edef3d1792072c40f66d123c62644de03b9b5281dc726631e85a \
    --algorithm NONE \
    --prop 'com.android.build.boot.fingerprint:Droidlogic/ohm/ohm:11/RD2A.211001.002/ubuntu03041518:userdebug/test-keys' \
    --prop 'com.android.build.boot.os_version:11'
test "$(wc -c < "$OUTPUT")" -eq "$PARTITION_SIZE"

# Re-extract the generated image and prove that its decompressed kernel is
# exactly the freestanding measurement Image built by measure-shim.
mkdir "$WORK/verify"
(
    cd "$WORK/verify"
    "$MAGISKBOOT" unpack -h "$OUTPUT" > "$OUT/unpack-verify.txt" 2>&1
    grep -F 'HEADER_VER      [3]' "$OUT/unpack-verify.txt" >/dev/null
    grep -F 'KERNEL_FMT      [gzip]' "$OUT/unpack-verify.txt" >/dev/null
    cmp kernel "$MEASURE"
)

"$AVBTOOL" info_image --image "$OUTPUT" > "$OUT/avb-info.txt"
# The embedded descriptor names its partition "boot". avbtool therefore
# resolves a sibling named boot.img during descriptor verification.
ln -s "$OUTPUT" "$WORK/boot.img"
"$AVBTOOL" verify_image --image "$WORK/boot.img" > "$OUT/avb-verify.txt"
grep -E '^Algorithm:[[:space:]]+NONE$' "$OUT/avb-info.txt" >/dev/null
grep -E '^[[:space:]]+Partition Name:[[:space:]]+boot$' "$OUT/avb-info.txt" >/dev/null

(
    cd "$OUT"
    sha256sum X96_P0_FASTBOOT_BOOT_ONLY_NE_JAMAIS_FLASHER.img > SHA256SUMS
)

echo "Built and verified: $OUTPUT"
echo "RAM boot only. Never use fastboot flash or USB Burn Tool."
