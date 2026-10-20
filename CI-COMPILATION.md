# Compilation XNU P0

XNU 8796 ne peut pas être compilé complètement avec le NDK Linux présent sur
ce poste : le build dépend d'outils Xcode/macOS, notamment `iig`, des SDK et du
KDK correspondant. Le workflow `.github/workflows/xnu-x96.yml` prépare la
porte de validation sans toucher à la X96.

Il utilise des versions épinglées :

- runner `macos-14` et Xcode 15 ;
- `blacktop/darwin-xnu-build` commit
  `663906528d1cd5ea8fde7de6f16de73db9511549` ;
- macOS 13.5 / XNU 8796 ;
- configuration `DEVELOPMENT_ARM64_X96SC2` ;
- patches P0 socle et console UART, appliqués dans cet ordre et dont les
  SHA-256 sont consignés dans `out/SHA256SUMS`.

Pour l'exécuter, ce dossier doit être placé dans un dépôt GitHub autorisé par
son propriétaire, puis le workflow `XNU X96SC2 P0` doit être lancé
manuellement. Aucun secret, firmware Apple, sauvegarde de box ou donnée
personnelle ne doit être ajouté au dépôt.

Le résultat attendu est `kernel.development.x96sc2`. Même si la compilation
réussit, ce noyau n'est pas flashable : il devra d'abord passer le boot QEMU
avec l'ADT QEMU et un root ramdisk de test.
