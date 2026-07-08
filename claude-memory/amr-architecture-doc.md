---
name: amr-architecture-doc
description: Doc de référence unique de toute la structure projet + décision migration lancement réel
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

`docs/reference/ARCHITECTURE.md` (dans le repo instance `openamr`) est LE document de référence unique qui
explique toute la structure : les 3 ensembles de code (plateforme `openamr-platform-sw` / instance
`openamr` / firmware `linorobot2_hardware`), les 8 packages, les 18 launch + graphe d'inclusion, la
règle du transmetteur de but, le flux de données (TF/topics sim vs réel/firmware/docking), et un
**audit** §6 (doublons/divergences/docs périmées). Créé/à jour 2026-06-26.

**Décision (2026-06-26) — migrer le lancement réel vers platform-sw** : `bringup.launch.py
sim:=false` devient LE lancement réel, `nav2_params.yaml` (platform-sw) fait foi. L'ANCIEN système
(`openamr/launch/openamr_real_bringup.launch.py` + `openamr/config/nav2_params_real.yaml` +
`scripts/bringall.sh`) est à marquer legacy puis supprimer après validation robot. **Pas encore
appliqué** — plan détaillé dans §6 de ARCHITECTURE.md.

**Actualisation des autres docs (visualization.md=FastDDS périmé, navigation.md=docking TODO périmé,
bringup.md, running-the-robot.md) : reportée**, à faire plus tard (l'utilisateur a choisi « juste
l'audit pour l'instant »).

Voir [[amr-nav2-bringup]] (la recette de lancement) et [[amr-next-session-plan]].
