# Fix log — change tracking

> Record of all changes made while executing `docs/FIX-PLAN.md`. For each
> change: files, what, **why**, and how to verify. Session of 2026-06-26.
> Repos: `platform-sw` = openamr-platform-sw, `instance` = openamr.

---

## A1 — Reintegrate `velocity_smoother` + `collision_monitor` (🔴1)

**Problem fixed:** the integration (single `bringup.launch.py` command) had **lost the reactive
safety**. `navigation_launch.py` launched neither `velocity_smoother` nor `collision_monitor` (absent
from `lifecycle_nodes`), even though `nav2_params.yaml` configures them and the old system launched
them via `openamr/launch/collision_monitor_launch.py`. Result: the `controller_server` published
directly to `/cmd_vel`, with no safety net → consistent with "the robot hits visible objects".

**Modified files (platform-sw):**
- `ros2/src/openamrobot_nav2/launch/navigation_launch.py`
  - Added `velocity_smoother` and `collision_monitor` to `lifecycle_nodes`.
  - `controller_server`: remap `cmd_vel → cmd_vel_nav` (no longer writes the final `/cmd_vel`).
  - Added the `velocity_smoother` node (remap `cmd_vel → cmd_vel_nav` as input) and
    `collision_monitor` (no remap: topics set in the YAML).
  - Same additions in the `use_composition` branch (parity, even though not used).
- `ros2/src/openamrobot_nav2/package.xml`
  - Added `<exec_depend>nav2_velocity_smoother</exec_depend>` and `nav2_collision_monitor`.

**The resulting command chain:**
`controller_server → cmd_vel_nav → velocity_smoother → cmd_vel_smoothed → collision_monitor → cmd_vel`
(consistent with `nav2_params.yaml`: `cmd_vel_in_topic: cmd_vel_smoothed`, `cmd_vel_out_topic: cmd_vel`).
No loop: the controller no longer publishes `cmd_vel`, so the `velocity_smoother` reads only the
controller's output, not that of the collision_monitor.

**Why this wiring:** the `collision_monitor` `FootprintApproach` zone projects the footprint along
the command and **slows down** (`approach` action) if a collision is predicted on
`/scan_filtered`. The `velocity_smoother` smooths accelerations (consistent with the limits in
`gazebo_control.xacro`). Applied in `navigation_launch.py` → applies to **sim AND real** (shared-stack
principle).

**Docking note:** during docking, the `controller_server` is inactive (no nav goal) → the
`velocity_smoother`/`collision_monitor` receive nothing → `dock_trigger` drives `/cmd_vel` directly
(intended behavior, it has its own obstacle guard). No publisher conflict.

**Verify:** `python3 -m py_compile navigation_launch.py` OK. To validate in sim: `ros2 node list`
must show `velocity_smoother` + `collision_monitor` active, and the robot must slow down when facing an
obstacle. ⚠️ Requires a `colcon build` (new nodes + deps) before testing.

**Status:** ✅ code done · ✅ **validated in sim (2026-06-26)** · install is symlinked (no rebuild needed).

**Sim validation (2026-06-26):** launched `bringup.launch.py sim:=true use_docking:=true` headless.
- `velocity_smoother` + `collision_monitor` launched AND `active [3]` (activated by the lifecycle manager).
- cmd_vel chain verified 1:1 at each stage: `/cmd_vel_nav` (controller→smoother), `/cmd_vel_smoothed`
  (smoother→monitor), `/cmd_vel` (monitor→base). No loop.
- Exactly one forwarder on `/goal_pose_nav` (dock_trigger, no relay).
- End-to-end motion: sent a `/goal_pose` at 1.2 m → robot navigated (odom x 0 → 0.85 m). The
  collision_monitor does not over-block. ✅

---

## A2 — Timeouts on `dock_trigger.py` action waits (🔴2)

**Problem:** `_send_action_blocking` waited for the acceptance AND the result of a Nav2 action
**without any bound** (`while not future.done(): sleep`). If Nav2 never completes (lifecycle
inactive, BT stuck), the docking sequence froze forever → permanent `busy=True` → the node
no longer accepted any trigger/undock/goal until a kill.

**File:** `openamrobot_docking/scripts/dock_trigger.py` (`_send_action_blocking`).
- Added `accept_timeout=10.0` and `result_timeout=120.0` (via `time.monotonic()`).
- On timeout: error log, `cancel_goal_async()`, `return False` (the sequence fails
  cleanly instead of blocking).

**Status:** ✅ code done.

---

## A3 — Dock pose: code↔YAML defaults aligned (🔴3)

**Problem:** the code defaults (`dock_pose_x=0, y=4.9, yaw=π/2`) and the YAML defaults
(`x=4.899, y=0, yaw=0`) were **contradictory**. If a launch forgot to pass the params, the
robot drove toward a completely wrong staging area (→ wall).

**File:** `dock_trigger.py:117-119` → defaults aligned with `dock_trigger.yaml` (`4.899, 0, 0`).
The **real** physical pose still needs to be measured in your map and put into the YAML (task B2).

**Status:** ✅ code done · ⏳ B2 (measure the real pose).

---

## A4 — Obstacle cone direction (lidar mounted at 180°) (🔴4)

**Problem:** `dock_trigger`'s obstacle guard looked into the scan frame with
`center_angle=0` ("front"). But the real RPLIDAR is mounted **yaw=π** → angle 0 of the scan points
to the **rear**. So the "front" cone monitored the rear → the robot drove forward blind.

**Files:**
- `dock_trigger.py`: new parameter `obstacle_scan_forward_angle` (default **0.0**, sim); the
  two call sites (`goto-point pre-check`, `forward drive`) use it instead of a hardcoded `0.0`.
- `docking_real.launch.py`: override `obstacle_scan_forward_angle: 3.14159` (π) for the real robot.
  → Sim keeps 0 (lidar aligned), real offsets by π (lidar at 180°). One parameter, two profiles.

**Status:** ✅ code done · ⏳ to confirm on the robot (E2/E4).

---

## A5 — Parameterizable AMCL initial pose (🔴5)

**Problem:** `nav2_params.yaml` has `set_initial_pose: true` at `(0,0)`. Correct in sim (robot spawned
at the origin), **wrong in real** (the robot is never at the map origin) → AMCL mislocalized →
costmaps in the wrong place, absurd docking staging. The old `bringall.sh` worked around it via
"auto-pose".

**File:** `openamrobot_bringup/launch/bringup.launch.py` (`_params_with_map`).
- The function now takes `is_sim`. In **real**, it writes `amcl.set_initial_pose = False` in
  the temporary params → AMCL is no longer teleported to (0,0); the operator gives the pose via RViz
  "2D Pose Estimate". In **sim**, behavior unchanged (origin correct).

**Status:** ✅ code done · ⏳ to validate in real (E2).

---

## A7 — Cleanup of the temporary params file (minor)

**Problem:** `_params_with_map` created a `tempfile` on every launch without ever deleting it →
accumulation of `/tmp/nav2_params_map_*` on the Pi.

**File:** `bringup.launch.py` — `import atexit` + `atexit.register(...)` deletes the file on
process exit (the nodes have read their params by then).

**Status:** ✅ code done.

---

## C2 — Mark obsolete scripts legacy

**Problem:** stale scripts still in `scripts/` could mislead or break things.
- `odom_tf_relay.py`: superseded by the robot_localization EKF. Running it alongside the EKF
  creates a SECOND publisher of the `odom->base_link` TF → flickering TF, unstable AMCL/costmaps.
- `tune.sh`: superseded by `pid_tuner.py`; also hardcodes the Pi sudo password (`admin`).

**Files:** legacy header added to `scripts/odom_tf_relay.py` (double-TF warning) and
`scripts/tune.sh` (replaced + security note on the hardcoded password; French usage line translated).

**Status:** ✅ done.

---

## C3 — Harden `bringall.sh` (legacy, minimal surgical)

**Problem (audit):** `pkill -9 -f "ros2 launch"` would kill ANY unrelated ros2 launch on the machine;
`-9` left serial ports not released; hardcoded `/home/botshare/...` paths failed silently (missing
map → empty costmaps).

**File:** `scripts/bringall.sh` (mirror of the Pi copy; legacy until C4).
- Kill list: replaced the bare `"ros2 launch"` with project-specific launch names
  (`openamr_real_bringup`, `localization_launch`, `navigation_launch`); SIGTERM first (frees serial
  ports) THEN SIGKILL; added `velocity_smoother` (now spawned by navigation_launch via A1).
- Added `[ -f ]` guards on `$BRINGUP`, `$MAP`, `$RELAY` (abort with a clear message instead of a
  silent empty-costmap failure).

**Status:** ✅ done · `bash -n` OK. (Repo mirror only — the live Pi copy needs the same edits at C4.)

---

## A6 — Anti-double-forwarder guard in dock_trigger (validated)

**Problem:** there must be exactly ONE forwarder on `/goal_pose_nav`. A leftover goal relay or an
orphaned `dock_trigger` (witnessed live: an incomplete shutdown left a second dock_trigger →
2 publishers on `/goal_pose_nav` → every RViz goal published twice). Cannot kill the other node,
but we can warn the operator.

**File:** `openamrobot_docking/scripts/dock_trigger.py`.
- One-shot timer (4 s after startup, lets other nodes register) → `_check_single_forwarder()`:
  `count_publishers(goal_pose_nav)`. If >1 → loud `ERROR` "DOUBLE FORWARDER…"; if 1 → `INFO`
  "Goal forwarder OK".

**Validation (2026-06-26):**
- 1 forwarder (dock_trigger alone) → `INFO: Goal forwarder OK: sole publisher on /goal_pose_nav`. ✅
- 2 dock_triggers (the real orphan scenario) → `ERROR: DOUBLE FORWARDER: 2 publishers…`. ✅
- Note: a `topic_tools relay` is a *lazy* publisher (only creates its publisher on first message), so
  the relay-vs-dock_trigger overlap is caught once a goal flows; the orphaned-dock_trigger case
  (eager publisher) is caught immediately.

**Status:** ✅ done · ✅ validated.

---

## Security fix — removed hardcoded Pi sudo password from tune.sh

**Problem:** `scripts/tune.sh` hardcoded the Pi sudo password (`echo admin | sudo -S …`, ×2) — a secret
in the repo, violating the project's "no secrets in repo" rule.

**File:** `scripts/tune.sh` — replaced `echo admin | sudo -S` with plain `sudo` (prompts interactively).
Comment updated. `bash -n` OK.

**Status:** ✅ done.

---

## FW — Precise low-speed RPM (period method) — flashed & deployed

**Problem:** `/debug` rpm came out as a coarse 0/3/6/9 staircase. Root cause: the Encoder measured
speed by counting INTEGER ticks over a fixed ~20 ms window; at 1024 CPR + ~50 Hz only a few ticks
land per window → ~2.9 rpm per tick resolution. Not a rounding bug — a low-speed resolution limit.

**File:** `~/linorobot2_hardware/firmware/lib/encoder/encoder.h` (generic/Teensy `Encoder::getRPM()`),
mirrored to `firmware/lib/encoder/encoder.h` (instance repo). Backup on Pi: `encoder.h.bak`.
- Period method: only CLOSE the measurement window when ≥1 new edge arrived, so `dt` spans the true
  time between edges → fine resolution at low speed. 150 ms with no edge ⇒ rpm 0 (stopped). New
  member `prev_rpm_` holds the value between edges. Targeted ONLY the Teensy class (not ESP32/PICO).

**Done on the Pi:** patched → `pio run -e teensy40` SUCCESS (10.8 s) → flashed (`teensy_loader_cli`,
"Booting") → micro-ROS agent restarted, Teensy reconnected. ✅

**Status:** ✅ flashed. Verify in the GUI: rpm should show fine values (e.g. 5.2, 5.8) instead of 0/3/6.

## Deploy — platform-sw pushed to the robot (Pi) & rebuilt

The PC platform-sw (integration + A1–A6 fixes) was AHEAD of the Pi (Pi = older PR#18 state + local
field tuning). Deployed the changed CODE (not maps / not unit calibration) to the Pi:
- Backed up the Pi src (`~/src_backup_*.tgz`), rsynced the 9 modified + 4 new files, plus the missing
  `openamrobot_bringup` package scaffolding (setup.py/cfg, module, resource, tests — the Pi's bringup
  was incomplete because the Pi used the legacy `openamr_real_bringup` instead).
- `colcon build --symlink-install` on openamrobot_nav2 / openamrobot_docking / openamrobot_bringup →
  all SUCCESS (cleared one stale symlink in build/install).
- Verified on the Pi: `bringup.launch.py --show-args` parses (sim/use_docking/map); installed
  `navigation_launch.py` has collision_monitor + velocity_smoother; new docking/relay launch files
  present in install.

⚠️ **Footprint note:** the deployed `nav2_params.yaml` uses the TRUE chassis footprint
`[0.415, 0.19 … 0.29]` (0.78×0.58). The Pi previously ran the inflated `[0.535 … 0.41]` margin. This
is correct now that collision_monitor is active (A1), but **watch the first real runs** (audit B3).

**Status:** ✅ deployed & rebuilt. ⏳ real-robot validation = Phase E.

## R — Review corrections (Raj Indulkar, 27 June 2026)

Applied in response to the PR review. See `docs/integration-review-response.html` for the full matrix.

- **R-PR4 trans_stopped_velocity** 0.25 → **0.02** (was > max_vel_x 0.20). ✅
- **R-PR4 vy_samples** 5 → **1** (differential base, max_vel_y=0); **BaseObstacle.inflate_cost** removed (inert in Jazzy). ✅
- **R-PR2 RPLIDAR** `angle_compensation` → **`angle_compensate`** (correct rplidar_ros param). ✅
- **R-PR4 velocity limits aligned**: `velocity_smoother` max_velocity/accel/decel now match the DWB
  limits (0.20 / 0.5 / accel 0.5 / decel −2.5,−2.0) — one approved real-robot limit. ✅
- **R-PR1 SLAM scan**: `slam.yaml` `scan_topic` `/scan` → **`/scan_filtered`** (no chassis arcs in maps). ✅
- **R-PR1 QoS doc corrected**: perception README + `scan_body_filter.py` no longer claim Nav2
  universally requires RELIABLE; reworded to endpoint-compatibility (verify with `topic info --verbose`). ✅
- **R-PR3 geometry**: `sign_test.py` / `guided_encoder_test.py` `LR` 0.45 → **0.46** (matches firmware). ✅
- **R-PR1/PR2 scan ownership (cross-PR invariant)**: the scan body filter was **removed from
  `navigation_launch.py`** (the generic nav layer) and made a **data-source responsibility** — the SIM
  profile starts the laser_filters chain in `bringup.launch.py`, the REAL profile via
  openamrobot_perception, and `sim_bringup_launch.py` (legacy) starts its own. navigation_launch only
  CONSUMES `/scan_filtered`. **Validated in sim: exactly 1 publisher, 4 subscribers** (AMCL + 2
  costmaps + collision_monitor), full nav + safety nodes active. ✅
- **Deployed** to the Pi (`deploy_to_pi.sh`, rsync + colcon build, 4 pkgs) — PC and Pi in sync. ✅

## R-FW — Firmware safety block (Raj PR5) — built, flashed, mirrored

One reflash, four items. Files edited on the Pi (source of truth), then mirrored to
`firmware/{src/firmware.ino, lib/pid/pid.cpp, lib/pid/pid.h}`. Pi backups: `.bak2` / `.bak`.

- **R-PR5 #19 PID** (`pid.h`/`pid.cpp`): explicit init of `integral_/derivative_/prev_error_` (were
  indeterminate); added **`reset()`**; **saturation-aware anti-windup** (conditional integration:
  the integral grows only when the output isn't pushed further into saturation). ✅
- **R-PR5 #3 watchdog** (`moveBase`): on stale `/cmd_vel` (>200 ms) → **deterministic full stop +
  PID reset** (was: velocity zeroed but PID still running). `moveBase` restructured: open-loop path
  first (exclusive), then watchdog, then closed-loop; odometry always updates. ✅
- **R-PR5 #20 odom dt** (`moveBase`): reject abnormal first/large `vel_dt` (≤0 or >0.5 s → 0) so the
  first odometry sample doesn't jump. ✅
- **R-PR5 #2 (bounds part)** (`openloopCallback`): reject non-finite values + clamp to
  `0.7*PWM_MAX`. The full **arming / exclusive diagnostic mode** (new subscriber + GUI handshake) is
  the remaining part — 🔶.

**Done:** `pio run -e teensy40` SUCCESS → flashed ("Booting") → agent restarted, Teensy reconnected.
**Status:** ✅ #3, #19, #20 flashed · 🔶 #2 partial (bounds done, arming TODO). Bench plots (step,
saturation, timeout) still to attach for Raj.

## R2 — Review corrections, batch 2 (Raj review)

- **R-PR2 #12 map gating** (`bringup.launch.py`): `map` default now empty. Real (`sim:=false`) **raises
  a clear error** without an explicit `map:=` (no silent bundled-map fallback); both profiles verify
  the map file exists. Sim with empty map → bundled walled_world map. ✅
- **R-PR1 #27 camera params** (`camera.launch.py`): width / height / format / frame_id / camera_name
  are all launch arguments (defaults match this unit); node name = `camera_name` (aligned). ✅
- **R-PR1 #26 input validation** (`scan_body_filter.py`): `_pairs_rad` now rejects odd-length sector
  lists, non-finite values and reversed/wrapped pairs; `close_max` must be positive & finite. (Unit
  tests `colcon test`: still to add — 🔶.) ✅ validation
- **R-PR5 #21 firmware reproducibility** (`firmware/README.md` + `firmware/apply_overlay.sh`): pinned
  upstream `linorobot/linorobot2_hardware @aaf9d59` (branch `jazzy`); overlay file list documented;
  apply script clones + checks out the commit + copies the overlay. (CI: noted as next step.) ✅
- **Deployed** bringup + perception to the Pi (in sync).

## R3 — Diagnostics safety (Raj PR3 #4/#22)

- **#22 `high_rate_capture.py`** rewritten: on the first jerk it **STOPS IMMEDIATELY** (zero command
  at the trigger instant) then logs the coast-down **passively** (was: kept driving 0.4 s after the
  jerk). + `--arm` required, finite/bounded speed & duration, **fresh-telemetry-required** before any
  motion. ✅
- **#4/#22 `openloop_test.py`**: same safety gate — `--arm` required, PWM/duration finite + bounded
  (|pwm|≤500, dur≤30 s), and refuses to drive without fresh `/debug` telemetry. ✅
- Pattern established; remaining powered scripts (`powered_debug_test`, `guided_encoder_test`,
  `sign_test`, `yawtest`) to get the same gate — 🔶. Exclusive-ownership (mux) check: with #1 mux.
- (These scripts run on the PC; firmware already bounds `/debug/openloop` independently — defense in depth.)

## R4 — Review corrections, batch 4

- **R-PR3 #30 diagnostics split** (`scripts/README.md`): tools categorized by risk — **read-only**
  (low-risk PR) vs **powered** (require `--arm`) vs launch/config. Clear separation for a low-risk PR. ✅
- **R-PR4 #29 nav vs docking tolerances**: verified they are **already separate** — nav uses coarse
  `xy_goal_tolerance 0.35`, docking uses its own tight tolerances (`docking_threshold 0.05`,
  `scan_centring_tolerance 0.035 rad`, `spin_yaw_tolerance 0.02 rad`); the docking sequencer does NOT
  use the nav tolerance. Documented in `nav2_params.yaml`. (The base-config + sim/real overlay
  refactor is the remaining part — 🔶.) ✅ tolerance separation
- **R-PR5 #28 firmware build profile** (`firmware.ino`): `#define ENABLE_POWERED_DEBUG` gates the
  raw-PWM motor application. Defined = current commissioning build; commenting it out yields a
  **production image where `/debug/openloop` cannot drive the motors** (subscriber kept → executor
  count unchanged). **Build-verified** (SUCCESS); not reflashed (behavior identical with the define
  on). Mirrored. ✅

## Tools — `pid_tuner.py` (interface) + live PID-tuning session

**Interface improvements** (`scripts/pid_tuner.py`):
- Open-loop/PID radio moved below the sliders (no longer overlapped the Kp/Ki/Kd labels).
- PWM slider max → 1023 (firmware full-scale, was 220); default 150.
- `duration (s)` slider (0.5–15 s) for the step length.
- RPM plot smoothed (moving average) + raw faint — readable trend (the encoder period fix made raw rpm fine, but smoothing keeps the curve clean).
- Speed slider shows **both** m/s and the equivalent wheel rpm.
- **PWM OUTPUT** plotted on a 2nd axis (cyan/magenta dotted) with the saturation ceiling — tells gain-limited (PWM low) vs torque/battery-limited (PWM pinned ~1023) apart.
- Gain slider ranges widened: Kp 0–20, Ki 0–10, Kd 0–3.

**Live PID-tuning findings (real robot, wheels in the air):**
- The live tune works (`/debug/tune` applied by the firmware) and the encoder period fix gives fine rpm.
- A good common gain set lands around **Kp ≈ 0.8, Ki ≈ 0.2, Kd ≈ 0.5** — the **RIGHT wheel tracks cleanly** there.
- The **LEFT wheel keeps a slow (~1 s) sustained limit cycle (±6 rpm) that barely responds to Kp/Kd** → not a linear damping problem. Likely **stick-slip (integral-driven)** and/or the **left-wheel cable faux-contact** (known hardware blocker [[amr-left-wheel-faux-contact]]). Next: drop Ki (0.2→0.1→0.05); if it persists at Ki≈0 it's the cable (no gain fixes it).
- **Principle (diff-drive):** keep ONE common Kp/Ki/Kd for both wheels (matched closed-loop dynamics → straight driving), tuned for the WORST wheel; compensate the steady-state asymmetry with the feedforward **R-gain (MOTOR2_GAIN)**, not per-wheel PID gains. The firmware already does this.

## FW — Per-wheel encoder correction + R-gain (flashed 2026-06-29)

**Root cause found for the "left wheel oscillation":** not the PID, not the cable — a **geometric
encoder error** (magnet misalignment). `scripts/encoder_calib.py` (open-loop, constant speed, bins
the measured rpm by wheel angle = counts mod 1024) showed the LEFT encoder reports **±18% (0.84..1.22,
~40% peak-to-peak), 2 cycles/rev**, IDENTICAL across PWM 150/200/250/300 → position-locked, speed-
independent. RIGHT is small (~±5%). The PID was chasing a 40% **measurement** ripple that isn't real.

**Fix flashed:**
- `firmware.ino`: `LEFT_CAL[36]`/`RIGHT_CAL[36]` correction tables (from the calib) + `calib_rpm()` —
  `true = measured / cal[counts mod 1024]`, applied to current_rpm1/2 before the PID and odometry.
- `lino_base_config.h`: `MOTOR2_GAIN` **1.10 → 1.05** (the right wheel ran 4.8% faster at the same PWM).
- Built (SUCCESS), flashed, agent reconnected, mirror synced.

**Result — the correction table DID NOT HOLD (verified by re-running `encoder_calib.py`):**
- v1: LEFT flat (2.3%) ✅ but RIGHT worse (anti-phase, 19%).
- v2 (tables refined `new = residual × old`): BOTH rippled again (left ±5%, right ±8%) → no convergence.
- **Root cause:** the encoder is read **incrementally** — counts reset to 0 at every Teensy boot at a
  random wheel angle, so `counts mod 1024` is an angle **relative to boot, not absolute**. Every reflash
  reboots → the encoder zero shifts (differently per wheel, since they stop at different positions) →
  the fixed table lands at the wrong angle. **A position-indexed table can't work with an incremental
  encoder.**

**Real fix (next):** a **velocity filter** (smooths the 2/rev ripple without a phase reference → survives
reboots; trade-off = some lag, ~½-rev window), or read the **AS5040 absolute angle** (SSI/PWM), or
re-center the magnet (HW). `MOTOR2_GAIN` 1.05 stays (scalar, phase-independent). The flashed v2 tables
should be disabled (CAL=1.0) until the filter replaces them. All data saved for diagrams:
`docs/data/encoder_calib_data.json` + `..._after-correction.json`. Full write-up:
`docs/history/encoder-calibration.md`. Tool: `scripts/encoder_calib.py`. See [[amr-pid-tuning]].

## Remainder
- **C1** (firmware mirror resync): done — full overlay (`firmware.ino`, `lino_base_config.h`,
  `encoder.h`, `pid.*`) + README + apply script mirrored & pinned.
- **C4** (repoint bringall → bringup, remove old): after robot validation (Phase E).

## Global verification (2026-06-26)
`py_compile` OK on bringup.launch.py, navigation_launch.py, dock_trigger.py, docking_real.launch.py.
`bash -n` OK on bringall.sh, tune.sh. **A1 validated end-to-end in sim** (see A1). Install is
symlinked, so launch-file changes are live; nav2 collision_monitor/velocity_smoother are stock
packages (no build needed for the validation that was run).

## FW — Velocity control chain finalized (flashed 2026-06-29)
Full motor velocity loop tuned on the bench and baked as firmware defaults. Baseline gains chased a
speed-dependent overshoot; the fix was structural, not just gains:
- **Feedforward** `PWM = KFF*target_rpm + FF_OFFSET + PID` (`KFF_DEFAULT=7.87`, `FF_OFFSET_DEFAULT=21`,
  firmware.ino). The FF supplies the holding PWM, so the PID barely integrates → **same response shape at
  every speed** (a pure PID makes the integral guess the holding PWM, which differs per speed → overshoot
  that grows with speed). Gains then drop to **K_P=2.0 / K_I=0.10 / K_D=0.10** (lino_base_config.h).
- **Back-calculation anti-windup** (pid.cpp): bleeds the excess out of the integral on saturation
  (vs the old conditional-integration freeze) → no high-speed overshoot.
- **Small-window velocity estimator** (12 counts, firmware.ino): clean rpm at low speed (instant getRPM =
  only ~1 count/sample below 5 rpm → ±70% noise → the PID chased it).
- **Anti-stiction dither** `DITHER_DEFAULT=92` PWM, ±flipped at 25 Hz, **active only <13 rpm**
  (firmware.ino): breaks the low-speed stick-slip limit cycle (0→9 rpm) → smooth motion down to ~0.06 m/s
  for docking. Net average 0 (no speed bias). Below ~0.06 = hard mechanical floor (motor deadband ~120 PWM).
- **`MOTOR2_GAIN` 1.05 → 1.00** (FF + integral now handle the asymmetry).
- **Live tune** `/debug/tune` (Twist): linear=Kp,Ki,Kd; angular.x=R-gain; angular.y=**Kff**; angular.z=**dither**.
  `pid_tuner.py` has sliders for all (incl. Kff, Dither). New tools: `align_enc_cal.py` (fast per-boot
  ripple-table phase align, ~8 s), `apply_enc_cal.py`, `calibrate_and_apply.sh`, `encoder_ref_table.json`.
- Reminder: re-run `align_enc_cal.py` after each Teensy power-cycle (the ripple table lives in RAM).
