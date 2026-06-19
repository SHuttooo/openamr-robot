---
name: amr-nav2-bringup
description: "Recette Nav2+AMCL réel qui MARCHE (2026-06-19) + tous les pièges (filtre doublon, teleop, outil RViz, footprint, obstacle_min_range)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Nav2 + AMCL fonctionnent sur le robot réel (2026-06-19).** Localisation AMCL sur carte `coin2`, nav
autonome (plan global + DWB + évitement temps réel). Détails complets : docs/software/navigation.md.
Pré-requis : [[amr-pi-ros-commands]] (SSH, env Cyclone, agent). Carte : `~/maps/coin2.*` (+ repo maps/).

## Séquence de lancement (sur le Pi, env sourcé : jazzy + linorobot2_ws + camera_ws +
## openamr-platform-sw/ros2/install + RMW cyclonedds)
1. `ros2 launch /home/botshare/openamr_real_bringup.launch.py`  (agent, lidar, scan filter, EKF, caméra, TF)
2. `ros2 launch openamrobot_nav2 localization_launch.py map:=/home/botshare/maps/coin2.yaml use_sim_time:=false`
3. `ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false`
   (controller sort sur **/cmd_vel_raw** ; filtre scan doublon RETIRÉ du launch → plus besoin de le tuer)
4. `ros2 launch /home/botshare/collision_monitor_launch.py`  ← Collision Monitor (sécurité, voir plus bas)
5. `python3 ~/goal_relay.py`  (repo scripts/goal_relay.py) ← relais /goal_pose → action navigate_to_pose
Puis RViz (PC) : **2D Pose Estimate** (localiser) → **2D Goal Pose** (but). PAS « Nav2 Goal ».

## COLLISION MONITOR (sécurité « ne touche jamais ») — ACTIF
Chaîne : `controller → /cmd_vel_raw → collision_monitor → /cmd_vel → Teensy`. Le monitor (`FootprintApproach`,
source `/scan_filtered`, empreinte réelle 78×58) **projette l'empreinte et arrête le robot avant tout
contact**, indépendamment de l'inflation (qui est donc basse, 0.10, juste pour la planif). Config dans
nav2_params `collision_monitor:` (cmd_vel_in `cmd_vel_raw`, `time_before_collision: 0.8`, min_range 0.10).
Launch : `~/collision_monitor_launch.py` (repo launch/collision_monitor_launch.py). Le remap
`cmd_vel→cmd_vel_raw` est dans le `remappings` partagé de navigation_launch.py.

## PIÈGES (chacun a coûté du temps)
1. **Doublons de process** (agents/lidars/EKF en multiple, à force de relancer) → conflits série/USB/TF →
   tout devient instable. TOUJOURS clean-kill + UN seul launch. (pgrep sur-compte à cause du wrapper
   `ros2 run` → vérifier `ps -ef`.)
2. **`/scan_filtered` en double** : navigation_launch lance SON `laser_filters` (scan_to_scan_filter_chain,
   nommé scan_body_filter) qui entre en conflit avec notre `scan_body_filter.py` → 2 publishers → obstacles
   faux. **`pkill -9 -f scan_to_scan_filter_chain` à chaque fois.**
3. **RViz « Nav2 Goal » ne fait RIEN** (le GoalTool a besoin du panneau Navigation2) → utiliser
   **« 2D Goal Pose »** (publie /goal_pose) + lancer **`goal_relay.py`** qui le convertit en action.
4. **Teleop en conflit** : teleop_twist_keyboard (avec repeat_rate) inonde /cmd_vel avec sa dernière
   commande (0) à 10 Hz → écrase Nav2. **Tuer la teleop avant Nav2.**
5. **`obstacle_min_range: 0.35` aveugle les obstacles proches** → ils disparaissent de la costmap quand le
   robot approche → il fonce dedans. Mettre **0.10** (le scan_body_filter enlève déjà la coque).
6. **SmacPlanner2D lent** avec footprint non-circulaire + faible inflation (il prévient). Passer à **NavFn**
   (`nav2_navfn_planner::NavfnPlanner`) si lent (mais NavFn = robot ponctuel → besoin inflation ≈ rayon
   inscrit ~0.29). DWB qui serpente : RPP testé mais **bloqué en rotation sur place** → gardé DWB.
7. **« Failed to make progress »** = le contrôleur n'avance pas (RPP bloqué, ou chemin infaisable car
   inflation trop basse pour le gros robot).

## RÉGLAGES CLÉS (réglables à chaud, sans redémarrer)
- **Footprint réel** (robot 0.78×0.58, coins arrondis, base_link décalé : avant 0.415 / arrière −0.365) —
  PAS `robot_radius` (qui était 0.22 = cercle 44 cm trop petit → il rasait les obstacles) :
  `ros2 param set /local_costmap/local_costmap footprint "[[0.415,0.19],[0.415,-0.19],[0.315,-0.29],[-0.265,-0.29],[-0.365,-0.19],[-0.365,0.19],[-0.265,0.29],[0.315,0.29]]"` (idem global).
- Vitesse : `ros2 param set /controller_server FollowPath.max_vel_x 0.16` (max_vel_theta 0.7).
- Inflation : `ros2 param set /local_costmap/local_costmap inflation_layer.inflation_radius 0.15` (idem global).
- Clear : `ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"`.
- Snapshot config qui marche : repo `config/nav2_params_real.yaml`.

## CONCEPT : inflation ≠ évitement
- **Inflation** (le bleu) = coût DOUX de planification, traversable. Ne garantit PAS le non-contact.
- **Ne pas toucher** = le contrôleur teste l'EMPREINTE vs costmap locale en temps réel (besoin
  obstacle_min_range petit). Garantie DURE « ne touche jamais » (à faire) : **Collision Monitor**
  (zone stop = footprint+marge) ou **élargir le footprint** de quelques cm.

Cf [[amr-session-suite-nav2-cyclone]], [[amr-pi-ros-commands]], [[amr-encoder-5v-overvoltage]].
