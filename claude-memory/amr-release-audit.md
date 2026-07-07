---
name: amr-release-audit
description: "État de l'audit de cohérence 'première release' (2026-07-08) : ce qui est OK, ce qui est corrigé, et les décisions OUVERTES à reprendre (topic IMU, rayon roue sim, version v0.01, doc release d'Alex)."
metadata:
  node_type: project
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-08 — Gros audit de cohérence transverse (FW/HW/SW) pour la 1re release. Mis de côté ici.**

## ✅ Vérifié cohérent (ne pas re-auditer)
Pins FW config ↔ HW wiring (match exact) ; odométrie `/odom/unfiltered`→EKF→`/odom` ; géométrie FW/HW
(Ø0.2/voie0.46) ; meta files (LICENSE/NOTICE/AUTHORS/CHANGELOG/SECURITY/CONTRIBUTING) non vides dans les
3 repos ; part numbers (moteur Z4BLD60 / driver ZBLD.C20-120L2R / AS5040 / MPU6500 / RPLIDAR A1 / IMX708)
cohérents ; tensions 3.3V (AS5040/IMU) ; copyright OpenAMRobot 2026 ; aucun secret/credential leaké.

## ✅ Corrigé et poussé pendant l'audit
- HW : 6 refs cross-repo cassées (`firmware/xxx.md (see openamr-platform-fw…)`) → refs propres (commit `8c9e034`).
- HW : serial Teensy `16778200` labellisé "reference unit".

## 🔴 DÉCISIONS OUVERTES (à reprendre)
1. **Topic IMU — le seul vrai bug.** Firmware git publie `/imu/data_raw`+`/imu/mag` mais l'EKF lit
   `/imu/data` (rien ne le produit). Déployé ≠ git. **Trancher sur le robot** : `ros2 topic list | grep imu`.
   Détail + les 2 fixes possibles : [[amr-imu-topic-contract]]. NE PAS corriger à l'aveugle.
2. **Rayon roue en simulation.** Mon fix `robot.sdf` (branche `fix/sim-wheel-geometry`) met le diff-drive
   à 0.10, MAIS `gazebo_control.xacro` + le visuel URDF disent encore **0.11** ≠ 0.10 mesuré. À aligner à
   0.10 (avec re-test sim, car ça change la sim). Cf [[amr-wheel-geometry]]. **Sim toujours utilisée** (démos).
3. **Version v0.01.** Aucune version déclarée nulle part. Ajouter une entrée `## [0.01]` aux CHANGELOG des
   3 repos + tag git. Lié au point 4.
4. **Doc release d'Alex (demandée, PAS encore écrite).** Alex veut un texte pro/concis pour le canal commun :
   *ce qu'est une release + comment en faire une correctement*, cadré **v0.01** (SemVer, tag, checklist).
   À rédiger en anglais, prêt à coller.

## Autres chantiers en cours (rappels)
- [[amr-diagrams-todo]] : 15 diagrammes à générer (placeholders posés, prompts inclus).
- Docking = priorité de Matthieu pour la démo (Vendredi). Nav + UI = OK/contents.
- Fix `robot.sdf` = branche à part, PAS dans les PR de release tant que sim pas re-testée.
