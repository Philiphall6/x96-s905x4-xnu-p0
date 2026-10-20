# Compilation XNU P0

XNU 8796 ne peut pas être compilé complètement avec le seul NDK Linux présent
sur ce poste : le build dépend d'outils Xcode/macOS, notamment `iig`, des SDK
et du KDK correspondant. Le workflow `.github/workflows/xnu-x96.yml` exécute
cette compilation sans toucher à la X96.

Il utilise des versions épinglées :

- runner Intel `macos-15-intel` et Xcode 16.2. Cette combinaison est un essai
  validée pour ce build : l'essai macOS 15 ARM64 n'avait obtenu aucun runner,
  et GitHub avait explicitement signalé une contrainte de capacité sur sa
  flotte macOS ARM64 ;
- `blacktop/darwin-xnu-build` commit
  `663906528d1cd5ea8fde7de6f16de73db9511549` ;
- macOS 13.5 / XNU 8796 ;
- configuration `DEVELOPMENT_ARM64_X96SC2` ;
- patches P0 socle et console UART, appliqués dans cet ordre et dont les
  SHA-256 sont consignés dans `out/SHA256SUMS`.

Le run `39470717273`, au commit `74b414a`, a terminé avec succès :

- page du run :
  `https://github.com/Philiphall6/x96-s905x4-xnu-p0/actions/runs/39470717273` ;
- noyau : `kernel.development.x96sc2` ;
- format contrôlé : Mach-O 64 bits, ARM64, exécutable ;
- taille : `16432688` octets ;
- SHA-256 du noyau :
  `5bccf3a3aee242f24f4f075f1a6d38af09b698dbd1d26ed43996791812530ca1` ;
- SHA-256 de l'archive GitHub :
  `504370c318320c0c71485d7ebcee072faa63319387fd44b56862a2bae4977a09`.

L'archive contrôlée et extraite se trouve dans le partage Windows, sous
`X96-XNU-P0-NE-PAS-FLASHER/GITHUB-BUILD-39470717273/`.

Ce noyau n'est pas flashable : ce n'est ni une image Android `boot.img`, ni une
image Amlogic/Burn Tool. Il doit maintenant passer le boot QEMU avec l'ADT QEMU
et un ramdisk de test avant toute préparation d'un essai matériel RAM-only.
