---
name: amr-project-docs
description: Emplacement et structure de la documentation projet AMR (onboarding étudiant)
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

Doc d'onboarding du projet AMR, **en anglais**, dans `Documents/projet/openamr/docs/` (21 fichiers .md).
Structure "par composant + vue d'ensemble" : `README.md`, `00-overview.md`, `01-communication.md`
(carte précise des comms : bus/protocoles/baud/topics+types+frames), `hardware/` (raspberry-pi, teensy,
motors-drivers, encoders, imu, lidar, camera, power, wiring-pinout), `firmware/` (firmware, control-loop-pid,
debug-telemetry), `software/` (ros-architecture, bringup, navigation), `procedures/` (running-the-robot, safety),
`history/diagnostics.md` (le "pourquoi").

À TENIR À JOUR quand on avance (chaque fichier a une ligne "Last updated"). Navigation/docking = fiche-plan
légère qui renvoie au guide `~/openamr_hardware_bringup_guide` (déjà détaillé), à étoffer plus tard.

**Le projet est sur GitHub privé** : `https://github.com/SHuttooo/openamr-robot`. Réorganisé en
`docs/`, `scripts/` (diag + odom_tf_relay), `launch/` (bringup), `firmware/` (overlay des 3 fichiers
modifiés). Le clone `linorobot2_hardware` et `.claude` sont git-ignorés. Workflow/visu/git : [[amr-dev-workflow]].
Voir [[amr-real-bringup]].
