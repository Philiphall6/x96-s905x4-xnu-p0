#!/bin/bash
# Stage Apple's matching open-source libpthread provider before XNU patches.
set -euo pipefail

[[ "${MACHINE_CONFIG:-}" == X96SC2 ]] || exit 0
[[ "${MACOS_VERSION:-}" == 13.5 ]] || {
    echo 'X96SC2 libpthread requires the XNU 8796 / macOS 13.5 source set' >&2
    exit 1
}
[[ -f bsd/pthread/pthread_shims.c ]]

pthread_commit=a6c70ca0e544347a0377babf748f831577ec24f9
stage_dir=$(mktemp -d)
trap 'rm -rf "$stage_dir"' EXIT
git init -q "$stage_dir"
git -C "$stage_dir" fetch -q --depth 1 \
    https://github.com/apple-oss-distributions/libpthread "$pthread_commit"
git -C "$stage_dir" checkout -q FETCH_HEAD
[[ "$(git -C "$stage_dir" rev-parse HEAD)" == "$pthread_commit" ]]

python3 - "$stage_dir" <<'PY'
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
target = Path("bsd/pthread/x96_libpthread")
if target.exists():
    raise SystemExit(f"refusing to overwrite staged provider: {target}")
for directory in ("kern", "private", "include"):
    shutil.copytree(source / directory, target / directory)


def replace(filename: str, old: str, new: str, count: int) -> None:
    path = target / "kern" / filename
    text = path.read_text()
    if text.count(old) != count:
        raise SystemExit(f"unexpected libpthread source at {filename}: {old!r}")
    path.write_text(text.replace(old, new))


# Match the stricter types used by the public XNU source while retaining the
# provider ABI. These are source adaptations, not behavioural replacements.
replace("kern_trace.h", "vm_kernel_unslide_or_perm_external(ptr,",
        "vm_kernel_unslide_or_perm_external((vm_offset_t)ptr,", 1)
for callback, count in (("psynch_wait_update_owner", 4),
                        ("psynch_wait_complete", 1),
                        ("psynch_wait_wakeup", 2)):
    replace("kern_synch.c", f"pthread_kern->{callback}(kwq,",
            f"pthread_kern->{callback}((uintptr_t)kwq,", count)
replace("kern_support.c", "*kevent_list_out = NULL;", "*kevent_list_out = 0;", 1)
replace("kern_support.c", "user_addr_t kevent_list = NULL;",
        "user_addr_t kevent_list = 0;", 2)
replace("kern_support.c", "workq_kevent(p, &th_addrs, NULL,",
        "workq_kevent(p, &th_addrs, 0,", 1)
replace("kern_support.c", "panic(__func__ \": thread_set_wq_state failed: %d\", error);",
        "panic(\"%s: thread_set_wq_state failed: %d\", __func__, error);", 4)
PY

# The XNU build uses -nostdinc. Preserve the SDK's target macro definitions
# beside the provider so the staged build context remains reproducible.
sdk_root=$(xcrun --sdk macosx --show-sdk-path)
cp "$sdk_root/usr/include/TargetConditionals.h" \
    bsd/pthread/x96_libpthread/TargetConditionals.h
echo "Staged Apple libpthread-514.100.2 ($pthread_commit) for X96SC2"
