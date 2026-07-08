---
name: amr-nav-accel-deadlock
description: "Nav qui ne bouge PAS / cmd_vel bloqué à 0.025 rad/s = deadlock limite d'accélération × plancher de stiction ; fix = monter acc_lim ; démasqué en corrigeant le biais gyro"
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-06 — LE bug "le robot ne bouge pas / calcule 50 ans".** `cmd_vel` reste bloqué à
`angular.z = 0.025`, `linear.x = 0` en boucle, 0 progrès, recovery à répétition.

## Cause = deadlock accélération × stiction
- `0.025 = acc_lim_theta (0.5) × période contrôleur (0.05s @ 20Hz)`. C'est la vitesse MAX que DWB
  peut commander au **1er cycle depuis l'arrêt** (limite d'accél).
- Robot à l'arrêt → vitesse mesurée 0 → DWB ne peut sampler que `0 ± acc×dt` = ±0.025 → commande 0.025
  → **sous le plancher de stiction moteur (~0.15 rad/s)** → roues ne tournent pas (cible rpm=0 sur
  `/debug/left|right`) → mesuré reste 0 → **boucle infinie**.

## Pourquoi ça "marchait avant" puis plus
Le **biais gyro** (-0.31 rad/s, cf [[amr-imu-gyro-bias-boot]]) donnait une vitesse angulaire mesurée
≠ 0 → DWB samplait autour de -0.31 et sortait du deadlock (bougeait, lentement/salement). **Corriger
le gyro a DÉMASQUÉ le deadlock d'accél.** Deux bugs qui se compensaient.

## FIX = monter les accélérations pour que le 1er cycle dépasse le plancher
Dans `nav2_params.yaml` (FollowPath + velocity_smoother) :
- `acc_lim_theta 0.5 → 3.0` (1er cycle 0.15 = plancher), `acc_lim_x 0.5 → 1.0`, `max_angular_accel 3.0`.
- Équilibrage anti-nervosité : `decel_lim_theta -2.0 → -3.0` ; garder vitesses calmes `max_vel_x 0.20`
  `max_vel_theta 0.5` (mettre 4.0/1.0 rendait le freinage dur).
- **CES PARAMS DWB NE SE RÈGLENT PAS À CHAUD** (`ros2 param set` ne prend pas) → **éditer le YAML +
  RELANCER** le bring-up. Sur le Pi c'est `openamr-platform-sw/.../nav2_params.yaml` en **src ET build**
  (install = symlink vers build).
- Plancher moteur mesuré : linéaire ~0.04, angulaire ~0.15 ([[amr-min-velocity-floors]]).

Le vrai fix propre serait un plancher de vitesse sur `cmd_vel` (sigma-delta comme le docking), mais
monter l'accél suffit. Cf `docs/history/2026-07-06-nav-gyro-ui.md`.
