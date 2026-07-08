# OpenAMR — Project audit (2026-07-01)

Whole-project state review at the end of Day 3. Covers the three repos (docs, ROS
stack, operator UI), the docking work, and the standing hardware/operational issues.
Compiled from a 3-way repo audit + the session/`claude-memory` record.

---

## 0. Executive verdict

The robot **navigates (Nav2 + AMCL), has a working operator UI, and docks end-to-end**
on the AprilTag bundle — a lot works. The engineering is solid (unified sim/real bring-up,
well-reasoned docking sequencer, clean UI). The gaps are **maturity, not capability**:

- **No functional tests** anywhere (lint only) — regressions surface on hardware.
- **Significant uncommitted work** (docking config + code, misc launch/nav/perception edits)
  sitting on the working tree, not in any pushed branch.
- **6 PRs are ready but not opened** to `openAMRobot:main`.
- **Recurring hardware/operational issues** still gate reliability (left-wheel cable, Pi 5
  brown-out, encoder ripple per boot, camera focus/edge, LiDAR light, nav lifecycle stall).
- **Docking is functional but not yet reliable/straight** — tuning in progress.

Overall maturity: **advanced prototype / integration stage**, not yet unattended-field-ready.

---

## 1. Repositories, Git & PR state

| Repo | Path | Role | Branch state |
|---|---|---|---|
| `openamr` | `~/Documents/openamr` | Personal docs + journal + `claude-memory` | `master`, **12 commits unpushed** + uncommitted docs/memory |
| `openamr-platform-sw` | `~/…/openAMRobot/openamr-platform-sw` | ROS 2 stack | on `local/test-all`; **17 files modified + 1 untracked, uncommitted** |
| `openamrobot-ui` | `~/…/openAMRobot/openamrobot-ui` | Operator UI | `feat/real-robot-integration`, pushed & clean (only `.env` local) |

### PR readiness (all pushed to the SHuttooo forks, 0 behind their upstream target)
- **platform-sw → openAMRobot:main — 5 PRs**: `feature/diagnostics`, `feature/docking-apriltag-gate`,
  `feature/nav2-real-tuning`, `feature/perception-scan-body-filter`, `feature/real-bringup`.
  ⚠️ Re-push `nav2-real-tuning`, `perception-scan-body-filter`, `real-bringup` first (local/origin drift).
  `perception` ⊂ `real-bringup` (overlap — merge perception first, rebase real-bringup).
- **ui → openAMRobot:main — 1 PR**: `feat/real-robot-integration`.
- **Total 6 PRs ready; none opened yet.**

### ⚠️ Uncommitted work (risk of loss / not in any PR)
- **platform-sw (biggest)**: 17 modified files on the `local/test-all` working tree, incl. the
  **docking edits** (`dock_trigger.py`, `dock_trigger.yaml`, `tags_36h11.yaml`), plus
  nav2/perception/bringup/drivers edits, and untracked `goal_relay.launch.py`. **None of this is
  captured in the pushed `feature/docking-apriltag-gate` branch.** → commit to the PR once the dock
  is validated.
- **openamr**: `diagnostics.md` §17 + `RUNBOOK-real-robot.md` + 10 new + 4 modified memory notes,
  all uncommitted; 12 commits unpushed on `master`. Stray **`piece_actuelle.yaml` at the repo root**
  (looks accidental).

---

## 2. ROS 2 stack (`openamr-platform-sw`)

**All packages are production-ready** (unified sim/real bring-up, thin driver layer, calibrated
body filter, hardware-tuned Nav2, full URDF, Gazebo sim). One-liners:
`bringup` (sim/real launcher) · `drivers` (micro-ROS agent + RPLIDAR) · `perception` (scan body
filter + camera) · `nav2` (unified params, AMCL) · `gazebo` (Harmonic sim) · `description` (URDF) ·
`docking` (AprilTag sequencer + gate).

### Docking package — solid core, some fragility
**Strengths**: well-reasoned multi-phase sequencer (centring scan → two-sided normal estimate →
pure-pursuit line → EMA-far/frozen-near visual approach), correct angle-based obstacle guard,
CPU-efficient on-demand AprilTag gate, 50+ documented params, thread-safe with bounded timeouts.

**Weaknesses / risks**:
- **No functional tests** — the 1.6k-line sequencer has only lint checks (copyright/flake8/pep257).
  Regressions caught only on hardware.
- **Live parameter reads in the Phase-5 hot loop** (`visual_servo_kp`, `visual_servo_filter_alpha`
  every 20 Hz; `scan_rotation_speed` per scan) — added Day 3 for live tuning. Convenient now, but a
  code smell / step-glitch risk. **Once the gains are frozen, revert to cached `self.*` (init).**
- **`camera_forward_offset = 0.35` hard-coded** (must stay in sync with the URDF/mount) → make it a
  parameter or TF-derived.
- **Tag baseline**: the design references outer tags at ±0.45 m (90 cm). The math actually uses the
  *detected* tag positions (adapts to any baseline), but a narrower baseline = noisier normal — the
  current **52 cm bundle is why the dock isn't straight** (see §5).
- **Unit-specific hard-codes** (documented, but break on a different robot): `obstacle_scan_forward_angle
  = π`, lidar_link `yaw = π`, camera static TF, `scan_body_filter` sectors. All calibrated for THIS unit.
- Frame names as bare strings (no typo protection); no covariance/variance check on the TF dock estimate.

---

## 3. Operator UI (`openamrobot-ui`)

**Architecture**: React + Tailwind served by Flask (:5050), browser↔ROS via `rosbridge` (:9090),
relay nodes convert TRANSIENT_LOCAL→VOLATILE, camera via `web_video_server` (:8080), CycloneDDS/domain 0.

**Maturity: beta / development-ready.** Core works end-to-end; some panels are stubs.

- **Works (wired to Nav2)**: manual drive, map/costmap/path display, docking control
  (`/dock_trigger`, `/undock_robot`, status), nav status/feedback, camera panel, battery/health.
- **Present but NOT in the main launch** (`new_ui_launch.py`): `folders_handler` (map/route files) and
  `waypoint_nav` (route follower) — they exist and are launchable via **`physnode_launch.py`**, so
  waypoints *can* work but aren't started by default → usability friction. *(Correction to an earlier
  note: waypoint execution is not missing, just decoupled from the main launch.)*
- **Stubs**: lifecycle control panel (buttons are no-ops), Blocks/Blockly (scaffolding, no backend).
- **Gaps**: battery serial `/dev/ttyUSB0` hard-coded (falls back to simulated); no auth/TLS; the
  **DDS gotcha** (Compose defaults to FastDDS if `.env` absent → "connected but zero topics") — resolved
  by the `.env` but fragile.

---

## 4. Hardware & operational issues (standing)

From the session + `claude-memory`. These gate reliability regardless of software:

| Issue | State | Impact |
|---|---|---|
| **Left wheel faux-contact** (intermittent cable) | Open — needs soldering | Drivetrain drops out; #1 hardware blocker |
| **Pi 5 brown-out at bring-up** (current spike > 5 A supply) | Open | Pi freezes/cuts; check `ping` before blaming software |
| **Battery voltage** | Need ≥ 25 V at rest | Below → weak torque, wheel slip, the robot bumps |
| **Encoder ripple** (incremental, phase lost each boot) | Mitigated | Re-run `align_enc_cal.py --arm 250` after every Teensy power-cycle |
| **Camera IMX708 / libcamera** | Works on RPi fork | Focus saga (manual→continuous+fast); **edge softness = field curvature (hardware)** |
| **LiDAR light on camera** | **Fixed Day 3** | IR laser dot dropped tag detections → lidar-pause during camera phases |
| **Motor-driver faults (ZBLD.C20)** | Documented | LED code = green×5 + red; e.g. 2v/4r = 14 locked-rotor, 1v/5r = 10 undervoltage |
| **Nav lifecycle stall at boot** | Workaround | planner/bt inactive; `bond_timeout 60 s` fix not taking on install → manual activation |
| **Stick-slip low-speed floor (~0.06 m/s)** | Physical | Docking speeds sit near it → juddery; dither helps |
| **AMCL drift/jumps** | Observed | Corrects odometry drift with jumps → map-frame docking targets jump (Phase 5 is camera-frame, immune) |

---

## 5. Docking — today's focus, current state

**Works end-to-end**: staging → scan → estimate → pre-dock → re-estimate → visual approach → docked,
then undock. **Tuning in progress.** Config: `dock_pose 1.807/0.003/0`, `docking_distance 0.25`,
`drive_speed 0.08`, `scan_rotation_speed 0.25`, `visual_servo_kp 0.4/alpha 0.4`, obstacle guard off,
camera continuous-AF/fast, lidar paused during camera phases, tag size 0.131, scan mask −108°.

**Open for a reliable/straight dock**:
1. **id 2 detection reliability** (12–67 %) + **wider baseline (~90 cm)** — the root cause of the noisy
   normal / crooked dock.
2. Finish the Phase-5 visual-servo gain tuning (kp/alpha), then **revert the live-reads to cached**.
3. Re-enable a proper obstacle guard (fix the forward self-view in `scan_body_filter`) instead of off.

Full narrative: `docs/history/diagnostics.md` §17.

---

## 6. Prioritised recommendations

1. **Make the dock straight** — widen the bundle baseline to ~90 cm + fix id 2 detection. Highest value.
2. **Capture the work in Git** — commit the docking config + `dock_trigger.py` to `feature/docking-apriltag-gate`; re-push the 3 drifted branches; **open the 6 PRs**.
3. **Fix the nav lifecycle stall** — the `bond_timeout` fix isn't reaching the installed launch (rebuild / symlink-install); removes the manual-activation workaround.
4. **Hardware blockers** — repair the left-wheel cable; address the Pi 5 brown-out (power/wiring).
5. **UI** — add `folders_handler` + `waypoint_nav` to `new_ui_launch.py` so routes work out of the box; implement the lifecycle-control service calls.
6. **Tests** — add functional tests for the docking sequencer (Phase-5 EMA, obstacle cone) and a UI smoke test.
7. **De-hard-code** — `camera_forward_offset` → parameter/TF; document the tag-bundle baseline as a param.
8. **Housekeeping** — commit the openamr journal/memory (push if a backup is wanted); remove the stray `piece_actuelle.yaml`.

---

*Sources: 3-way repo audit (git/PR/docs, ROS stack, UI) + session record. See `claude-memory/` for the
operational recipes and `docs/history/diagnostics.md` for the day-by-day "why".*
