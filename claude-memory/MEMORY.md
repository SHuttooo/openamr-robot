# Mémoire projet — Robot AMR (OpenAMR / linorobot2)

- [Documentation projet](amr-project-docs.md) — doc onboarding EN anglais dans Documents/projet/openamr/docs/ (21 .md), à tenir à jour

- [Accès SSH au Pi](pi-ssh-access.md) — `ssh pi` (botshare@172.17.201.29), clé installée, sourcer ROS
- [Test A : encodeurs OK](amr-encodeurs-ok-test-A.md) — les 2 encodeurs comptent, hypothèse "encodeur droit mort" réfutée
- [Firmware debug flashé](amr-firmware-debug-flashed.md) — /debug/left|right|pwm (counts bruts), IMU réparée (puce = MPU6500 → USE_MPU9250_IMU), chaîne build/flash PlatformIO sur le Pi
- [Bring-up réel (1 launch)](amr-real-bringup.md) — openamr_real_bringup.launch.py = agent+lidar+odom→TF ; /cmd_vel /odom /imu /scan + TF prêts pour SLAM/Nav2 ; gotcha reset lidar
- [Emballement droit RÉSOLU](amr-runaway-rootcause.md) — 2 pots du driver droit : VAR (10 vs 3,5) = survitesse, ACC/DEC (0 vs 4) = à-coups ; alignés sur le gauche → roue droite stable
