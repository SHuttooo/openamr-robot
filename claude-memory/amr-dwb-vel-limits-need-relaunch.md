---
name: amr-dwb-vel-limits-need-relaunch
description: "Les limites cinématiques DWB (max_vel_x/max_speed_xy/sim_time) ne se mettent PAS à jour à chaud via ros2 param set — il faut relancer Nav2 ; le velocity_smoother, lui, clampe à chaud"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

2026-07-08, réglage vitesse Nav2 sur le robot réel. Piège qui a coûté ~1h :

**`ros2 param set /controller_server FollowPath.max_vel_x 0.35` (et `max_speed_xy`, `sim_time`) ne prend PAS effet à chaud.** `ros2 param get` renvoie bien 0.35, mais DWB continue d'utiliser l'ANCIENNE valeur (limites cinématiques figées au `configure` du contrôleur). Symptôme diagnostique imparable : le `/cmd_vel` reste bloqué **exactement** sur un échantillon de la grille DWB juste sous l'ancien plafond (ex. `linear.x = 0.18157894…` = plus grand échantillon < 0.20 dans la grille [-0.05, 0.35] à 20 samples). Les valeurs `k/(n-1)` propres = signature « c'est DWB qui échantillonne/borne », pas un ralentissement de scoring.

**Le fix = éditer `nav2_params.yaml` PUIS RELANCER Nav2** (`bringup_composed.launch.py`). Après relance, DWB atteint bien 0.35.

**Contournement sans relance :** le `velocity_smoother`, LUI, accepte `max_velocity`/`min_velocity` à chaud et **clampe** la sortie (chaîne : DWB → velocity_smoother → collision_monitor → base). Donc pour BAISSER le plafond effectif tout de suite, `ros2 param set /velocity_smoother max_velocity "[v, 0.0, w]"` mord immédiatement. Pour AUGMENTER au-delà de la limite DWB, en revanche, il faut relancer (le smoother ne peut que réduire ce que DWB produit).

**How to apply :** pour changer une vitesse max Nav2 sur ce robot → éditer le fichier (src + `cp` vers `build/openamrobot_nav2/config/` car build = copie, pas symlink) + relancer. Backup le fichier avant sed. Le relaunch du `bringup_composed` NE power-cycle PAS le Teensy (agent micro-ROS se reconnecte) → pas de recalibration gyro/encodeur à refaire, table encodeur en RAM survit ; juste re-donner la pose AMCL. Valeurs de base de ce robot : max_vel_x/max_speed_xy 0.20, max_vel_theta 0.5, rotate_to_heading_angular_vel 0.5, sim_time 1.7. Voir [[amr-nav2-bringup]], [[amr-min-velocity-floors]], [[amr-user-drives-real-robot-launches]].
