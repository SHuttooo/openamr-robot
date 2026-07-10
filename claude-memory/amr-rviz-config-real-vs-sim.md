---
name: amr-rviz-config-real-vs-sim
description: "RViz robot RÉEL = openamr_nav.rviz (pas nav2_view.rviz qui est la config SIM) ; le mesh robot dépend de robot_state_publisher, absent du bring-up réel"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Le repo platform-sw a **deux** configs RViz nav2, chacune pour un contexte — ne PAS les confondre :

- **`openamrobot_nav2/rviz/openamr_nav.rviz`** = **ROBOT RÉEL**. C'est celle documentée dans
  `docs/real_robot/01_bringup.md`. Contient : Map, LaserScan (`/scan_filtered`), **2 Path**
  (`/plan` + `/local_plan`), **Polygon** (empreinte), RobotModel (`/robot_description`). Identique
  (byte-à-byte) à la copie perso de l'utilisateur `~/Documents/openamr/scripts/openamr_nav.rviz`
  (celle qu'il lance tout le temps). **C'est CELLE-CI qu'il faut donner pour un test réel.**
- **`openamrobot_nav2/rviz/nav2_view.rviz`** = **SIMULATION**. Câblée dans
  `sim_bringup_launch.py`. Pas de display Path. NE PAS la proposer pour le robot réel.

Commande réel :
```bash
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```

**Piège du mesh 3D robot :** le RobotModel lit `/robot_description`, publié par
`robot_state_publisher` — **qui n'est lancé QU'EN SIM** (dans `bringup.launch.py` il n'apparaît que
sous `sim:=true`). Sur le robot réel il y a donc **0 publisher** de `/robot_description` → **pas de
mesh robot dans RViz** (le lidar, le chemin, l'empreinte, la carte marchent quand même). Ce n'est
PAS un problème de WiFi ni de config RViz — c'est le nœud qui n'est pas dans le bring-up réel. Pour
avoir le mesh il faut lancer `robot_state_publisher` séparément. Voir [[amr-nav2-bringup]],
[[amr-platform-sw-prs]].

Leçon méthodo : pour une commande de test RÉEL, lire `docs/real_robot/*` du repo AVANT de choisir un
fichier par son nom (j'ai pris `nav2_view.rviz` = sim au lieu de `openamr_nav.rviz` = réel, ~1 h perdue).
