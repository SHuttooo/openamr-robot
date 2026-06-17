---
name: amr-dev-workflow
description: "Environnement de dev/visu du projet AMR (Pi headless, visu, dépôt git)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

**Le Pi est headless** (Ubuntu Server, pas de bureau) → on n'y lance NI RViz NI Gazebo. ROS 2 tourne
sans GUI ; on calcule sur le Pi et on visualise à distance. Gazebo = simulation uniquement, inutile sur
le vrai robot.

**Options de visualisation :**
- **Foxglove** : `foxglove_bridge` sur le Pi (websocket :8765) + Foxglove Studio sur Windows → voir
  /scan, TF, carte en direct **sans rebooter** (on reste sous Windows, donc avec Claude). PAS encore installé.
- **Ubuntu dual-boot** (sur le même PC que Windows) : ROS 2 Jazzy + RViz/Gazebo natifs, voit les topics du
  Pi si même `ROS_DOMAIN_ID` + même RMW + même réseau. MAIS sous Ubuntu on perd l'accès à Claude (qui tourne
  côté Windows). Donc : Foxglove pour bosser AVEC Claude ; Ubuntu pour de la visu approfondie en solo.

**Dépôt git (privé)** : `https://github.com/SHuttooo/openamr-robot` (compte gh = SHuttooo). Contient
`docs/`, `scripts/`, `launch/`, `firmware/` (overlay = nos 3 fichiers modifiés du firmware), et une copie
**caviardée** de cette mémoire dans `claude-memory/`. Le gros clone `linorobot2_hardware` et `.claude` sont
git-ignorés. ⚠️ **Aucun secret dans le repo** : le mot de passe du Pi est retiré des docs (voir [[pi-ssh-access]]
en local pour le vrai mot de passe).

**Reprendre Claude sur une autre machine (ex. Ubuntu)** : installer Claude Code, cloner le repo ; le contexte
est dans `docs/` + `claude-memory/`. Pour la recall auto, copier `claude-memory/*` dans
`~/.claude/projects/<id>/memory/` de la nouvelle install.
