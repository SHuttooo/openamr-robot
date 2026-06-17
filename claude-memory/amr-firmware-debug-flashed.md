---
name: amr-firmware-debug-flashed
description: Firmware debug flashé sur le Teensy (counts bruts) + chaîne de build/flash PlatformIO sur le Pi
metadata: 
  node_type: memory
  type: project
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

Le 2026-06-17, on a flashé un **firmware debug** sur le Teensy (remplace le firmware d'origine,
non récupérable avant la vraie source thèse attendue ~2026-06-19). Base = upstream
`linorobot2_hardware` + notre config §7, cloné dans `~/linorobot2_hardware` sur le Pi.

**Ajouts debug (firmware.ino)** : 3 publishers `geometry_msgs/Vector3` best-effort :
- `/debug/left`  : x=rpm cible, y=rpm mesuré, z=counts bruts encodeur (MOTOR1 gauche)
- `/debug/right` : idem droite (MOTOR2) ← pour voir le décrochage des counts
- `/debug/pwm`   : x=pwm gauche, y=pwm droite (saturation PID visible)
Les 6 publishers passent (limite d'entités micro-ROS OK).

**Config flashée** : valeurs §7 (K_P 0.3/K_I 0.4/K_D 0.25, MOTOR_MAX_RPM 80, CPR 1024,
WHEEL 0.2, LR 0.45, PWM 3000, MOTOR1_ENCODER_INV true, MOTOR2_INV true, MOTOR1 PWM=1/INA=20/INB=21),
+ `BAUDRATE 115200` (l'agent tourne à 115200), + `MOTOR_POWER_MAX_VOLTAGE 24`.
⚠️ `_INV`/PID = RECONSTRUITS (§6.2), à re-vérifier ; à comparer à la vraie source.

**IMU RÉSOLUE** : la puce « MPU6050 » est en fait une **MPU6500**. Scan I²C (mini-firmware `~/i2cscan`
sur le Pi) : puce vivante à **0x68**, mais **WHO_AM_I = 0x70** (= MPU6500, pas 0x68 d'un vrai MPU6050).
Le driver MPU6050 la rejetait (testConnection echoue) → setup() plantait (LED 3 flashs). Fix : config
**`USE_MPU9250_IMU`** (au lieu de USE_MPU6050_IMU) — son testConnection accepte WHO_AM_I 0x70 (bits 6:1
= 0x38, validé dans MPU9250.cpp:77), et la classe MPU9250IMU ne fait qu'accel+gyro (pas de magnéto).
Vérifié : `/imu/data` lit la gravité (accel z ≈ 9,74 m/s²) → **vraie IMU fonctionnelle**. Câblage SDA18/SCL19 OK.
Note : pas de magnéto (USE_FAKE_MAG auto), orientation quaternion non calculée (raw accel+gyro seulement) ;
IMU montée avec un léger tilt (accel x ≈ -2 au repos) à recaler dans l'URDF. Outil de scan I²C réutilisable : `~/i2cscan`.

**Chaîne de build/flash sur le Pi (Ubuntu 24.04, PEP 668)** — non trivial, à réutiliser :
- PlatformIO installé DANS le penv : `~/.platformio/penv/bin/pio` (sinon les `pip install`
  internes de micro_ros_platformio sont bloqués par PEP 668). penv créé via `virtualenv` (pip --user)
  car `python3-venv`/ensurepip manquait.
- Build : `cd ~/linorobot2_hardware/firmware && ROS_DISTRO=jazzy ~/.platformio/penv/bin/pio run -e teensy40`
  (script `~/build_fw.sh`). 1er build ~5 min (compile micro-ROS), incrémental ~8 s.
- Flash : `teensy_loader_cli` (installé via `sudo apt install teensy-loader-cli`) + règles udev
  PJRC copiées dans `/etc/udev/rules.d/00-teensy.rules`. Commande qui marche (root) :
  `sudo teensy_loader_cli --mcu=TEENSY40 -w -v <firmware.hex>` quand le Teensy est EN HALFKAY.
  Le `-s` (soft reboot) peut rater l'écriture par course de timing → relancer `-w` une fois en HalfKay.
- `pkill -f micro_ros_agent` s'auto-matche (tue son ssh, exit 255) → utiliser `pkill micro_ros_agent`.

Voir [[pi-ssh-access]], [[amr-encodeurs-ok-test-A]].
