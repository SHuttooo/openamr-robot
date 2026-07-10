---
name: ""
metadata: 
  node_type: memory
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

2026-07-08 : symptôme « la nav ne tourne plus proprement / les cmd_vel de rotation sont trop basses / il cale à 0.15 rad/s » — j'ai passé des heures à triturer les params Nav2 à chaud (`acc_lim_theta`, `min_speed_theta`, `angular_dist_threshold`, dither firmware…). **Le vrai coupable = des points LIDAR parasites vus TRÈS PRÈS du robot** (quelque chose sur/à côté du robot renvoyait du scan) → la costmap voyait un obstacle collé → `collision_monitor` bridait `/cmd_vel` → mouvement intermittent/faible. L'utilisateur a dégagé l'objet → réglé instantanément.

**Why :** ce robot met déjà l'intelligence rotation dans la config (RotationShim `rotate_to_heading_angular_vel: 0.5`, `angular_dist_threshold: 0.785`, DWB tuné). Quand « ça bride en rotation », le réflexe param-tuning est presque toujours faux : la chaîne de sécurité (`collision_monitor` + costmap sur `/scan_filtered`) gate la vitesse pour une raison PHYSIQUE.

**How to apply :** AVANT de toucher au moindre param contrôleur, vérifier qu'il n'y a pas de retour LIDAR fantôme proche : regarder `/scan`/costmap dans RViz (points collés au footprint ?), enlever tout objet/câble près du plan du lidar. Voir aussi [[amr-nav2-bringup]] (empreinte élargie, min_range 0, angle mort 2D) et [[amr-min-velocity-floors]] (le plancher 0.15 rad/s EST réel mais n'était PAS le sujet ici). Piège méthodo : ne pas empiler des fixes à chaud sur un symptôme avant d'avoir éliminé la cause capteur.

**Bonus de la session :** mon checkout PC `openamr-platform-sw` était une branche PÉRIMÉE (DWB direct, acc_lim_theta 1.0) ≠ le Pi (déjà RotationShim + valeurs tunées). Toujours lire le fichier SUR LE PI (`~/openamr-platform-sw/ros2/src/openamrobot_nav2/config/nav2_params.yaml`) avant de raisonner sur des valeurs — pas le checkout PC. Voir [[amr-platform-sw-prs]].
