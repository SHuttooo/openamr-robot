---
name: amr-docking-bundle-setup
description: "Setup physique du dock AprilTag (map piece_actuelle) : bundle 3 tags 36h11, DISPOSITION vue robot = id 2 GAUCHE / id 1 CENTRE / id 0 DROITE, carré noir 0.131 m, baseline 52 cm. Dock pose capturée = (1.807, 0.003, yaw 0) dans dock_trigger.yaml. id 2 marginal (~50%, le tag le plus proche) à fiabiliser."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Docking AprilTag **sans dock physique** (le bundle EST la cible). Robot réel, map `piece_actuelle`.
Capturé 2026-07-01. Voir [[amr-apriltag-on-demand-gate]] (gate CPU) et le runbook `docs/reference/RUNBOOK-real-robot.md`.

## Bundle physique
- 3 tags **36h11**, IDs **0/1/2**. Taille = **carré noir 0.131 m** (imprimé à 87 % sur A4 → mesuré ;
  `size: 0.131` dans `openamrobot_docking/config/tags_36h11.yaml`, Pi + PC).
- **DISPOSITION (vue du robot) : `id 2` À GAUCHE — `id 1` AU CENTRE — `id 0` À DROITE.**
- id 1 = **cible** (tag central). id 0 & id 2 = extérieurs (estiment la normale).
- Baseline id0↔id2 = **52 cm centre-à-centre** (39,7 cm entre bords intérieurs) ; id 1 pile au milieu
  (13,35 cm de blanc de chaque côté). Coplanaires, même hauteur (≈ hauteur caméra), surface plane verticale.
- L'ordre gauche/droite n'affecte PAS le code (la normale est désambiguïsée vers le robot), mais noté pour
  reproductibilité. PDF à réimprimer : `~/Documents/apriltag_36h11_id{0,1,2}.pdf`.

## Dock pose (map piece_actuelle) — écrite dans dock_trigger.yaml (Pi + PC)
- `dock_pose_x: 1.807`, `dock_pose_y: 0.003`, `dock_pose_yaw: 0.0` = position de tag_1 dans la map,
  cap d'approche +x. Staging = dock − staging_distance(2 m)·cos/sin(yaw) → robot vers x≈−0,2.
- Capture : robot localisé à (0.03, 0.047) yaw≈0, ~1,78 m devant le bundle (tags à x≈1.80,
  y de −0.26 à +0.28, tag_1 à (1.807, 0.003)).
- ⚠️ `dock_trigger` lit le param **au démarrage** → **relancer le bringup** (`use_docking:=true`) pour
  prendre la nouvelle dock pose (un `ros2 param set` à chaud ne suffit pas, valeur cachée à l'init).

## À FIABILISER avant un vrai accostage
- **id 2 marginal** : détecté ~50 % des frames, `decision_margin ~82` (vs ~95 pour id 0/1). C'est le tag
  « le plus proche » (bundle légèrement incliné, côté id 2 vers le robot). Cause probable : angle rasant /
  léger flou / glare. À corriger (coplanarité stricte, réduire l'inclinaison, éclairage). **Le code exige
  les 3 tags vus ENSEMBLE** (`_estimate_dock_once` → sinon « never saw all three tags together »).
- Calibration encodeurs faite ce jour (phase L 181.5°/R 309°) avant de rouler [[amr-pid-tuning]].

## 1er test réel (2026-07-01) — la séquence VA JUSQU'AU BOUT ✅
Staging → scan/centrage (both tags centred) → estimation `dock centre (1.80,0.01), normal ~1°, dist 1.77m`
→ pré-dock 2 m sur la normale → re-estimation → **approche visuelle Phase 5 → `docked: depth 0.144m`**.
**id2 à 67 % a suffi.** Défauts observés + corrections :
- **A tapé le mur** : `docking_distance` 0.15 m trop court → **passé à 0.35 m** (dock_trigger.yaml Pi+PC).
- **Pas droit** : normale bruitée — Phase 4 a re-estimé −3.5° puis 6.6° (**désaccord 10°**). Cause = id2
  marginal + baseline 52 cm étroit. Fix = fiabiliser id2 et/ou **élargir baseline à ~90 cm**.
- **Garde-fou obstacle = FAUX POSITIF** : « obstacle at 0.38 m » dans le cône avant = le robot **se voit
  lui-même** (lidar yaw=π, `scan_body_filter` ne coupe que l'arrière ±40°, pas l'avant). Contourné en
  lançant `dock_trigger` avec `-p obstacle_check_enabled:=false`. **Vrai fix à faire** : couper aussi le
  secteur avant du self-view, ou monter obstacle_min_range.
- **Nav recale au boot** (planner/bt inactive) MALGRÉ le bond_timeout 60 s → l'install ne prend pas le fix
  du launch (à vérifier : symlink-install du .py ?). Contournement = activation manuelle des nœuds nav.
- **Lancer dock_trigger seul** (sans relancer tout le bringup) recharge la dock pose :
  `ros2 run openamrobot_docking dock_trigger.py --ros-args --params-file <install>/config/dock_trigger.yaml
  -p use_sim_time:=false -p obstacle_scan_forward_angle:=3.14159 -p use_apriltag_gate:=true` (le param est
  lu à l'init → restart obligatoire après édition yaml). install = symlink vers src (édit src = OK).

## Drivers moteurs — code défaut LED (ZBLD.C20-120L2R)
Légende dans `docs/hardware/motor-driver-fault-codes.md`. **Code = (verts × 5) + rouges.**
Vu après le crash mur : **2 verts / 4 rouges = code 14 = ROTOR BLOQUÉ** (roue coincée contre le mur ;
libérer + power-cycle 24 V, les défauts se verrouillent). **Sous-tension = code 10 (1 vert / 5 rouges)**.
GAUCHE = M1, DROITE = M2. Voir [[amr-driver-balance-dip]].

## Day 3 soir — avancées (2026-07-01) — récit complet dans docs/history/diagnostics.md §17
- **Caméra focus** : était en **Manual/infini** (`AfMode=0`) → tags flous en approche. Passé en
  **Continuous + Fast + Full** (`AfMode=2, AfSpeed=1, AfRange=2`) — le manual hunt en lent, Fast suit
  bien. **Bords mous = courbure de champ (hardware)**. Params focus live (`ros2 param set /camera ...`).
- **Lumière LIDAR** = le laser IR balaie un point sur les tags → détections loupées. **FIX codé dans
  dock_trigger.py** : `_set_lidar()` coupe le lidar (`/stop_motor`) au staging et le relance
  (`/start_motor`) dans le finally (gaté `use_apriltag_gate`). Collision_monitor déjà court-circuité
  pendant le dock (cmd_vel direct) → aucune vraie perte.
- **Gains LIVE-tunables** (modif code) : `visual_servo_kp`, `visual_servo_filter_alpha`,
  `scan_rotation_speed` relus par boucle → `ros2 param set /dock_trigger <p> <v>` SANS restart.
- **Config actuelle** : docking_distance **0.25**, drive_speed **0.08** (0.05 sous le plancher
  stick-slip), scan_rotation_speed **0.25** (0.15 trop lent = ne tourne pas), undock **1.0**,
  obstacle_check **false**, visual_servo_kp 0.4/alpha 0.4, line_yaw_kp 1.5. Masque scan élargi à **−108°**.
- **Toujours OUVERT** : id 2 à fiabiliser + baseline à élargir (~90 cm) = LE fix « droit » ; nav lifecycle
  recale au boot → activation manuelle ; finir le tuning gains puis **commit dock config+code sur la PR**.
- Modifs code faites Pi ET PC (dock_trigger.py) ; backups `.bak_lidar`/`.bak2` sur le Pi.

## Day 4 (2026-07-02) — galères démarrage + Phase 5 runaway
- **Lidar crash-loop au boot** (rplidar_composition exit 1, respawn) → aucun scan → RViz vide + AMCL
  pas localisé. **FIX : `pkill -f rplidar_composition`** (respawn propre) → `/scan` repart. À refaire si
  ça recrashe au boot.
- **IMU biais gyro énorme** : `/imu/data` angular_velocity.z = **-0.176 rad/s (-10°/s) À L'ARRÊT** →
  l'EKF dérive le lacet ~12°/s → odométrie qui tourne → **impossible de localiser** (les points lidar
  dérivent dans RViz). Encodeurs OK (0). **FIX : reset Teensy robot IMMOBILE** → recalibre le gyro au
  boot → yaw rate retombe à 0. ⚠️ Le reset Teensy **efface la calib encodeurs** → refaire align_enc_cal.
- **Caméra passée en AUTOFOCUS CONTINU** (`AfMode=2/Fast/Full`) à la demande user — MAIS ça **hunt en
  mouvement** (cf le runaway ci-dessous).
- **Lidar-pause CORRIGÉ** : avant il coupait le lidar dès le staging (Phase 2) → AMCL figé → RViz cassé
  pendant tout le dock. Maintenant `_set_lidar(False)` est **UNIQUEMENT au début de Phase 5** (caméra
  pure, pas besoin d'AMCL) ; Phases 1-4 gardent le lidar. Confirmé dans les logs : « LiDAR motor -> stopped »
  n'apparaît qu'en Phase 5.
- **dock_pose re-capturée** pour la localisation du jour = **(1.730, 0.035, yaw 0)** (= map→tag_1).
- **⚠️ PHASE 5 RUNAWAY (2026-07-02)** : Phase 1-4 OK (normal 11.8°→5.2°, désaccord 6.6° → repositionne
  1.5m), lidar coupé ✅, puis **Phase 5 → le robot A FONCÉ AVANT-GAUCHE** (régime FAR, avant le freeze —
  pas de log « freezing axis »/« docked »). **Cause probable : l'autofocus CONTINU qui hunt → détections
  pourries → axe/servo faux**, + normale bruitée. Piste : soit focus fixe (mais flou courte distance),
  soit **piloter LensPosition depuis la distance connue du tag** (déterministe, pas de hunt), soit limiter
  la vitesse/omega en Phase 5 FAR + garde-fou anti-runaway.

## Day 5 (2026-07-02) — visual servo rebuild + THE latency root cause (English going forward)
Full day: `docs/history/2026-07-02-audit-vision-latency-and-compute.md`. Root cause: [[amr-vision-latency-cpu]].
- **Phase-5 visual corrector REBUILT** (`_final_visual_approach`): camera-frame **PD** on the tag-1
  bearing `omega=-(kp·bearing+kd·d)`, made dominant (raised `freeze_axis_distance` to 1.5, line only
  does the far coarse leg); **hysteresis deadband** (`visual_align_deadband` 0.10) so it drives straight
  when aligned (kills per-frame bang-bang from the 0.15 stick-slip floor); **coast-straight through brief
  tag dropouts** + **odom dead-reckoning** of depth for the last blind cm; `min_turn_omega` 0.15 floor so
  yaw corrections actually execute. New yaml: `visual_servo_kp 1.0/kd 0.2/alpha 0.6`,
  `drive_yaw_max_omega 0.35`, `visual_lost_max_frames 25`. kp/kd/alpha/deadband/freeze all LIVE (re-read each loop).
- **LiDAR-cut idea = DEAD END**: cutting the lidar motor at the FAR→NEAR hand-over KILLED apriltag
  detection within ~1 s (rplidar/apriltag likely share a container). REVERTED, behind param
  `stop_lidar_in_approach` (default false). ⚠️ We therefore never actually TESTED the IR-dot
  hypothesis (the cut broke detection for an unrelated reason) → it stays OPEN, maybe a compound
  problem; latency is the measured/dominant cause, IR dot (if any) secondary.
- **THE blocker = detection latency** (250-700 ms) from Pi5 CPU saturation, not the gains. Fixes deployed
  (NOT yet verified — needs apriltag restart): `apriltag_gate.py` **`max_fps` throttle 10fps** (kills the
  input backlog, keeps full res → no precision loss) + **`decimate 2.0`** in tags_36h11.yaml (threads 3).
- **`camera_forward_offset = 0.35`** hard-coded in `_final_visual_approach`; docking_distance 0.25;
  dock_pose used = (1.730, 0.035, 0). Pi backups: `.bak_visual/.bak_coast/.bak_lidarcut/.bak_lidaron/.bak_decimate/.bak_throttle`.
