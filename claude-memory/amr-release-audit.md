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

## ✅ Commit linorobot2 ÉPINGLÉ (2026-07-08, retrouvé par diff — TODO NOTICE.md fermé)
Base FW identifiée par comparaison des 3 fichiers overlay à TOUT l'historique de `linorobot/linorobot2_hardware` :
**branche `jazzy`, commit `aaf9d59cd18c0cd1905be6fdae9ea5c99961a766` (2026-04-30)** = HEAD au démarrage projet
(juin 2026) ; fichiers source dernière modif upstream à `36ffb76d` (2026-04-10, "Add support for ESP32 Wifi").
Preuve : l'écart résiduel = exactement les valeurs par défaut linorobot2 que l'utilisateur a remplacées
(K_P 0.6→2.0, WHEEL 0.152→0.2, LR_WHEELS 0.271→0.46, COUNTS 144000→1024, MOTOR1_PWM swap 21→1 suivant le
conseil inline upstream). NOTICE.md + overlay README **mis à jour en local** (pas encore committés).

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

## Audit PROFESSIONNALISME des docs (2026-07-08) — fait, verdict OK
Globalement **professionnel** : structure/profondeur OK, pas de français résiduel, build artifacts
(`install/build/log`) bien gitignorés, meta files complets, placeholders honnêtement déclarés.
Points relevés, **volontairement NON corrigés (choix utilisateur : garder la voix ingénieur honnête)** :
- Ton « journal de dev » dans `power.md` HW (« for nothing », « end of session », « a whole session ») — ASSUMÉ.
- Sections `## TODO` dans power.md / camera.md HW (pourraient être « Open items »).
- ⚠️ 2 vrais défauts (pas du ton) laissés en l'état sur demande : chemin PERSO `~/Documents/openamr` dans
  FW `docs/architecture/encoder-calibration.md` ; lien cassé `openamrobot_docking/docs/09_troubleshooting.md`
  → `../../CONTRIBUTING.md` (mauvaise profondeur, devrait être `../../../../`). À fixer si un jour souhaité.

## 🔧 À FAIRE (reprise — 2026-07-08, plus tard dans la journée)
1. **Vendorer les scripts de calibration encodeur dans `openamr-platform-fw`.** `align_enc_cal.py`,
   `apply_enc_cal.py`, `encoder_ref_table.json`, `calibrate_and_apply.sh` sont **UNIQUEMENT** dans le
   repo notes (`~/Documents/openamr/scripts/`), dans AUCUN repo de release. Or la doc FW
   `docs/architecture/encoder-calibration.md` en DÉPEND (calib par boot, à relancer après chaque
   power-cycle Teensy) → un utilisateur de release ne peut pas les obtenir. Les copier dans
   `openamr-platform-fw` (ex. `tools/encoder-calibration/`) + brancher la doc dessus. **NE PAS les
   supprimer du repo notes** (actifs).
2. **Ménage code repo notes (en attente de décision).** Candidats redondants avec les repos de release :
   `firmware/` (⊂ platform-fw), 11 scripts diagnostics (⊂ platform-sw tools/diagnostics), `config/`+`launch/`
   (⊂ platform-sw). ⚠️ `firmware/`+`launch/` = ce que `deploy_to_pi.sh`/`apply_overlay.sh` déploient sur le
   Pi → ne retirer QU'APRÈS avoir migré le workflow de déploiement vers les repos platform. **Demander avant
   de supprimer** (consigne utilisateur, repo précieux).

## 📐 Diagrammes — HW FINI (11/11), reste 7 (FW+SW)
Checklist complète : [[amr-diagrams-todo]]. **HW = 11/11 FAIT** (câblage + capteurs imu/lidar/camera,
générés + vérifiés AVEC l'utilisateur 08-07, committés+poussés sur `feature/hardware-audit`, PR HW ouverte).
Reste **7** : **FW** (4: control-loop, micro-ros-bringup, debug-telemetry, encoder-calibration — prompts
déjà rédigés dans les docs, exacts, prêts à générer) + **SW** (3: networking-DDS, collision-monitor,
vision-pipeline). Workflow : ouvrir le doc → copier le prompt du commentaire → générer
→ remplacer le bloc placeholder par `![...](diagrams/<slug>.svg)` → vérifier fond blanc + dims + 0 prompt.
**Données câblage = FIABLES** (pins = firmware `lino_base_config.h`, audit physique VERIFIED 2026-06-19,
recroisé) → générer sans re-vérifier. SEUL point à confirmer sur la carte si fidélité parfaite voulue :
l'ordre exact des 12 bornes driver + label RS485 inutilisé (A+/B- vs B+ lu). Diagrammes FW/SW = logiques
(dérivés du code, rien à mesurer).

## 🌿 À FAIRE (reprise) — nettoyer les branches du fork SW
Le fork `openamr-platform-sw` a **8 branches** ; objectif = **3-5 PR + main**. À GARDER : `main`,
`feature/real-robot-bringup` (PR1), `feature/docking` (PR2), `feature/real-robot-docs-pr` (PR3),
`fix/sim-wheel-geometry` (PR4 potentielle, en attente re-test sim). **Les 3 en trop (non-PR)** :
- `local/test-all` — branche d'intégration (72 commits), PAS une PR. **Copie locale existe** → retirable
  du fork sans risque (`git push origin --delete local/test-all`).
- `matthieu/bundle-docking` (62 commits) + `matthieu/contribution` (10 commits) — **vieilles branches perso**
  d'avant l'intégration. ⚠️ Les retirer du fork = **les PERDRE** si pas de copie locale. **DEMANDER à
  l'utilisateur** avant (ce sont ses branches historiques, précieuses). Vérifier `git branch` local d'abord.

## Autres chantiers en cours (rappels)
- [[amr-diagrams-todo]] : 15 diagrammes à générer (placeholders posés, prompts inclus).
- Docking = priorité de Matthieu pour la démo (Vendredi). Nav + UI = OK/contents.
- Fix `robot.sdf` = branche à part, PAS dans les PR de release tant que sim pas re-testée.
