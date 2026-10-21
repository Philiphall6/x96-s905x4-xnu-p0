# Validation XNU X96SC2 sous QEMU

Date du jalon : 2026-10-21

## Résultat

Le noyau `DEVELOPMENT_ARM64_X96SC2` atteint un espace utilisateur minimal sous
QEMU `virt`/GICv2. Le test final a duré 150 secondes et a produit les trois
résultats attendus :

```text
BSD root: md0, major 1, minor 0
*** X96SC2 userspace: init running as PID 1 ***
X96SC2 init: still alive
```

Le fichier `result.json` confirme :

```json
{
  "qemu_returncode": 0,
  "seconds": 150.0,
  "panic_observed": false,
  "userspace_init_observed": true,
  "userspace_heartbeat_observed": true
}
```

Cette validation couvre le démarrage XNU monocœur, le GICv2, le timer, la
console série, le montage racine `mockfs`, les fournisseurs pthread, AES-CBC et
SHA-256, l'ajout d'une signature ad hoc valide au vnode et l'exécution du PID 1.
Elle ne valide pas encore le matériel Amlogic réel ni un userland tvOS.

## Progression observée

| Run GitHub | Correctif ajouté | Résultat QEMU utile |
| --- | --- | --- |
| `39544197614` | racine RAMDisk `mockfs` | blocage : fournisseur pthread absent |
| `39545938207` | libpthread `514.100.2` | blocage : `_aes_encrypt_key128+0x18` |
| `39547467118` | AES-CBC BearSSL portable | blocage : `_SHA256_Init+0x18` |
| `39549797096` | SHA-256 `ccsha256_ltc_di` | atteint `/sbin/launchd`, puis interface OSEntitlements absente |
| `39553350284` | pont AMFI sans entitlements | PID 1 et heartbeat, aucune panique |

Chaque correctif correspond au premier arrêt réellement observé. Aucun service
matériel fictif n'a été ajouté pour masquer une erreur.

## Artefact validé

- run GitHub Actions : `39553350284` ;
- artefact GitHub : `12324693647` ;
- archive `xnu-x96sc2-p0.zip` :
  `09ad4576100d4a5248f0097d77b166f8db47e6f230e8d3f48cfec990b043c5ff` ;
- `kernel.development.x96sc2` : 16 473 840 octets ;
- SHA-256 du noyau :
  `cebaef8791c4219be8cc2ad36767cd66ae602735d2fe6b52b0f33659f26125e8` ;
- init Mach-O signé :
  `ae9f103caaa1564996c57c500cae0408c137d0f15c5fb7d015835944222341b1`.

L'archive et les preuves QEMU sont dans le partage Windows :

```text
X96-XNU-P0-NE-PAS-FLASHER/
  GITHUB-BUILD-39553350284-AMFI/
    QEMU-RUN-0007-PID1-PASS/
```

## Limites de sécurité

Le pont AMFI intégré ne fabrique aucun objet d'entitlements, refuse toutes les
requêtes d'entitlement et n'accorde aucun privilège. La validation de structure
de signature et des hachages de pages exécutables reste assurée par XNU. Les trust
caches restent indisponibles sans Image4.

Il n'existe dans ce jalon aucun contournement Apple ID, activation, SEP,
FairPlay, DRM ou contrôle de signature. Le noyau Mach-O n'est ni une image Android, ni une
image Amlogic Burn Tool et ne doit pas être flashé.
