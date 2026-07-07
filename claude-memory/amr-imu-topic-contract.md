---
name: amr-imu-topic-contract
description: "INCOHÉRENCE non résolue (audit 2026-07-08) : le firmware git publie /imu/data_raw + /imu/mag (USE_FAKE_MAG non défini) MAIS l'EKF lit /imu/data et rien ne produit /imu/data (pas de madgwick). À trancher SUR LE ROBOT : ros2 topic list | grep imu."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-08 — Trou d'intégration IMU trouvé à l'audit de cohérence. NON résolu (besoin du robot).**

## Les faits (vérifiés dans le code git)
- `firmware.ino` : le nom de topic IMU dépend de `#ifndef USE_FAKE_MAG`. Dans le config git,
  **`USE_FAKE_MAG` n'est PAS défini** → le firmware publie **`/imu/data_raw`** + **`/imu/mag`**.
- `ekf.yaml` (robot_localization) : **`imu0: /imu/data`** (fusionne seulement le yaw-rate gyro).
- **Aucun node ne produit `/imu/data`** (pas de `imu_filter_madgwick`, pas de remap) dans les launch git.
- `drivers.launch.py` commente aussi (à tort) que l'agent bridge `/imu/data`.
- ⚠️ Or la mémoire [[amr-imu-gyro-bias-boot]] dit que **sur le vrai robot l'EKF FUSIONNE bien le yaw-rate**
  → donc le **déployé diffère du git**. L'odométrie (/odom/unfiltered → EKF → /odom) est cohérente, elle.

## Les deux vérités possibles (indécidable au bureau)
- **(A)** Déployé = firmware publie `/imu/data_raw`, et l'ekf déployé lit `/imu/data_raw` (git ekf périmé).
  → Fix git = `ekf.yaml imu0: /imu/data_raw` + corriger le commentaire `drivers.launch.py`.
- **(B)** Déployé = firmware avec `USE_FAKE_MAG` DÉFINI → publie `/imu/data` direct (pas de /imu/mag),
  ce qui colle avec l'ekf `/imu/data`. Le MPU6500 n'ayant **pas de magnéto**, c'est le cas physiquement
  logique. → Fix git = **définir `USE_FAKE_MAG`** dans `lino_base_config.h` (et alors mes docs de cette
  session disant « /imu/data_raw + /imu/mag » seraient À CORRIGER en « /imu/data »).

## Comment trancher (30 s sur le robot)
Robot allumé + agent lancé : `ros2 topic list | grep imu`.
- Si `/imu/data_raw` **et** `/imu/mag` apparaissent → cas (A) → repointer l'ekf sur `/imu/data_raw`.
- Si seulement `/imu/data` (pas de `/imu/mag`) → cas (B) → définir `USE_FAKE_MAG` + docs à corriger.
Vérifier aussi qu'un node `imu_filter_madgwick` ne tourne pas (`ros2 node list`).

**NE PAS corriger à l'aveugle** (comme la géométrie, ça a failli partir dans le mauvais sens).
Détail : audit du 2026-07-08. Cf [[amr-imu-gyro-bias-boot]], [[amr-wheel-geometry]].
