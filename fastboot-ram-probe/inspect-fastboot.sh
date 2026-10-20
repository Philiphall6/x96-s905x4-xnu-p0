#!/bin/sh
set -eu

FASTBOOT=/home/mint/Android/Sdk/platform-tools/fastboot
test -x "$FASTBOOT"

DEVICES="$($FASTBOOT devices 2>/dev/null | awk 'NF >= 2 && $2 == "fastboot" { print $1 }')"
COUNT=$(printf '%s\n' "$DEVICES" | awk 'NF { count++ } END { print count + 0 }')

if [ "$COUNT" -eq 0 ]; then
    echo "Aucun appareil Fastboot détecté. Aucune action effectuée." >&2
    exit 2
fi
if [ "$COUNT" -ne 1 ]; then
    echo "Refus : $COUNT appareils Fastboot détectés. Préciser un seul appareil." >&2
    printf '%s\n' "$DEVICES" >&2
    exit 3
fi

SERIAL=$(printf '%s\n' "$DEVICES" | awk 'NF { print; exit }')
if [ "$#" -eq 1 ] && [ "$1" != "$SERIAL" ]; then
    echo "Refus : le numéro demandé '$1' ne correspond pas à '$SERIAL'." >&2
    exit 4
fi

echo "Appareil Fastboot unique : $SERIAL"
for VARIABLE in product serialno version-bootloader secure unlocked current-slot slot-count max-download-size; do
    echo "--- getvar $VARIABLE ---"
    "$FASTBOOT" -s "$SERIAL" getvar "$VARIABLE" 2>&1 || true
done

echo "Diagnostic terminé. Aucune écriture et aucun démarrage demandés."
