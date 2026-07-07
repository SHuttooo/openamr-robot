---
name: amr-platform-sw-prs
description: "État GitHub openamr-platform-sw au 2026-07-07 : CONSOLIDÉ en 3 PR propres poussées sur le fork SHuttooo vers openAMRobot:main (real-robot-bringup, docking en DERNIER, docs). Les 8 anciennes feature-branches ont été fusionnées puis supprimées du fork (gardées en local). Contenu byte-vérifié == local/test-all + correcteur validé."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Repo `openamr-platform-sw`** (`~/Documents/openAMRobot/openamr-platform-sw`). Remotes : `origin`=SHuttooo
(fork, on push ici), `upstream`=openAMRobot (cible des PR), `raj`=rajindulkar22 (reviewer).
Claude n'a PAS accès upstream ni au CLI `gh` → **c'est l'utilisateur qui ouvre les PR**.

## 2026-07-07 : CONSOLIDÉ de 8 → 3 PR (demande utilisateur « moins de PR », « docking à la fin »)
Sur le fork il ne reste QUE ces 3 branches PR (+ `main`, `local/test-all`, `matthieu/*`) :

1. **feature/real-robot-bringup** — PR1. Tout ce qui fait rouler/percevoir le robot HORS docking :
   perception (scan body filter + cap caméra 15fps) + bringup sim/real + drivers + nav2 (tuning réel
   validé, RotationShimController, **fix accel anti-deadlock** [[amr-nav-accel-deadlock]]) + vision-composition
   (launches intra-process) + diagnostics. 5 commits logiques. Base = `upstream/main`.
2. **feature/docking** — PR2, **à merger EN DERNIER**. Gate apriltag on-demand [[amr-apriltag-on-demand-gate]]
   + dock normal robot-frame + **le correcteur NEAR réécrit ce soir et validé "c'est aligné"** (dt réel,
   compensation profondeur, moyennage pondéré) + autofocus continu (`camera.launch.py`) + doc legacy.
   16 commits. Base = `upstream/main`. Touche aussi `camera.launch.py` (ajoute autofocus par-dessus le
   fps cap de PR1 → merge sans conflit).
3. **feature/real-robot-docs-pr** — PR3, docs-only indépendante (navigation/safety/real_robot + index README).
   Base = `upstream/main`, cherry-pick propre.

**Ouvrir les PR** : `https://github.com/openAMRobot/openamr-platform-sw/compare/main...SHuttooo:<branche>`.

## Filet de sécurité (rollback docking demandé par l'utilisateur)
- Tag **`docking-legacy-pre-2026-07-07-near-approach`** poussé sur le fork = snapshot exact du `dock_trigger.py`
  AVANT la réécriture de ce soir.
- Doc **`ros2/src/openamrobot_docking/docs/15_legacy_near_approach.md`** (dans PR2) = explique l'ancienne
  méthode NEAR + comment revenir en arrière. Gardée, pas utilisée par le code.

## Les 8 anciennes branches granulaires
Fusionnées dans les 3 PR puis **supprimées du fork** (perception-scan-body-filter, real-bringup, nav2-real-tuning,
vision-composition, diagnostics, docking-apriltag-gate, docking-near-approach, real-robot-docs, +
fix/docking-near-servo-af). **Toujours présentes en LOCAL** comme backup. Vérif de complétude faite :
0 orphelin, PR1 byte-identique à `local/test-all`, PR2 == correcteur validé.

## Méthode / garde-fous
Consolidation par `git checkout <branche-source> -- <fichiers>` sur une branche neuve off `upstream/main`,
puis cherry-pick du correcteur. **Piège rencontré** : `feature/nav2-real-tuning` distante portait une config
SIM périmée (max_vel_theta 2.0, pas de RotationShimController) ≠ config réelle validée → toujours vérifier le
SENS du diff (`git diff origin/<b> <b>`) avant un force-push. `local/test-all` = intégration testée (PAS une PR).
Commits sans mention Claude [[amr-commit-no-claude]]. PAS de force-push destructif [[amr-commit-no-claude]].
