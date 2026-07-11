# Ouverture des PR — openamr-platform-sw (fork SHuttooo → upstream openAMRobot)

Guide pour ouvrir les 4 pull requests, **une par une**, dans l'ordre. Base de chaque PR :
**`openAMRobot/openamr-platform-sw : main`**. Head : la branche du fork `SHuttooo`.

**Empilées (stacked) → merger DANS L'ORDRE**, avec review d'Alex entre chaque :
**1. bring-up → 2. docs → 3. docking**, et **4. sim-fix indépendante**.

> ⚠️ **DCO** : l'upstream exige `Signed-off-by:` sur chaque commit. Vérifié : les 4 branches
> sont OK (0 commit non signé). Si un check DCO passe rouge, c'est qu'un nouveau commit non
> signé s'est glissé → `git commit --amend --no-edit -s` (ou `git rebase --signoff <base>`) puis force-push.

---

## PR #1 — `feature/real-robot-bringup` — merge 1st ✅ (ouverte)

Lien de création :
```
https://github.com/openAMRobot/openamr-platform-sw/compare/main...SHuttooo:feature/real-robot-bringup
```
**Titre :** `Real-robot bring-up: sensors, micro-ROS, EKF, Nav2 & composed vision`

**Description :**
```markdown
Brings the platform up on the real robot (RPi5 + Teensy 4.0 + RPLIDAR A1 + Pi Camera IMX708, ROS 2 Jazzy, CycloneDDS / domain 0).

## What this adds
- **Data-source composition**: micro-ROS agent + LiDAR + EKF + scan body-filter + camera bring-up.
- **Composed vision**: intra-process (zero-copy) camera + AprilTag container — the default profile for camera/docking (~15 fps, ~half the vision CPU of the legacy Python gate).
- **Nav2**: real-robot navigation tuning + planner speed-up; nav-only goal relay.
- **Perception**: LiDAR body-reflection filter (±140°, empirically calibrated); 15 fps camera cap; continuous autofocus.
- **Diagnostics**: hardware diagnostics scripts + troubleshooting log.

⚠️ Reviewers: read this COMMIT BY COMMIT (the "Commits" tab), not the full "Files changed" diff — the fork has diverged from upstream, so the raw diff is large and misleading. Each commit is scoped and its message explains WHY.

First of a stacked set — **merge this before** the docs and docking PRs.
```

---

## PR #2 — `feature/real-robot-docs-pr` — merge 2nd (après le merge de #1)

Lien de création :
```
https://github.com/openAMRobot/openamr-platform-sw/compare/main...SHuttooo:feature/real-robot-docs-pr
```
**Titre :** `Real-robot, navigation & safety docs (multi-agent audited)`

**Description :**
```markdown
Engineering documentation series for the real robot, navigation and safety, plus package READMEs.

## What this adds
- `docs/real_robot/*`, `docs/navigation/*`, `docs/safety/*` and package docs.
- Composed profile documented as **the camera/docking default**; `camera_ws` sourcing; RViz real-vs-sim config; DDS/networking; calibration; troubleshooting.
- **Full 59-doc audit**: 45 corrections aligning every doc with the live code — parameters, commands and behaviour (composed default, odom-anchored dock line, LIDAR stop 0.13 m, `obstacle_check_enabled` off, DWB limits not live-tunable, etc.).

⚠️ Reviewers: read this COMMIT BY COMMIT, not the full diff.

Merge after the bring-up PR.
```

---

## PR #3 — `feature/docking` — merge LAST (après #1 et #2)

Lien de création :
```
https://github.com/openAMRobot/openamr-platform-sw/compare/main...SHuttooo:feature/docking
```
**Titre :** `AprilTag docking: 3-tag bundle, odom-anchored approach, robust undock`

**Description :**
```markdown
The AprilTag docking pipeline (7-phase sequencer, camera-frame approach).

## What this adds
- **3-tag bundle** (36h11) pose estimation + geometric dock normal; on-demand AprilTag gate (vision CPU only during a dock).
- **Unified odom-frame approach line**: the dock reference line lives permanently in the `odom` frame, refined by lag-correct in-odom tag lookups — **no base_link↔odom tier switch**. Fixes the reference line swinging with the robot and the near-dock oscillation. `unified_odom_line` param (default true, live-tunable).
- **LIDAR-controlled final stop** (`stop_lidar_distance` 0.13 m; camera depth is a failsafe); forward obstacle guard **off by default** (the dock trips it); calmed pure-pursuit gains; `final_push_speed` to clear the dock step on a low battery.
- During the maneuver: **AMCL laser correction + Nav2 collision_monitor paused** (collision_monitor only after Phase 1); undock reverse **measured in odom** (immune to the AMCL relocalise jump) + a rough ~180° spin.
- `log_splitter` — splits `/rosout` into per-node `/logs/<node>` topics for focused debugging.

⚠️ Reviewers: read this COMMIT BY COMMIT, not the full diff.

**Merge last** (builds on bring-up + docs).
```

---

## PR #4 — `fix/sim-wheel-geometry` — indépendante (n'importe quand)

Lien de création :
```
https://github.com/openAMRobot/openamr-platform-sw/compare/main...SHuttooo:fix/sim-wheel-geometry
```
**Titre :** `fix(description): correct sim diff-drive wheel geometry to match the real robot`

**Description :**
```markdown
The Gazebo diff-drive plugin used a wheel radius of `0.046533 m` while the visual/real wheel is `0.11 m`, so the simulated robot's odometry and motion were miscalibrated (it drove "wrong").

## Fix
- Correct the diff-drive `wheel_radius` in `robot.sdf` to match the real robot.

Independent of the other three PRs — can be merged any time.
```

---

## Flow de review (avec Alex)
1. Ouvrir la PR, ajouter **Alex** en reviewer, se **self-assign**.
2. Envoyer à Alex le lien + le texte « comment lire » (commit par commit).
3. Alex review → corriger si besoin → **merge**.
4. Passer à la PR suivante (son diff rétrécit une fois la précédente mergée).
