---
name: amr-docking-unified-odom-line
description: "Docking near-approach réécrit — la ligne du dock vit TOUJOURS en odom (plus de bascule base_link/odom) → la ligne ne balaie plus avec le robot, plus de saut/oscillation"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-09 : réécriture du correcteur d'approche finale du docking** (`unified_odom_line`, défaut `true`), validé sur le robot réel « énormément mieux ».

**Avant (bug)** : cascade de tiers qui CHANGEAIT de repère — `base_link` (tag live) quand le tag est frais, ligne figée en `odom` quand perdu. Conséquences : (a) la ligne verte de référence **balayait AVEC le robot même tag détecté** — car ancrée sur le tag live **laggé** en base_link : une ligne dessinée en base_link mais **recalculée** chaque frame reste fixe sur le dock SI la détection est sans retard ; **avec du lag** elle est décalée du mouvement du robot pendant le retard → elle suit le robot. (b) **saut** à la frontière de tier → oscillation. Et `detection_max_age=1.5s` faisait coaster 1,5 s (~15 cm) sur une détection périmée collée au robot quand le tag se perdait.

**Fix** : la ligne du dock vit **en permanence en `odom`**. Les 3 tags frais sont lus **directement en odom** via `_lookup_tag_odom3` (**lag-correct** : `lookup_transform('odom', tag, Time(0))` résout `odom←base_link` à l'horodatage de DÉTECTION du tag → tag placé là où il était quand vu, pas traîné par le robot qui a bougé pendant la latence caméra). Ils raffinent la ligne en EMA (poids dégressif ∝ depth). Tag centre seul → recale seulement la **position** (normal figé). Aucun tag → coast sur la ligne odom via odométrie. **Même loi pure-pursuit partout, plus de changement de repère.** Bonus : chaque tag frais **re-corrige la dérive odom** (l'ancien Tier 3 figé ne re-corrigeait jamais) → robuste au gyro/batterie ; seul le dernier cm aveugle est odom pur. Interrupteur à chaud : `ros2 param set /dock_trigger unified_odom_line false` (revient aux tiers).

**Réglages associés figés dans `dock_trigger.yaml`** (avant = à chaud, perdus à la relance → l'oscillation « revenait » à chaque relance) : `line_yaw_kp 2.5→1.2`, `line_lookahead_distance 0.3→0.5`, `turn_deadband 0.04→0.09`, `drive_yaw_max_omega 0.3→0.255`, `dock_pose 4.899/0 → 1.362/0.222 yaw 0` (tag réel dans `piece_actuelle`, sinon staging hors carte « outside bounds »), arrêt final via **lidar** `stop_lidar_distance 0.12` (+ `docking_distance 0.12` failsafe caméra), `undock_reverse_distance 1.5→0.7`, `detection_max_age` remis à 1.5 (le design odom rend la valeur peu critique).

**Undock robuste (même commit)** : recul mesuré en **odom** (avant en map → sautait quand AMCL se réactive → recul coupé court) ; **spin 180° grossier** `_spin_angle_odom` (intègre le yaw odom, tol ±8°, cadence ferme) au lieu du spin vers un yaw précis ; `undock_reverse_distance 1.5→0.7`. Arrêt final **lidar 0.10** (+ `docking_distance 0.10` failsafe) ; `final_push_speed` (défaut 0.05, monter ~0.12 pour l'élan sur la marche à batterie basse).

**Poussé** : commité + push sur **`feature/docking`** (fork SHuttooo) commit **9b88328** (sign-off DCO `SHuttooo <matthieuvinet04@gmail.com>`). Ma version = sur-ensemble propre de feature/docking (seule fonc retirée = `_dock_pose_from_two`, le fallback 2-tags bruité, exprès). Les **docs** (docs/navigation, docs/real_robot, nav2/README) restent **non-commitées** sur `feature/real-robot-docs-pr`. L'utilisateur ouvre la PR upstream.

**Restant** : recharger la batterie (était 24,5 V < 25 V → couple mou + odom qui dérive) ; vérifier le biais gyro. Voir [[amr-docking-gate-4hz-bottleneck]], [[amr-vision-latency-cpu]], [[amr-imu-gyro-bias-boot]], [[amr-battery-voltage-check]], [[amr-platform-sw-prs]].
