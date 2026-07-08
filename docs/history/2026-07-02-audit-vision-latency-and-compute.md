# Audit — AprilTag docking, vision latency, and the compute platform (2026-07-02)

Deep-dive after a full day spent making the AprilTag-bundle docking reliable on the
real robot. The docking logic is sound and the motor is fine; **the day's real wall
was vision latency caused by the Raspberry Pi 5 being CPU-saturated when it runs
Nav2 + camera + AprilTag at the same time.** This document records every problem we
hit, answers "is the Pi underpowered / how do others do it", and lists prioritized
fixes.

Platform under test: Raspberry Pi 5 (4 cores), Sony IMX708 @ 1280×720 (camera_ros),
RPLIDAR A1, Teensy firmware (micro-ROS), ROS 2 Jazzy, Nav2, AprilTag 36h11 bundle
(3 coplanar tags) as the dock target. No physical dock — the printed bundle IS the
target.

---

## 1. Executive summary

- The docking **sequencer is functionally complete** (staging → scan → 3-tag normal
  estimate → pre-dock → visual approach → docked) and the **drivetrain is healthy**
  (measured, see §2.1).
- The **visual servo was unstable** (left-right oscillation, drifting into the wrong
  tag, poor final alignment). We rebuilt the corrector (PD + hysteresis + coast), but
  the instability persisted.
- **Root cause found by measurement:** the AprilTag detections the controller consumes
  are **250–400 ms stale** (were 700 ms and growing). A visual servo fed 300 ms-old
  positions *chases* — it corrects for where the tag was, oscillates, and eventually
  loses lock. Latency, not the control law, was the dominant problem.
- The latency is **CPU saturation**: on a real dock the Pi 5 sits at **load ≈ 8 on 4
  cores** (2× oversubscribed). The AprilTag detector is starved, so its input queue
  backs up and the detections go stale.
- **The Pi 5 is not "too weak" in the abstract — it is over-subscribed by running the
  full Nav2 stack + full-resolution AprilTag + the camera pipeline concurrently.** This
  is a resource-budgeting / system-design problem. Others solve it by *not* doing all
  three at full quality on one CPU (see §4).

---

## 2. Every problem we hit today (with root cause)

### 2.1 Motor "struggles at low speed" — RESOLVED (not a fault)
Symptom: the robot juddered/stalled at very low docking speeds; suspected a left-wheel
faux-contact and/or an under-sized motor.

Measured (open-loop test + closed-loop sweeps on the ground, `scripts/min_velocity_sweep.py`):
- Left wheel healthy (10.4 rpm vs right 10.9, no dropouts).
- **Linear floor:** 0.04 m/s reliable, **0.05 m/s clean**; below → stick-slip judder.
- **Angular floor:** **0.15 rad/s** reliable; below → stall.
- Motor Z4BLD60-24GN-30S: 60 W, 30:1 gearbox, ~100 rpm wheel (≈0.49 m/s max),
  ~4.18 N·m/wheel. **Well-sized (over-sized on torque).** Above the floors the
  real/commanded ratio is ~1.0.

Conclusion: the floors are **stick-slip + coarse Hall commutation at low RPM** (running
a geared BLDC at ~10-30 % of max speed), NOT a torque shortfall. Docking speeds were
re-based above the floors (taper floored at 0.05, scan at 0.17, a `min_turn_omega`
0.15 floor for yaw corrections). See `claude-memory/amr-min-velocity-floors.md`.

### 2.2 Visual servo instability
Symptoms across the day: (a) drove into the outer tag (id 0) instead of the centre
(id 1); (b) left-right oscillation; (c) "aligns but advances poorly"; (d) not aligned.

Work done (all in `dock_trigger.py::_final_visual_approach`):
- Made the **camera-frame visual corrector dominant** over the noisy map-frame
  pure-pursuit line (raised `freeze_axis_distance` to 1.5 m; line only does the far
  coarse leg).
- Rebuilt the corrector as a **PD** on the image-frame bearing to the centre tag
  (`omega = -(kp·bearing + kd·d_bearing/dt)`), with solvePnP-spike rejection.
- Added a **hysteresis deadband** so it drives straight when aligned and only commits a
  correction past a threshold (kills per-frame bang-bang from the stick-slip floor).
- Added **coast-straight through brief tag dropouts** (instead of stutter-stopping) and
  an **odometry dead-reckoning** of depth for the last blind centimetres.

Outcome: better, but the oscillation/misalignment persisted — because the *input* was
stale (§2.5). Good control on 300 ms-old data still chases.

### 2.3 The LiDAR IR-dot dead end
Hypothesis (from earlier notes): the RPLIDAR's IR laser dot sweeps the tags and drops
detections. We wired the sequence to **stop the LiDAR at the FAR→NEAR hand-over**
(NEAR is camera-only), non-blocking, restart at the end, with the control loop made
robust to a stale `map→odom` TF (pose optional, odom dead-reckoning).

Result: **stopping the LiDAR motor killed the AprilTag detection within ~1 s** (tag
lost → abort), reproducibly. Most likely the rplidar node and apriltag share a process
container / the motor-stop disrupts it. **Reverted** and put behind a param
(`stop_lidar_in_approach`, default false) — the LiDAR now stays on the whole dock.
Caveat: because the cut broke detection for an unrelated reason, we never actually
tested the IR-dot hypothesis — whether the IR dot also hurts detection **remains open**
(possibly a compound problem). What is measured and dominant is the latency; the IR dot,
if it contributes, is secondary.

### 2.4 Camera focus
Continuous autofocus (`AfMode=2`) **hunts while moving** → motion blur → dropped
detections at close range. A deterministic focus (drive `LensPosition` from the known
tag distance) was designed but not deployed — deprioritized once latency was found to
dominate. Still worth doing (§5).

### 2.5 ROOT CAUSE — AprilTag detection latency from CPU saturation
Measured with a purpose-built probe (`scripts/apriltag_stats.py`, then the
zero-overhead `scripts/apriltag_latency.py` that reads only `/apriltag/detections`):

| Config | Detection rate | Detection latency | Notes |
|---|---|---|---|
| `decimate 1.0` (full-res quad detect) | ~8 Hz | **700 ms, GROWING** | queue backlog; latency crossed `detection_max_age` (1.5 s) → false "tag 1 lost" |
| `decimate 2.0` (½-res quad, full-res refine) | ~15 Hz | ~250 ms, stable | 3× better; all 3 tags, margin ~85 |
| `decimate 2.0`, featherweight probe, real dock | 2–19 Hz (thrashing) | **250–390 ms sustained** | confirms it is REAL, not a measurement artifact |

The image *feeding* the detector is fresh (`/apriltag/image_in` age ≈ 60 ms), but the
detector emits detections stamped 250–400 ms old → **its input queue is backed up**:
it is fed faster than it can process because it is **starved of CPU**.

CPU snapshot during a real dock: **`load average 8.0` on 4 cores.**

| Process | %CPU | Note |
|---|---|---|
| `web_video_server` | 54 % | diagnostic streamer — kill during real runs |
| `camera_node` | 37 % | IMX708 @ 1280×720 |
| `apriltag_gate.py` | 35 % | **Python re-publish of every full-res frame** |
| `apriltag_node` | 20 % | the detector itself |
| `dock_trigger.py` | 18 % | the sequencer |
| Nav2 (controller/planner/bt/behavior/collision/lifecycle/costmaps) | ~45 % | **runs idle during the visual approach** |

So the "AprilTag is slow" is really "the Pi is 2× oversubscribed, everything time-slices,
the detector's queue grows." The vision *input* pipeline alone (camera + gate) is ~72 %.

Fix deployed today (precision-preserving): a **throttle in `apriltag_gate.py`
(`max_fps`, default 10)** — forward at most ~10 fps to the detector so its queue never
overflows. Full resolution is kept (no precision loss, unlike lowering the camera
resolution). Expected: latency → ~1 frame (~100 ms), gate + detector CPU down.

### 2.6 Nav2 lifecycle stall at boot
The unified bringup launches everything at once; the **navigation** lifecycle group
came up **inactive** (planner/bt_navigator/behavior/smoother/velocity_smoother) while
the **localization** group (map_server, amcl) was active → goals did nothing. This is a
recurring boot-ordering / bond-timeout issue. Recovery: 2D Pose Estimate first, then
re-trigger the manager (`ManageLifecycleNodes command:0`). Proper fix pending (serialize
nav activation after `map→odom`, or raise bond timeouts). RViz also needs a **config**
(`-d openamr_nav.rviz`) — bare `rviz2` shows no map.

---

## 3. Is the Raspberry Pi 5 underpowered for this?

**Honest answer: borderline, and only because we run everything at full quality at once.**

- The Pi 5 (Cortex-A76 ×4) is genuinely capable — it runs Nav2 + SLAM comfortably, or a
  camera + AprilTag comfortably. **What it cannot do is all of them concurrently at full
  resolution with headroom.** AprilTag's quad detector is the expensive part (~1.5 cores
  full-res); add the camera ISP-in-software (camera_ros), a Python image-forwarding gate,
  and the full Nav2 stack, and 4 cores are gone.
- There is **no GPU/NPU acceleration** for AprilTag on the Pi. The detector runs on the
  CPU, competing with everything else. On accelerated platforms the same detection is
  <10 ms and off the CPU entirely.
- Two structural wastes make it worse than it needs to be: (1) the **Python gate
  re-publishing full-res frames** (35 % CPU for a passthrough), and (2) **Nav2 running
  at ~45 % during the visual approach, when it is not used at all** (Phase 5 drives
  `/cmd_vel` directly).

So: not "the Pi is junk", but "this is the wrong resource budget for one Pi." With the
optimizations in §5 it can be made to work; for comfortable margins you either offload
vision or change the docking modality.

---

## 4. How others do it (comparison)

### 4.1 Compute platform
- **Hobby / light robots:** Raspberry Pi (like us) — fine if vision is light or
  time-shared, painful if you also run heavy Nav2 + real-time fiducials.
- **Serious / commercial AMRs:** an **x86 mini-PC (Intel NUC / equivalent)** for Nav2 +
  perception, or an **NVIDIA Jetson (Orin Nano/NX/AGX)** when vision is heavy. Jetson's
  `isaac_ros_apriltag` runs AprilTag **on the GPU in sub-10 ms**, leaving the CPU for
  Nav2. This is the single biggest difference from our setup.
- **Real-time control** is almost always on a **separate microcontroller** (we already do
  this — the Teensy), so motion never competes with vision for scheduling.

### 4.2 Docking modality — most production AMRs do NOT use a camera + AprilTag
- **2D-LiDAR + reflective markers** (V-shaped or flat retro-reflectors): the *dominant*
  industrial approach. The existing safety LiDAR sees high-intensity returns from the
  reflectors and triangulates the dock. **No camera, no GPU, robust to lighting**, and it
  reuses a sensor we already have (RPLIDAR A1 reports intensity). Nav2 even ships an
  `opennav_docking` framework oriented this way.
- **IR beacon homing** (iRobot-style dock): the dock emits coded IR; the robot homes on
  it. Cheap, very robust at short range, needs a powered dock.
- **Depth camera (RealSense/OAK) + ICP / AprilTag on-device:** OAK cameras run the
  detector **on the camera** (Myriad X), offloading the host entirely.
- **Physical self-alignment:** a funnel / V-guide on the dock does the last-centimetre
  alignment mechanically, so the vision only needs coarse accuracy — this is why many
  docks look "sloppy" in software but still seat perfectly.
- **Camera + AprilTag (our approach)** is common in research and for markerless/flexible
  targets, but it is the most compute-hungry option and the most lighting/focus-sensitive.

### 4.3 Vision-pipeline tricks everyone uses
- **Detect at reduced resolution / with decimation**, refine corners at full res (we do
  this now via `decimate`).
- **ROI tracking:** run the full detector once to acquire, then only process a crop
  around the last known tag → an order of magnitude cheaper. AprilTag_ros lacks this
  natively; it is a common custom add-on.
- **Cap the detector's frame rate** to what it can sustain (we just added this to the
  gate) — prevents queue backlog / stale detections.
- **Run vision only in the docking window**, and **reduce/pause navigation** while
  docking (they are never both critical at the same instant).
- **Hardware ISP / GPU** for debayer + resize so the CPU never touches raw frames.

---

## 5. Solutions to improve — prioritized

### A. Now — software, free, keep the Pi
1. **Throttle the AprilTag input** to ~10 fps (DONE — `apriltag_gate.py max_fps`). Kills
   the backlog → detections fresh, full resolution kept.
2. **Never run the visualization tools during a real dock** (`web_video_server` alone was
   54 % CPU). Use them to diagnose, kill them to run.
3. **Pause / deactivate Nav2 during the visual approach.** Phase 5 uses `/cmd_vel`
   directly; the controller/planner/costmaps (~45 % CPU) are idle but running.
   Deactivate the nav lifecycle group at Phase-5 entry, reactivate at undock → frees
   ~1.5 cores exactly when the detector needs them. **Highest-value software change left.**
4. **Replace the Python gate with a zero-copy / C++ or intra-process** forwarder, or
   drop the gate entirely during docking and gate detection a different way — its 35 %
   full-res re-publish is pure overhead.
5. **Deterministic camera focus** (`LensPosition` from tag distance) to end AF hunting.
6. **ROI tracking** after first acquisition — biggest algorithmic win if we stay on CPU.
7. Keep `decimate 2.0` (good detection); only lower resolution as a last resort
   (it *does* cost tag-pose precision — avoid).

### B. Medium — offload the vision
8. **NVIDIA Jetson Orin Nano** + `isaac_ros_apriltag` (GPU, <10 ms, off the CPU). Robust
   margins, keeps the camera+AprilTag design. The clean answer if we keep this modality.
9. **OAK-D / Luxonis camera** — runs the fiducial detector on-camera, host stays free.
10. **Coral USB TPU** — helps for NN detectors, less so for classic AprilTag.

### C. Best-for-production — change the docking modality
11. **Switch docking to 2D-LiDAR reflective markers.** Reuses the RPLIDAR, no camera
    compute, no focus/lighting fragility, and aligns with Nav2's `opennav_docking`. This
    is how most real AMRs dock. Highest robustness, lowest compute — at the cost of
    reworking the dock target (reflectors instead of printed tags) and the detector.
12. **Add a mechanical V-guide** on the dock so vision only needs coarse accuracy.

### Recommended path
- **Short term:** ship A1–A3 (throttle + kill viz + pause Nav2 during the approach). This
  alone should bring the *effective* detection latency under ~120 ms on the current Pi and
  make the visual servo behave — no new hardware.
- **If docking must be bullet-proof for production:** move to **2D-LiDAR reflectors**
  (C11) — it is the most robust and the lightest on compute — or offload AprilTag to a
  **Jetson** (B8) if the camera/tag design must stay.

---

## 6. One-line takeaway
The docking maths and the motor are fine. The blocker is **feeding a real-time visual
servo from a CPU-starved detector**. Fix the *resource budget* (throttle vision, stop
running Nav2 and the detector flat-out at the same time) before touching the control
gains again — or move the fiducial detection off the CPU / to the LiDAR.

*Companion notes: `claude-memory/amr-min-velocity-floors.md`,
`docs/history/diagnostics.md`, `docs/RUNBOOK-real-robot.md`. Diagnostic tools added
today: `scripts/apriltag_latency.py` (zero-overhead latency), `scripts/apriltag_stats.py`,
`scripts/apriltag_det_overlay.py`, `scripts/apriltag_opencv_view.py`,
`scripts/min_velocity_sweep.py`.*
