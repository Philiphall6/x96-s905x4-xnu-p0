# Sonde X96 P0 — démarrage Fastboot en RAM uniquement

Ce dossier construit un conteneur Android boot v3 pour transporter la sonde
`x96-measure.Image` jusqu'au bootloader de la X96 sans écrire l'eMMC.

Le résultat est explicitement nommé :

`X96_P0_FASTBOOT_BOOT_ONLY_NE_JAMAIS_FLASHER.img`

Il conserve la structure du `boot_a` V5 connu, le noyau gzip et son pied AVB
sans signature (`Algorithm: NONE`). La vérification réextrait le noyau du
résultat et exige une identité bit à bit avec la sonde originale.

## Interdictions

- ne jamais charger ce fichier dans Amlogic USB Burn Tool ;
- ne jamais employer `fastboot flash`, `fastboot update` ou `fastboot erase` ;
- ne l'écrire dans aucune partition, carte SD ou clé USB ;
- ne pas lancer l'essai tant que l'appareil n'est pas identifié sans ambiguïté
  par son numéro de série Fastboot et qu'une récupération Burn Tool connue
  n'est pas disponible.

## État

Artefact hors ligne seulement. Le démarrage matériel n'a pas été exécuté.
La future commande RAM-only devra utiliser exclusivement `fastboot boot`,
après une nouvelle vérification de l'appareil et de l'image. Si le bootloader
refuse cette commande, l'essai s'arrête : aucun contournement par flash n'est
autorisé pour ce jalon.

`inspect-fastboot.sh` ne fait que lire les variables d'un appareil Fastboot
unique. `boot-ram-only.sh` contient uniquement la commande de démarrage RAM,
mais exige le numéro de série, la bonne empreinte de l'image et la confirmation
explicite `X96_RAM_BOOT_CONFIRM=RAM_ONLY`.
