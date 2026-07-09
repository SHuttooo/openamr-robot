# 2026-07-09 — Docking : la ligne d'approche vit toujours en odom (fin de l'oscillation) + undock robuste

Session centrée sur **l'oscillation de l'approche finale du docking** (régime NEAR), diagnostiquée jusqu'à la cause racine puis corrigée par une **réécriture du repère de référence**. En bonus : correction de l'undock, de la distance d'arrêt, de la pose du dock (hors carte), et ajout d'un « coup de rein » final pour la marche du dock à batterie basse. Le tout commité + poussé sur `feature/docking` du fork.

## Point de départ

À l'approche du dock, **grosse oscillation gauche-droite** : « la ligne de référence bouge, même quand le tag est détecté, comme si le correcteur essayait de corriger une ligne qui se déplace ». Deux symptômes distincts finissent par se recouper :
1. la **ligne verte de référence balaie avec le robot**,
2. quand la caméra **perd** le tag, « l'odométrie ne prend pas le relais » — la ligne + le point rouge glissent **avec** le robot.

## Le diagnostic en cascade

- **Faux départ écarté** : ce n'était pas (seulement) les gains. On a d'abord calmé le correcteur (kp/lookahead) → l'oscillation rapide devient lente mais **ne meurt pas** → signature d'un **retard (lag)** dans la boucle, pas d'un simple gain trop fort.
- **`detection_max_age = 1.5 s`** : quand la caméra perd un tag, sa TF reste « valide » 1,5 s → le code continue 1,5 s (~15 cm) sur la **détection figée collée en `base_link`** (qui glisse avec le robot) avant de basculer sur l'odométrie. Baissé à 0,5 s d'abord (puis remis à 1,5 après la réécriture, devenu peu critique).
- **La vraie cause** (comprise avec l'utilisateur) : le correcteur **CHANGEAIT de repère**. Tant que le tag est frais → ligne calculée en **`base_link`** (repère robot) depuis la détection live ; tag perdu → ligne figée en **`odom`**. Deux mécanismes différents, et **le basculement** (+ le lag) crée le saut.

### L'insight clé

Une ligne dessinée en `base_link` mais **recalculée chaque image** depuis une détection **sans retard** reste fixe sur le dock (le recalcul annule le mouvement du robot). **Avec du lag caméra** (100–700 ms, Pi chargé), le recalcul utilise une **vieille** position du tag → la ligne est décalée du mouvement récent du robot → **elle suit le robot**, puis se re-cale au rafraîchissement suivant. C'est exactement « la ligne bouge même quand le tag est détecté ».

## Le fix propre — `unified_odom_line`

Réécriture du cœur de l'approche NEAR : **la ligne du dock vit en permanence dans le repère `odom`** (monde fixe). Une **seule** loi pure-pursuit, quelle que soit la visibilité :
- **3 tags frais** → lus **directement en odom** via `_lookup_tag_odom3` (**lag-correct** : `tf2.lookup_transform('odom', tag, Time(0))` résout `odom←base_link` à l'horodatage **de détection** du tag → tag placé là où il était quand vu, pas traîné par le robot qui a bougé pendant la latence) → **raffinent** la ligne (EMA à poids dégressif ∝ profondeur).
- **tag centre seul** → recale seulement la **position** de la ligne (normal figé).
- **aucun tag** → la ligne **reste posée**, le robot glisse dessus via l'odométrie.

**Plus de bascule `base_link` ↔ `odom`** → la référence ne balaie plus avec le robot, plus de saut de frontière, le lag ne la fait plus swinguer. **Bonus** : chaque tag frais **re-corrige la dérive odom** (l'ancien Tier 3 figé ne re-corrigeait jamais) → robuste au gyro/batterie ; seul le dernier cm aveugle est odom pur.

Derrière l'interrupteur **`unified_odom_line` (défaut `true`, réglable à chaud)** — `false` = ancien cascade de tiers, pour un A/B sans redéployer.

**Résultat terrain : « énormément mieux »** — la ligne reste enfin plantée sur le dock.

## Réglages associés (persistés dans `dock_trigger.yaml`)

Les réglages calmes d'avant étaient **à chaud** → **perdus à chaque relance** (l'oscillation « revenait » car le yaml rechargeait des gains agressifs). Désormais figés :
- `line_yaw_kp` **2.5 → 1.2**, `line_lookahead_distance` **0.3 → 0.5**, `turn_deadband` **0.04 → 0.09**, `drive_yaw_max_omega` **0.3 → 0.255** (−15 %, demandé).
- **Arrêt final piloté au LIDAR avant** : `stop_lidar_distance` **0.10** (+ `docking_distance` 0.10 en failsafe caméra) — le lidar (fiable) commande l'arrêt, la caméra ne pré-empte jamais plus loin.
- **`final_push_speed`** (défaut 0.05) : plancher du taper = vitesse des derniers cm. À monter (~0.12) pour garder de l'**élan** et franchir la **marche du dock à batterie basse** (le docking arrive par définition à plat). Ma réécriture n'avait **pas** touché l'avance → le « mou » = la batterie, ce param compense.

## Bug annexe — pose du dock hors carte

Le planner abortait : `Goal (2.90, 0.00) was outside bounds`. Cause : `dock_pose_x = 4.899` (d'une autre carte) alors que `piece_actuelle.yaml` s'arrête à **x = 1.97 m** → staging (`dock_x − staging_distance` = 2.90) hors carte. Mesuré le tag réel (`ros2 run tf2_ros tf2_echo map charging_dock_tag_1` → (1.362, 0.222), +z ≈ −x ⇒ yaw 0) et corrigé **`dock_pose 4.899/0 → 1.362/0.222 yaw 0`** → staging à −0.638, dans la carte.

## Undock robuste

- **Recul** mesuré en **`odom`** (avant en `map` → sautait quand **AMCL se réactive** à l'undock → recul coupé court « ne recule pas de 0.7 m »).
- **Demi-tour 180° grossier** : nouveau `_spin_angle_odom` (intègre le yaw odom, tolérance ±8°, cadence ferme) au lieu du spin vers un yaw **précis** (fussy/timeout à basse batterie).
- `undock_reverse_distance` **1.5 → 0.7 m**.

## État final

- **Commité + poussé** : `feature/docking` du fork SHuttooo, commit **`9b88328`** (sign-off DCO). Ma version = sur-ensemble propre de la branche (seule fonction retirée = `_dock_pose_from_two`, le fallback 2-tags bruité, exprès). Déployé et compilé sur le Pi.
- **Docs** (docs/navigation, docs/real_robot, nav2/README) restées non-commitées sur `feature/real-robot-docs-pr`.

## Restant / à surveiller

- ⚠️ **Recharger la batterie** (était **24,5 V < 25 V** → couple mou + odométrie qui dérive ; le dernier cm aveugle du docking dépend de l'odom).
- **Vérifier le biais gyro** (robot immobile : `ros2 topic echo /imu/data --field angular_velocity.z --once`) — un gyro biaisé fait dériver la ligne figée.
- **Test complet** batterie chargée : accostage + franchissement de marche (`final_push_speed 0.12`), undock (recul 0.7 + demi-tour).
- **Ouvrir la PR** `feature/docking` upstream (accès utilisateur).
