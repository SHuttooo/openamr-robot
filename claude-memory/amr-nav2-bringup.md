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

## MARGE D'ÉVITEMENT « ne pas s'approcher à <10-20 cm » — EMPREINTE ÉLARGIE (2026-06-20)
Mécanisme retenu = **empreinte (footprint) élargie de +0.12 m** dans les DEUX costmaps (persisté
nav2_params.yaml). DWB teste l'empreinte vs costmap locale à chaque cycle → empreinte +12cm = règle
**DURE** « jamais à moins de ~12 cm d'un obstacle vu par le lidar » (bien plus fort que l'inflation, qui
n'est qu'un coût de planif doux). Empreinte élargie (à set sur local+global) :
`[[0.535,0.31],[0.535,-0.31],[0.435,-0.41],[-0.385,-0.41],[-0.485,-0.31],[-0.485,0.31],[-0.385,0.41],[0.435,0.41]]`
+ inflation 0.20 (le planificateur s'écarte aussi de ~20 cm). ⚠️ empreinte élargie = robot « plus gros » →
dans un espace très serré Nav2 peut ne plus trouver de chemin (réduire le pad à +0.10).
**Collision Monitor : PAS actif** (testé, il bloquait le robot → abandonné au profit de l'empreinte élargie).

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
   robot approche → il fonce dedans. Mettre **0.0** (le scan_body_filter enlève déjà la coque ; NE PAS en
   remettre — demande explicite de l'utilisateur).
8. **COSTMAPS VIDES → robot AVEUGLE → percute tout (2026-06-20, gros piège)** : si on lance
   `navigation_launch` AVANT que AMCL publie `map→odom` (pas de 2D Pose Estimate), le lifecycle des costmaps
   **abort**. Si on **active les nœuds À LA MAIN** (`ros2 lifecycle set ... activate`) ils montent **mal
   initialisés** : static layer ne charge pas la carte, obstacle layer ne s'abonne pas au scan → **les deux
   costmaps = 0 cellule occupée** → rien à éviter → fonce « de plein fouet ». FIX : lancer la nav SEULEMENT
   après `map→odom` (2D Pose Estimate d'abord), laisser le lifecycle_manager activer seul ; sinon RELANCER
   (ne jamais hand-activate). Vérif : `ros2 topic echo /global_costmap/costmap --field data --once` doit
   avoir des cellules ≠0/≠-1 (on a eu 36041 global / 3602 local une fois réparé).
9. **« le robot ne bouge plus » = quasi toujours le 24 V** (batterie off/déchargée), pas Nav2. Prouver avec
   un `/debug/openloop` direct (rpm) AVANT de debugger la nav.
10. **Lidar 2D à ~18 cm = angle mort vertical** : obstacle < ~18 cm de haut = INVISIBLE costmap → ni
    inflation ni empreinte élargie ne l'évitent (rien dans la costmap). Pas de fix logiciel (capteur bas /
    pare-chocs requis). Tester l'évitement avec obstacles > ~20 cm.
6. **SmacPlanner2D lent** avec footprint non-circulaire + faible inflation (il prévient). Passer à **NavFn**
   (`nav2_navfn_planner::NavfnPlanner`) si lent (mais NavFn = robot ponctuel → besoin inflation ≈ rayon
   inscrit ~0.29). DWB qui serpente : RPP testé mais **bloqué en rotation sur place** → gardé DWB.
7. **« Failed to make progress »** = le contrôleur n'avance pas (RPP bloqué, ou chemin infaisable car
   inflation trop basse pour le gros robot).

## ÉVITEMENT D'OBSTACLES — CE QUI MARCHE (2026-06-20, après grosse session debug)
Trois bugs cumulés faisaient « il voit l'obstacle mais fonce dedans ». Tous corrigés :
1. **QoS scan : costmaps VIDES** = le filtre `scan_body_filter.py` publiait `/scan_filtered` en
   **BEST_EFFORT** mais la costmap s'abonne en **RELIABLE** → « incompatible QoS, No messages will be sent »
   → 0 obstacle. FIX : publier `/scan_filtered` en **RELIABLE** (sert costmap reliable ET AMCL best_effort).
   Vérif fiable de l'occupation : petit script rclpy (sub transient_local), PAS `ros2 topic echo --field data`
   (tronque/timeout sur gros tableau + QoS volatile → faux 0).
2. **DWB critic = `BaseObstacle` (CENTRE seulement)** → inadapté gros robot : l'avant dépasse de **0,53 m**
   du centre → l'avant percute avant que le centre approche. FIX : ajouter le critic **`ObstacleFootprint`**
   (`ObstacleFootprint.scale: 10.0`) qui teste **TOUTE l'empreinte** → refuse toute trajectoire où la forme
   touche. (critics rechargés seulement au (re)démarrage du controller_server, pas à chaud.)
3. **Inflation = même valeur global/local** → le plan global rasait les murs. FIX = **2 costmaps réglées
   DIFFÉREMMENT** (c'est natif Nav2, l'idée de Matthieu) : **GLOBAL inflation 0.40 / cost_scaling 2.5**
   (planif centrée, tient compte de la taille — planner = robot ponctuel donc inflation≈rayon) ;
   **LOCAL inflation 0.15** (fin) + `ObstacleFootprint` pour l'évitement dur. Curseur « centrage » = inflation
   GLOBAL (monter=plus centré/écarté, baisser=plus de passages serrés). L'évitement dur ne dépend PLUS de
   l'inflation (vient de ObstacleFootprint).
+ **RPLidar timeout au démarrage** (`Error operation time out`, `/scan` publisher 0) = bug récurrent →
  **débrancher/rebrancher l'USB du lidar** (aucun fix logiciel). `bringall.sh` le détecte et le dit.

## COSTMAP « No map received » dans RViz (≠ costmaps vides — 2026-06-25)
Planner_server **active**, map→odom OK, mais display Global/Local Costmap **orange « No map received »**,
aucun cyan/magenta. CAUSE = `always_send_full_costmap: False` (défaut) → grille complète envoyée **1 fois**
(latched/transient_local) puis deltas ; RViz connecté APRÈS ce one-shot, et sur **WiFi** le sample latché ne
se livre pas au late-joiner → jamais de grille. FIX PERSISTANT (nav2_params.yaml, local **et** global) :
**`always_send_full_costmap: True`** → republie la grille complète à chaque cycle (publish_freq 5/2 Hz),
coût réseau négligeable, RViz l'a toujours. À chaud : `ros2 param set /global_costmap/global_costmap
always_send_full_costmap true` (+ local) puis `clear_entirely_*_costmap`. Côté RViz : display costmap en
**Durability Transient Local + Reliability Reliable**, puis Ctrl+S. (Le lidar A1 qui **hang juste après
« RPLIDAR running… SDK 1.12.0 »** sans crash = firmware figé `80008000` → **débrancher/rebrancher USB**, le
pkill seul ne suffit pas ; un reboot Pi power-cycle aussi le lidar.)

## DIMENSIONS ROBOT (footprint) — vérifié 2026-06-20
Robot **0,78 × 0,58 m**. base_link (axe roues, centre rotation) PAS centré : **avant 0,415 m / arrière
0,365 m** (lidar à 0,335 m devant base_link via TF base_to_lidar + 0,08 m lidar→avant), demi-largeur 0,29.
Empreinte réelle puis ÉLARGIE +0,12 m (marge dure) cf section marge. ⚠️ à reconfirmer au mètre : axe→avant
(~41,5) et axe→arrière (~36,5) — si l'axe est ailleurs, l'empreinte est décalée → touche d'un côté.

## RÉGLAGES CLÉS (réglables à chaud, sans redémarrer)
- **Footprint réel** (robot 0.78×0.58, coins arrondis, base_link décalé : avant 0.415 / arrière −0.365) —
  PAS `robot_radius` (qui était 0.22 = cercle 44 cm trop petit → il rasait les obstacles) :
  `ros2 param set /local_costmap/local_costmap footprint "[[0.415,0.19],[0.415,-0.19],[0.315,-0.29],[-0.265,-0.29],[-0.365,-0.19],[-0.365,0.19],[-0.265,0.29],[0.315,0.29]]"` (idem global).
- Vitesse (réglée 2026-06-25, robot lourd qui glisse/dépasse) : **max_vel_x 0.20** + **max_speed_xy 0.20**
  (sinon le cap 0.5 laissait filer) + **decel_lim_x -2.5** ; rotation **max_vel_theta 0.5** (2.0 était bien trop) + **decel_lim_theta
  -2.0**. `ros2 param set /controller_server FollowPath.<param> <val>` (à chaud) ; persistant nav2_params.yaml.
  Curseurs : trop vite tout droit→baisser max_vel_x ; dépasse en tournant→baisser max_vel_theta / renforcer decel_lim_theta.
- **Tourne mal sur place / costmap au côté bloque la rotation** (DWB peine à pivoter) → **RotationShimController**
  au-dessus de DWB (`plugin: nav2_rotation_shim_controller::RotationShimController` + `primary_controller:
  dwb_core::DWBLocalPlanner`, `angular_dist_threshold 0.785`) = pivote vers le chemin avant de rouler ; +
  **min_vel_x -0.10** (recul pour se dégager) + **vtheta_samples 40**. ⚠️ changement de plugin = RELANCER
  navigation_launch (pas à chaud). Si encore bloqué près d'un mur : baisser inflation locale 0.15→0.10 ou réduire l'empreinte.
- Inflation **globale 0.35** (0.20→0.35, le PLAN s'écarte plus des murs) / **locale 0.15** (évitement fin) — réglées 2026-06-25.
- Nettoyer points noirs d'une carte SLAM : `scripts/clean_map.py in.pgm out.pgm [taille_min]` (efface les
  petits amas de pixels noirs = bruit/objets mobiles, garde les murs). Procédure runbook §11bis.
- Lancement nav = **terminaux ROS classiques** (PAS iboot.sh, cf [[amr-commands-always-complete]]) :
  real_bringup → localization_launch map:=... → navigation_launch use_scan_filter:=false → relay /goal_pose /goal_pose_nav.
- Inflation : `ros2 param set /local_costmap/local_costmap inflation_layer.inflation_radius 0.20` (idem global, cost_scaling_factor 3.0).
- Clear : `ros2 service call /local_costmap/clear_entirely_local_costmap nav2_msgs/srv/ClearEntireCostmap "{}"`.
- Snapshot config qui marche : repo `config/nav2_params_real.yaml`.
- Cartes : `~/maps/coin2.*` (orig) + `~/maps/coin_ok.*` (bonne carte re-sauvée 2026-06-20). Sauver une carte
  courante : `ros2 run nav2_map_server map_saver_cli -f ~/maps/NOM --ros-args -p save_map_timeout:=20.0`.

## CONCEPT : inflation ≠ évitement
- **Inflation** (le bleu) = coût DOUX de planification, traversable. Ne garantit PAS le non-contact.
- **Ne pas toucher** = le contrôleur teste l'EMPREINTE vs costmap locale en temps réel (besoin
  obstacle_min_range petit). Garantie DURE « ne touche jamais » (à faire) : **Collision Monitor**
  (zone stop = footprint+marge) ou **élargir le footprint** de quelques cm.

Cf [[amr-session-suite-nav2-cyclone]], [[amr-pi-ros-commands]], [[amr-encoder-5v-overvoltage]].
