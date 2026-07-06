---
name: pi-ssh-access
description: Comment se connecter au Raspberry Pi 5 du robot AMR depuis la machine Windows
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

Le robot (Pi 5, OpenAMR/linorobot2) est joignable en SSH depuis la machine Windows de Matthieu.

> ⚠️ **IP en DHCP → elle CHANGE.** 2026-07-06 : Alex a changé le hardware du Pi (Matthieu a
> gardé le SSD) → nouvelle MAC → **nouvelle IP** : `172.17.201.29` (ancienne, MORTE) →
> **`172.17.17.64`** (actuelle). **TOUJOURS utiliser le hostname `botshare.local` (mDNS)** au
> lieu de l'IP en dur : `ssh botshare@botshare.local` — ça suit le SSD/hostname quelle que
> soit l'IP. Pour retrouver l'IP : `getent hosts botshare.local` ou
> `sudo arp-scan --localnet | grep -iE "raspberry|b8:27:eb|dc:a6:32|e4:5f:01|2c:cf:67|d8:3a:dd"`.

- Host : **`botshare.local`** (mDNS, robuste au DHCP ; IP actuelle `172.17.17.64`), user `botshare`, hostname `BOTSHARE`, Ubuntu 24.04 aarch64.
- ClÃ© publique `~/.ssh/id_ed25519_ovh.pub` installÃ©e dans `authorized_keys` du Pi â†’ connexion par clÃ©, non-interactive.
- Alias SSH dans `~/.ssh/config` : **`ssh pi`** — ⚠️ pointait sur l'ancienne IP `172.17.201.29`,
  à repointer sur `botshare.local` (`HostName botshare.local`) pour survivre au DHCP.
- Le mot de passe (auth password) du compte botshare est `<retiré du repo — voir mémoire locale>` (utilisÃ© une seule fois pour poser la clÃ©).

ROS n'est PAS chargÃ© en SSH non-interactif (`.bashrc` non sourcÃ©). PrÃ©fixer les commandes ros2 par :
`source /opt/ros/jazzy/setup.bash && source ~/linorobot2_ws/install/setup.bash && <cmd>`
En shell interactif (le user qui fait `ssh pi` Ã  la main), le `.bashrc` source dÃ©jÃ  ROS.

Devices : Teensy = `/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00` (ttyACM0) ;
RPLidar A1 = CP2102 (ttyUSB0). Agent micro-ROS lancÃ© Ã  115200.

Voir [[amr-encodeurs-ok-test-A]].

