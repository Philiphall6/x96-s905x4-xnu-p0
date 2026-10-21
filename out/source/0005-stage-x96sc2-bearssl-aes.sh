#!/bin/bash
# Stage a pinned, portable and constant-time AES implementation for X96SC2.
set -euo pipefail

[[ "${MACHINE_CONFIG:-}" == X96SC2 ]] || exit 0
[[ -f libkern/crypto/corecrypto_aes.c ]]

bearssl_commit=7bea48e5e850ab4cafbe68d3765cdaba13a86d6f
stage_dir=$(mktemp -d)
trap 'rm -rf "$stage_dir"' EXIT
git init -q "$stage_dir"
git -C "$stage_dir" fetch -q --depth 1 \
    https://www.bearssl.org/git/BearSSL "$bearssl_commit"
git -C "$stage_dir" checkout -q FETCH_HEAD
[[ "$(git -C "$stage_dir" rev-parse HEAD)" == "$bearssl_commit" ]]

python3 - "$stage_dir" <<'PY'
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
target = Path("libkern/crypto/x96_bearssl")
if target.exists():
    raise SystemExit(f"refusing to overwrite staged AES source: {target}")
shutil.copytree(source / "inc", target / "inc")
(target / "src/symcipher").mkdir(parents=True)
for filename in ("inner.h", "config.h"):
    shutil.copy2(source / "src" / filename, target / "src" / filename)

header = target / "src/inner.h"
text = header.read_text()
old = "#include <limits.h>"
if text.count(old) != 1:
    raise SystemExit("unexpected BearSSL inner.h limits include")
header.write_text(text.replace(
    old,
    "#if defined(KERNEL)\n#include <machine/limits.h>\n"
    "#else\n#include <limits.h>\n#endif",
))

for name in ("aes_ct", "aes_ct_enc", "aes_ct_dec", "aes_ct_cbcenc", "aes_ct_cbcdec"):
    shutil.copy2(source / "src/symcipher" / f"{name}.c",
                 target / "src/symcipher" / f"{name}.c")
shutil.copy2(source / "LICENSE.txt", target / "LICENSE.txt")
PY

echo "Staged BearSSL AES ($bearssl_commit) for X96SC2"
