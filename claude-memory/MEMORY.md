# Mémoire projet — Robot AMR (OpenAMR / linorobot2)

- [Documentation projet](amr-project-docs.md) — doc onboarding EN anglais dans Documents/projet/openamr/docs/ (21 .md), à tenir à jour

- [Accès SSH au Pi](pi-ssh-access.md) — `ssh pi` (botshare@172.17.201.29), clé installée, sourcer ROS
- [Test A : encodeurs OK](amr-encodeurs-ok-test-A.md) — les 2 encodeurs comptent, hypothèse "encodeur droit mort" réfutée
- [Firmware debug flashé](amr-firmware-debug-flashed.md) — /debug/left|right|pwm (counts bruts), IMU réparée (puce = MPU6500 → USE_MPU9250_IMU), chaîne build/flash PlatformIO sur le Pi
- [Bring-up réel (1 launch)](amr-real-bringup.md) — openamr_real_bringup.launch.py = agent+lidar+odom→TF ; /cmd_vel /odom /imu /scan + TF prêts pour SLAM/Nav2 ; gotcha reset lidar
- [Emballement droit RÉSOLU](amr-runaway-rootcause.md) — 2 pots du driver droit : VAR (10 vs 3,5) = survitesse, ACC/DEC (0 vs 4) = à-coups ; alignés sur le gauche → roue droite stable
- [Câblage couleurs DC](amr-wiring-dc-colors.md) — sur ce robot, alim continue : marron = + (rouge), bleu = − (noir) ; contre-intuitif, vérifier au multimètre
- [Caméra IMX708 / libcamera](amr-camera-imx708-libcamera.md) — HW OK (imx708_noir relié), mais libcamera upstream ne gère pas la Cam Module 3 sur Pi5 → compiler le fork Raspberry Pi de libcamera + camera_ros
- [PID / roue gauche](amr-pid-tracking-observation.md) — roue gauche intermittente = faux contact 24V (pas le PID) ; droite plus faible ; tuning à attendre (vraie source firmware)
- [Session 2026-06-18](amr-session-2026-06-18.md) — EKF IMU, filtre scan, SLAM+carte coin1, caméra IMX708 (fork RPi libcamera), roue gauche faux-contact, doc MAJ
- [Docking/Nav2 réel](amr-docking-nav2-real.md) — openamr-platform-sw buildé sur le Pi ; plan portage docking réel (CycloneDDS, calib caméra, dock AprilTag physique, gotcha isolation domaine sim)
- [Roue gauche faux-contact](amr-left-wheel-faux-contact.md) — BLOQUEUR n°1 : chaîne gauche intermittente (câble), à réparer (souder)
- [Réglage drivers (pots/DIP)](amr-driver-balance-dip.md) — équilibrage VAR droit (tangage), piste DIP SW1 boucle ouverte, quantif rpm
- [Suite session Nav2/Cyclone](amr-session-suite-nav2-cyclone.md) — CycloneDDS, openamr-platform-sw buildé, docking, contrôle OK ; reste câble gauche
