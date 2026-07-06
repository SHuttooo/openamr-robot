---
name: amr-next-session-plan
description: "Point de reprise (au 2026-07-06) — ce qu'il reste à faire. À relire au début de chaque session."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Point de reprise au 2026-07-06 (fin de session robot).** Ce qui MARCHE + ce qui RESTE.

## ✅ Ce qui marche maintenant (fait, ne pas refaire)
- **Nav débloquée** : le deadlock 0.025 rad/s est réglé ([[amr-nav-accel-deadlock]]).
- **Dérive gyro réglée** ([[amr-imu-gyro-bias-boot]]).
- **Cooler** : Pi à 47 °C, plus de throttling.
- **UI opérateur MARCHE** : waypoints + blocs (React+rosbridge dockerisée, Cyclone/domain 0) [[amr-ui-operator]].
- Doc du jour avec TOUTES les commandes : `docs/2026-07-06-session-robot-nav-gyro-ui.md`.

## ⏳ Priorité 1 : committer le fix nav (BESOIN DU PI ALLUMÉ)
Le fix accel de `nav2_params.yaml` est **sur le SSD du Pi** (src+build, persiste) mais **PAS committé** en git.
Ses valeurs sont dans la doc du jour + [[amr-nav-accel-deadlock]] :
`acc_lim_theta 3.0, acc_lim_x 1.0, max_angular_accel 3.0, decel_lim_theta -3.0, velocity_smoother
max_accel [1.0,0,3.0] / max_decel [-2.5,0,-3.0]`, garder `max_vel_x 0.20 / max_vel_theta 0.5`, downsample true.
- ⚠️ **Git de nav2_params EMMÊLÉ** : la branche `feature/nav2-real-tuning` a une config **SIM** (max_vel_theta 2.0,
  valeurs gazebo) ≠ la config validée du Pi ; du reverti-sim non-committé traîne sur le checkout `local/test-all`.
- **À faire (Pi allumé)** : récupérer `~/openamr-platform-sw/ros2/src/openamrobot_nav2/config/nav2_params.yaml`
  du Pi, démêler quelle branche doit porter le vrai tuning réel, committer au bon endroit. NE PAS committer la sim.

## ⏳ Priorité 2 : les PR du chantier doc (préparées, pas poussées)
`docs/PR-PLAN-2026-07-06.md` (8 PR) + `docs/RESUME-doc-chantier-2026-07-06.md`. Branches déjà committées :
FW `feature/teensy-4-0-linorobot2-overlay`, HW `feature/hardware-audit`, SW docs `feature/real-robot-docs`,
+ 6 branches SW code. **Reste** : pousser sur le fork `origin` (l'utilisateur ouvre les PR, pas d'accès upstream) ;
neutraliser le commentaire "roue" dans nav2_params ; indexer les docs SW (navigation/safety/real_robot) dans le README ;
base propre pour la PR docs (cherry-pick sur upstream/main) ; nettoyer le worktree `scratchpad/wt/sw-docs`.

## ⏳ Priorité 3 : robot
- **Tester le docking** bout-en-bout (préparé, pas relancé après le dernier reboot) — [[amr-docking-bundle-setup]].
- **Démo Alex** (voix → blocs → robot vers Station 4) — l'UI marche, à enregistrer.

## Démarrage session (rappels)
- Rallumer le Pi **robot IMMOBILE** (biais gyro capturé au boot) ; après power-cycle Teensy → **refaire la
  calib encodeur** (`align_enc_cal.py --arm 250`, roues en l'air).
- Lancer depuis **`openamr-platform-sw`** (config rapide), PAS `openamr-integration` (config lente).
- Params DWB (accel/vitesse) **PAS réglables à chaud** → éditer le YAML + relancer.
- Toutes les commandes : `docs/2026-07-06-session-robot-nav-gyro-ui.md`, [[amr-pi-ros-commands]], [[amr-nav2-bringup]].
- Commits sans mention Claude [[amr-commit-no-claude]] ; commandes complètes copiables [[amr-commands-always-complete]].
