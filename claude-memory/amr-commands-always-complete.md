---
name: amr-commands-always-complete
description: "Préférence forte : TOUJOURS donner les commandes complètes (source+export+config), jamais rviz2 seul ni de placeholder 'bloc de sourcing'"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

L'utilisateur veut **TOUTES les commandes en entier, à chaque fois** — aucun raccourci, aucun
placeholder type « colle le bloc de sourcing ». Chaque bloc de commande doit être copiable tel quel.

**RViz : PLUS JAMAIS `rviz2` tout seul.** Toujours donner la commande complète, avec config chargée :
```bash
source /opt/ros/jazzy/setup.bash
source ~/Documents/openAMRobot/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
(le `-d ...openamr_nav.rviz` ouvre RViz avec Map + LaserScan déjà ajoutés → rien à faire à la main ;
`rviz2` seul ouvre un RViz vide = inutile et énervant pour lui.)

**Why:** il s'est énervé plusieurs fois (2026-06-25) parce que je redonnais `rviz2` nu ou « bloc de
sourcing » à compléter. Il bosse en multi-terminaux SSH→Pi et veut copier-coller direct.

**Pas de `iboot.sh` / scripts maison pour lancer** : il veut les **commandes ROS classiques en terminaux
séparés** (un `ros2 launch` par terminal). Il a explicitement rejeté `bash ~/iboot.sh &`. Donner :
real_bringup (T1) → localization_launch map:=... (T2) → navigation_launch use_scan_filter:=false (T3) →
`ros2 run topic_tools relay /goal_pose /goal_pose_nav` (T4) → RViz (PC). Chaque terminal Pi commence par
`ssh botshare@172.17.201.29` **seul** (mot de passe interactif), puis le sourcing, puis le launch.

**How to apply:** sur le **Pi** (on lance des nœuds) = sourcer les 4 workspaces (jazzy + linorobot2_ws +
camera_ws + openamr-integration) + `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` + `ROS_DOMAIN_ID=0`. Sur le
**PC** (RViz/visu) = `source /opt/ros/jazzy/setup.bash` (+ platform-sw/ros2/install optionnel) + les 2
exports + `rviz2 -d <config>`. Toujours inclure le sourcing ET les exports dans CHAQUE bloc, même si
répétitif. Voir [[amr-pi-ros-commands]], [[amr-nav2-bringup]].