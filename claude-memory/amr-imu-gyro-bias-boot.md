---
name: amr-imu-gyro-bias-boot
description: "Pose qui dérive dans RViz robot immobile = biais gyro IMU ; le firmware calibre le gyro AU BOOT du Teensy → toujours démarrer/power-cycler le Teensy robot IMMOBILE"
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-06 — La pose du robot DÉRIVE dans RViz alors qu'il est physiquement immobile.**

## Cause = biais du gyro IMU
`/imu/data` `angular_velocity.z ≈ -0.31 rad/s` (≈ -17°/s) AU REPOS (mesuré, biais constant sur 5
échantillons). L'EKF (`ekf.yaml`) fusionne **uniquement le yaw-rate IMU** (`imu0_config` vyaw) → il
croit que le robot tourne à 17°/s → la pose dérive/tourne en continu. Rien ne compensait ce biais
(pas d'offset gyro ni de routine de calibration explicite dans le firmware).

## FIX = power-cycler le Teensy, ROBOT IMMOBILE
Le firmware linorobot2 calibre le gyro **au boot** (échantillonne l'offset en supposant le robot
immobile). Si le Teensy a démarré pendant que le robot bougeait/vibrait → biais capturé de travers.
→ **Débrancher/rebrancher l'USB du Teensy (ou reset), robot POSÉ et IMMOBILE, ne pas y toucher.**
Après : gyro à ~0 (vérifier `ros2 topic echo /imu/data --once` → `angular_velocity.z ≈ 0`).

## Règle opérationnelle
- **Toujours allumer/power-cycler le Teensy (= le Pi, s'il alimente le Teensy) avec le robot
  parfaitement immobile.** Sinon dérive de pose garantie.
- Après tout power-cycle Teensy → **refaire la calibration encodeur** (`align_enc_cal.py`, table RAM
  perdue) — cf [[amr-pid-tuning]].
- ⚠️ Ce biais gyro masquait un autre bug : le deadlock d'accélération nav ([[amr-nav-accel-deadlock]]).
Cf `docs/history/2026-07-06-nav-gyro-ui.md`.
