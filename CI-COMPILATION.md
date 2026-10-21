# Compilation XNU P0

XNU 8796 ne peut pas être compilé complètement avec le seul NDK Linux présent
sur ce poste : le build dépend d'outils Xcode/macOS, notamment `iig`, des SDK
et du KDK correspondant. Le workflow `.github/workflows/xnu-x96.yml` exécute
cette compilation sans toucher à la X96.

Il utilise des versions épinglées :

- runner Intel `macos-15-intel` et Xcode 16.2. Cette combinaison est validée
  pour ce build : l'essai macOS 15 ARM64 n'avait obtenu aucun runner,
  et GitHub avait explicitement signalé une contrainte de capacité sur sa
  flotte macOS ARM64 ;
- `blacktop/darwin-xnu-build` commit
  `663906528d1cd5ea8fde7de6f16de73db9511549` ;
- macOS 13.5 / XNU 8796 ;
- configuration `DEVELOPMENT_ARM64_X96SC2` ;
- patches P0, UART, `mockfs`, pthread, AES-CBC, SHA-256 et pont AMFI minimal,
  appliqués dans cet ordre et dont les SHA-256 sont consignés dans
  `out/SHA256SUMS`.

Le run actuel `39553350284`, au commit `77195ef`, a terminé avec succès :

- page du run :
  `https://github.com/Philiphall6/x96-s905x4-xnu-p0/actions/runs/39553350284` ;
- noyau : `kernel.development.x96sc2` ;
- format contrôlé : Mach-O 64 bits, ARM64, exécutable ;
- taille : `16473840` octets ;
- SHA-256 du noyau :
  `cebaef8791c4219be8cc2ad36767cd66ae602735d2fe6b52b0f33659f26125e8` ;
- SHA-256 de l'archive GitHub :
  `09ad4576100d4a5248f0097d77b166f8db47e6f230e8d3f48cfec990b043c5ff`.

L'archive contrôlée et extraite se trouve dans le partage Windows, sous
`X96-XNU-P0-NE-PAS-FLASHER/GITHUB-BUILD-39553350284-AMFI/`.

Ce noyau n'est pas flashable : ce n'est ni une image Android `boot.img`, ni une
image Amlogic/Burn Tool. Son test QEMU avec PID 1 est décrit dans
`QEMU-VALIDATION.md`. Un éventuel essai matériel futur restera RAM-only et
nécessite d'abord les mesures réelles de la mémoire et de l'entrée bootloader.
