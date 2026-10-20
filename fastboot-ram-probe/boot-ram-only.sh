#!/bin/sh
set -eu

BASE="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
FASTBOOT=/home/mint/Android/Sdk/platform-tools/fastboot
IMAGE="$BASE/out/X96_P0_FASTBOOT_BOOT_ONLY_NE_JAMAIS_FLASHER.img"
EXPECTED_SHA256=8e988fec8f3d34051dc842409dc5c78d15a866c5e2539e7ef4fcafe841ed4cc7

if [ "$#" -ne 1 ]; then
    echo "Usage: X96_RAM_BOOT_CONFIRM=RAM_ONLY $0 NUMERO_DE_SERIE" >&2
    exit 2
fi
if [ "${X96_RAM_BOOT_CONFIRM:-}" != RAM_ONLY ]; then
    echo "Refus : confirmation RAM_ONLY absente." >&2
    exit 3
fi

SERIAL=$1
test -x "$FASTBOOT"
test -f "$IMAGE"
ACTUAL_SHA256=$(sha256sum "$IMAGE" | awk '{ print $1 }')
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "Refus : SHA-256 inattendu pour l'image." >&2
    exit 4
fi

MATCHES="$($FASTBOOT devices 2>/dev/null | awk -v serial="$SERIAL" '$1 == serial && $2 == "fastboot" { count++ } END { print count + 0 }')"
if [ "$MATCHES" -ne 1 ]; then
    echo "Refus : le numéro '$SERIAL' n'est pas présent une seule fois en Fastboot." >&2
    exit 5
fi

echo "Commande autorisée : fastboot boot (RAM uniquement)"
echo "Aucune commande flash/update/erase n'est présente dans ce script."
exec "$FASTBOOT" -s "$SERIAL" boot "$IMAGE"
