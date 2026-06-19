# Mémoire projet — Robot AMR (OpenAMR / linorobot2)

- [Câblage couleurs DC](amr-wiring-dc-colors.md) — sur ce robot, marron = + (rouge), bleu = − (noir)
- [Caméra IMX708 / libcamera](amr-camera-imx708-libcamera.md) — HW OK, libcamera upstream ne gère pas la Cam Module 3 → besoin du fork RPi (à compiler)
- [Docking/Nav2 réel](amr-docking-nav2-real.md) — openamr-platform-sw buildé sur le Pi ; plan portage docking réel + gotchas (CycloneDDS, calib, dock physique, isolation domaine sim)
- [Roue gauche faux-contact](amr-left-wheel-faux-contact.md) — BLOQUEUR n°1 : chaîne gauche intermittente (câble), à réparer (souder)
- [Réglage drivers (pots/DIP)](amr-driver-balance-dip.md) — équilibrage VAR droit (tangage), piste DIP SW1 boucle ouverte, quantif rpm
- [Suite session Nav2/Cyclone](amr-session-suite-nav2-cyclone.md) — CycloneDDS, openamr-platform-sw buildé, docking, contrôle OK ; reste câble gauche
- [Encodeurs 5V surtension](amr-encoder-5v-overvoltage.md) — défaut : sorties A/B ~4V sur Teensy 3.3V non tolérant → à protéger (résistance/diviseur/level-shifter)
- [Commandes Pi/ROS (recette)](amr-pi-ros-commands.md) — SSH, env Cyclone, agent micro-ROS, /debug/openloop + /debug/left|right, le piège du backgrounding SSH → script détaché + log
- [Nav2+AMCL réel (recette)](amr-nav2-bringup.md) — séquence launch + TOUS les pièges (filtre doublon, teleop, 2D Goal Pose+relais, footprint 78×58, obstacle_min_range 0.10, DWB vs RPP)
- [Commits sans mention Claude](amr-commit-no-claude.md) — préférence : pas de Co-Authored-By/Generated, commits directs sur master
