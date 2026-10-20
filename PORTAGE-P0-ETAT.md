# État du portage XNU X96 — P0

Date du point de contrôle : 2026-10-20

## Résultat atteint

Le socle architectural nécessaire à un premier démarrage noyau existe sans
avoir modifié la box ni l'image Android stable :

- cible XNU `X96SC2` pour Cortex-A55/ARMv8.2, pages de 16 Kio et ABI arm64 ;
- le S905X4 possède quatre cœurs Cortex-A55, mais le démarrage P0 est limité
  volontairement à CPU0 ; le jalon P1 activera les quatre cœurs via PSCI/SMP
  après validation du démarrage, du GIC et du timer sur un seul cœur ;
- GIC-400 réel du S905X4 : GICD `0xfff01000`, GICC `0xfff02000` ;
- timer virtuel PPI 11 / INTID 27 ;
- interface GICv2 mémoire pour acknowledge, EOI et SGI ;
- ADT distincts pour QEMU et pour le matériel provisoire ;
- console framebuffer rendue configurable par carte ;
- console série XNU en polling, sélectionnée par ADT : Meson UART matériel ou
  PL011 QEMU, sans reconfiguration des horloges ni des broches ;
- pré-test Cortex-A55 exécuté en QEMU avec entrée EL2, descente EL1 et IRQ
  timer réussie ;
- shim de mesure S905X4 autonome compilé, avec garde EL/MMU/cache avant tout
  accès mémoire physique, pile incluse dans l'Image et zéro relocalisation ;
- conteneur Android boot v3 préparé pour un futur `fastboot boot` RAM-only :
  noyau gzip réextrait à l'identique, pied AVB `NONE` recalculé et vérifié ;
- la logique exacte de la sonde a démarré comme Image ARM64 brute sous QEMU :
  EL2, FDT dans `x0`, magie `0xD00DFEED` et fin de mesure validés.
- le contrôle automatique `tools/verify_p0.py` confirme la cohérence entre les
  deux ADT, le profil matériel et le code source de la console série.
- la compilation XNU complète `DEVELOPMENT_ARM64_X96SC2` réussit sur le runner
  GitHub Actions Intel macOS 15 avec Xcode 16.2 ; l'exécutable obtenu est un
  Mach-O 64 bits ARM64. Le premier échec provenait uniquement de l'absence de
  capacité du runner macOS ARM64 et n'avait exécuté aucune étape du build.

Le test QEMU termine avec le code 0 et affiche :

```text
PASS: GICv2 virtual timer INTID 27
```

La sonde ARM64 brute affiche également :

```text
CURRENTEL=0x0000000000000008
FDT_POINTER=0x0000000048000000
FDT_MAGIC=0x00000000D00DFEED
MEASUREMENT COMPLETE
```

## Artefacts

- `out/x96-s905x4-qemu.adt`
  - SHA-256 : `9c9351a25194164c99ec5c280bb4c574583bb0f428cbe87442874abedd9a1d5b`
- `out/x96-s905x4-hardware-provisional.adt`
  - SHA-256 : `ec522aff35a2789fead23e37a82bab25a2afd0a961448c2db531d754a1887716`
- `preflight-qemu/out/x96-preflight.bin`
  - SHA-256 : `3233a7fb4611c43020bd41d0ce7403a2eb5438b4c93a7e68a171c557f3dbe992`
- `measure-shim/out/x96-measure.Image`
  - taille : `70272` octets
  - SHA-256 : `d83500acd9b5b6c93dfed0a12b27c01add72f6d324b5a4eee9340baedccead1c`
- `measure-shim/out/x96-measure.elf`
  - SHA-256 : `71b7bc3ad0410c4d39fe65e2bbacdac37d18c855808bb98dc9cb066c4891ac58`
- `measure-shim/out/qemu/x96-measure-qemu.Image`
  - SHA-256 : `7caf7b3b524452676cb62569b8eb56c0728254a31de25b9247922cd605f8bc28`
- `fastboot-ram-probe/out/X96_P0_FASTBOOT_BOOT_ONLY_NE_JAMAIS_FLASHER.img`
  - taille : `67108864` octets
  - SHA-256 : `8e988fec8f3d34051dc842409dc5c78d15a866c5e2539e7ef4fcafe841ed4cc7`
  - deux reconstructions consécutives donnent la même empreinte
- branche XNU locale : `x96-s905x4`
- commit XNU socle P0 : `1dcd589464c104b63c131128359e52a000f179cf`
- commit XNU console UART : `91851b1261ba7b78366bd0909322953dc892f33e`
- patch local : `out/source/0001-x96sc2-add-single-core-XNU-P0-target-with-GICv2.patch`
- patch UART : `out/source/0002-x96sc2-add-firmware-configured-uart-console.patch`
- bundle Git local : `out/source/xnu-x96sc2-p0.bundle`
- build GitHub Actions réussi :
  `https://github.com/Philiphall6/x96-s905x4-xnu-p0/actions/runs/39470717273`
- commit du dépôt de build : `74b414a`
- `kernel.development.x96sc2`
  - format : Mach-O 64 bits, ARM64, exécutable
  - taille : `16432688` octets
  - SHA-256 : `5bccf3a3aee242f24f4f075f1a6d38af09b698dbd1d26ed43996791812530ca1`
- archive GitHub `xnu-x96sc2-p0.zip`
  - SHA-256 : `504370c318320c0c71485d7ebcee072faa63319387fd44b56862a2bae4977a09`

## Ce qui n'est pas encore validé

- entrée réelle fournie par BL33/U-Boot sur la X96 ;
- fréquence réelle de `CNTFRQ_EL0` sur la box ;
- carte des réservations ATF/BL31 et emplacement RAM sûr ;
- adresse, format et durée de vie du framebuffer après U-Boot ;
- shim Android boot v3 Amlogic ;
- console série physique ;
- prise en charge réelle de `fastboot boot` par ce BL33/U-Boot ;
- stockage, USB, Ethernet, affichage piloté, audio ou Apple userland.

Les ADT et valeurs framebuffer matériels portent donc explicitement le statut
`provisional`. Ils ne doivent pas être emballés dans une image à flasher.

## Prochaine porte de validation

1. Emballer les dépendances de test, puis démarrer le noyau XNU compilé sous
   QEMU GICv2 avec l'ADT QEMU et un ramdisk minimal.
2. Capturer la première sortie série XNU et corriger le premier arrêt observé
   sans masquer les erreurs du noyau.
3. Entrer volontairement dans le Fastboot de la X96 puis exécuter uniquement
   `fastboot-ram-probe/inspect-fastboot.sh` pour identifier l'appareil.
4. Si le bootloader annonce une cible compatible, tester le shim uniquement
   par `fastboot boot`, jamais par `flash`, `update` ou écriture eMMC.
5. Relever CurrentEL, `CNTFRQ_EL0`, MPIDR et le FDT vivant, puis remplacer
   toutes les valeurs provisoires avant le premier essai XNU réel.

Le portage ne contient aucun contournement Apple ID, activation, SEP, FairPlay,
DRM ou signature. L'objectif P0 reste une console noyau expérimentale.
