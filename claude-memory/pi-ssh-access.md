---
name: pi-ssh-access
description: Comment se connecter au Raspberry Pi 5 du robot AMR depuis la machine Windows
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

Le robot (Pi 5, OpenAMR/linorobot2) est joignable en SSH depuis la machine Windows de Matthieu.

- Host : `172.17.201.29` (rÃ©seau local), user `botshare`, hostname `BOTSHARE`, Ubuntu 24.04 aarch64.
- ClÃ© publique `~/.ssh/id_ed25519_ovh.pub` installÃ©e dans `authorized_keys` du Pi â†’ connexion par clÃ©, non-interactive.
- Alias SSH ajoutÃ© dans `~/.ssh/config` : **`ssh pi`** (= `botshare@172.17.201.29`).
- Le mot de passe (auth password) du compte botshare est `<retiré du repo — voir mémoire locale>` (utilisÃ© une seule fois pour poser la clÃ©).

ROS n'est PAS chargÃ© en SSH non-interactif (`.bashrc` non sourcÃ©). PrÃ©fixer les commandes ros2 par :
`source /opt/ros/jazzy/setup.bash && source ~/linorobot2_ws/install/setup.bash && <cmd>`
En shell interactif (le user qui fait `ssh pi` Ã  la main), le `.bashrc` source dÃ©jÃ  ROS.

Devices : Teensy = `/dev/serial/by-id/usb-Teensyduino_USB_Serial_16778200-if00` (ttyACM0) ;
RPLidar A1 = CP2102 (ttyUSB0). Agent micro-ROS lancÃ© Ã  115200.

Voir [[amr-encodeurs-ok-test-A]].

