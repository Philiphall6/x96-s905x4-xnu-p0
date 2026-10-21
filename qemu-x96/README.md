# Démarrage XNU X96SC2 sous QEMU

Ce banc lance uniquement le noyau ARM64 sous QEMU `virt` avec un GICv2. Il ne
communique pas avec la X96 et ne produit aucune image Amlogic ou Burn Tool.

Le test construit un petit exécutable Mach-O libre de dépendances, le présente
à XNU comme `/sbin/launchd` au moyen de `mockfs`, puis attend les messages :

```text
*** X96SC2 userspace: init running as PID 1 ***
X96SC2 init: still alive
```

Lancer un essai dans un nouveau dossier :

```sh
./qemu-x96/prepare-and-run.sh /chemin/kernel.development.x96sc2 \
    qemu-x96/out/run-0002-mockfs
```

Le test dure 150 secondes par défaut : XNU attend environ 30 secondes pendant
l'initialisation RTC avant de poursuivre BSD. Pour un diagnostic court qui ne
peut pas valider le montage racine :

```sh
X96_QEMU_SECONDS=30 ./qemu-x96/prepare-and-run.sh KERNEL NOUVEAU_DOSSIER
```

Les arguments de démarrage QEMU contiennent `wdt=-1`. Ce réglage désactive
uniquement les watchdogs de latence dans l'émulateur : une pause de
l'ordonnanceur hôte peut sinon dépasser le seuil XNU de quelques
millisecondes. L'ADT matériel et un futur essai RAM-only ne reçoivent pas ce
réglage.

Le dossier `runtime` contient la console série, les registres CPU, les deux
framebuffers bruts et `result.json`. En cas de panique, `symbols.txt` associe
automatiquement le PC, le LR et l'appelant aux symboles du noyau. La machine
QEMU possède 3 Gio uniquement pour couvrir le framebuffer précoce provisoire à
`0xdff80000`; les `boot_args` annoncent toujours exactement 1 Gio de RAM gérée
à XNU, de `0x40000000` à `0x80000000`.

Le noyau requis doit inclure le patch
`0003-x96sc2-enable-mockfs-RAM-disk-root-for-QEMU.patch`. Un noyau antérieur
démarre correctement mais reste dans `cpu_idle`, car il ne peut pas monter le
RAMDisk comme racine.
