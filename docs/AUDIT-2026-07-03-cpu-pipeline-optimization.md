# Audit — CPU / vision-pipeline optimization (2026-07-03)

Follow-up to `docs/AUDIT-2026-07-02-vision-latency-and-compute.md`. Yesterday we blamed
"CPU saturation". **Today's measurements refine that: the Pi 5 is NOT out of CPU, thermal,
memory, or I/O headroom. The docking detector starves because of the pipeline
*architecture* — inter-process message churn, not a lack of cores.** This document records
the evidence and lists every concrete action to fix it.

Robot: Pi 5 (4 cores), IMX708 @ 1280×720 via `camera_ros`, `apriltag_ros`, Nav2, CycloneDDS
domain 0. Dock target = printed 3-tag 36h11 bundle.

---

## 1. Evidence (measured live during load)

`vmstat 1` + `mpstat -P ALL` while the full stack ran (camera + apriltag + Nav2 + dock):

| Metric | Value | Meaning |
|---|---|---|
| CPU idle | **48–55 %** | **half the cores are FREE** |
| iowait | **0 %** | not disk/USB bound |
| run-queue `r` | 0–2 | almost nobody waiting for a core |
| swap | 0, 2.3 GB free | not memory bound |
| temp / throttle | **50 °C / 0x0** | **no thermal throttling** |
| **context switches** | **35 000 / s** | pathological scheduling churn |
| system time `sy` | **20 %** | kernel busy shuffling messages, not computing |
| softirq | 2–4 % | network/DDS interrupt load |

Pipeline rates (idle, apriltag on):
`/camera/camera_info` **28.7 fps** vs `/camera/image_raw` **10.4 fps** (3× mismatch) →
`/apriltag/image_in` **5.3 fps** → detections sparse. During a real dock the camera
collapses to ~3 fps and the gate forwards <1 fps → the visual servo loses the tag → abort.

## 2. Root cause — inter-process churn, not compute

The image path today is **3 processes and 2 DDS hops**:

```
camera_node ──DDS──▶ apriltag_gate.py ──DDS──▶ apriltag_node
 (process 1)         (process 2, Python/GIL)     (process 3)
```

Every 1280×720 RGB frame (2.7 MB) is **serialized + copied + DDS-delivered twice**, and the
middle hop is a **single-threaded Python node (GIL) in the hot path** re-publishing full-res
frames. With 50 % idle CPU, the bottleneck is clearly **serialization + scheduling + the
Python serialization point**, not core count. That is what produces 35 k ctx/s and 20 % sys
time, and what starves the detector.

**Conclusion: this is an architecture/optimization problem, not an under-powered Pi.** The
robotics logic (sequencer, motor, detection quality — margins 80–96) is sound; the vision
plumbing was never optimized. A full-res Python passthrough in the critical path is the
classic anti-pattern.

## 3. Feasibility confirmed on this Pi
- `ros2 component types` →  `camera_ros / camera::CameraNode` **and** `apriltag_ros / AprilTagNode`
  are both **composable** → they can share one process with intra-process (zero-copy) comms.
- Camera exposes `FrameDurationLimits` (fps cap) and `SyncFrames`.
- No `CYCLONEDDS_URI` set → default DDS; tuning headroom exists (mostly obviated by composition).

---

## 4. ACTIONS — concrete, prioritized

### A. Architecture — remove the IPC churn (the root cause) — HIGHEST IMPACT
- **A1. Compose camera + apriltag into ONE `component_container_mt`** with
  `use_intra_process_comms=True`. Load `camera::CameraNode` and `apriltag_ros::AprilTagNode`
  as `ComposableNode`s; remap the apriltag image input to the camera image topic (same
  process → passed by pointer, no DDS, no copy).
  - *Effect:* eliminates 2 DDS hops + 2 full-frame serializations → kills most of the 35 k
    ctx/s and the added latency; the detector is fed at the true camera rate.
  - *Files:* new `openamrobot_docking/launch/apriltag_composed.launch.py` (sketch in §5);
    keep `camera.launch.py` params (width/height/calibration) as ComposableNode params.
  - *Effort:* medium. *Risk:* medium (QoS/intra-process wiring; validate detections still flow).
- **A2. Drop the Python gate from the hot path.** Do on-demand gating by **loading/unloading
  the `AprilTagNode` component** from the container (container `~/_container/load_node` /
  `unload_node`, or lifecycle) at dock start/stop — instead of a Python republisher that runs
  full-res forever. When not docking → unload apriltag (frees ~1 core). When docking → load it.
  - *Effect:* removes the GIL passthrough (~40 % CPU + latency) entirely; apriltag CPU is 0
    outside docking (same benefit the gate gave) but with no per-frame Python cost.
  - *Files:* `dock_trigger.py::_set_apriltag` → call container load/unload instead of the
    `SetBool` gate service; retire `apriltag_gate.py` from `apriltag*.launch`.
  - *Effort:* medium. *Risk:* medium.

### B. Camera tuning — cheap, immediate, zero precision loss
- **B1. Cap the camera frame rate to ~15 fps.** Set `FrameDurationLimits: [66667, 66667]`
  (µs → 15 fps) — the detector never needs more; fewer frames = less churn.
  - *File:* `openamrobot_perception/launch/camera.launch.py` (add param), or live:
    `ros2 param set /camera FrameDurationLimits "[66667,66667]"`.
  - *Effect:* camera_node CPU + ctx/s down; **no resolution/precision change**.
- **B2. Fix the camera_info(30)/image(10) rate mismatch.** Capping fps (B1) aligns them; if
  the mismatch persists, check `SyncFrames`. Removes the apriltag "not synchronized" warnings
  and wasted camera_info traffic.

### C. Nav / system — secondary now (cores are NOT the wall) but still trims churn
- **C1. Deactivate idle Nav2 nodes during Phase 2–7.** Per-node (NOT the lifecycle-manager
  `PAUSE`, which would also kill `velocity_smoother`/`collision_monitor` that carry
  dock_trigger's `/cmd_vel_nav`→`/cmd_vel`). Deactivate:
  `controller_server planner_server bt_navigator behavior_server smoother_server waypoint_follower`.
  Reactivate at undock. Integrate into `dock_trigger.py` (deactivate at Phase-2 entry).
  - *Effect:* trims the ~45 % nav churn during the approach. Reversible.
- **C2. Never run `web_video_server` / the UI camera view during a real dock** (54 % CPU when
  the stream is open). Diagnose with it, kill it to run.

### D. DDS tuning — optional, if churn persists after A–C
- **D1.** Add a `CYCLONEDDS_URI` config: enable shared-memory (Iceoryx) for large messages
  and/or reduce discovery churn. Composition (A1) already removes the image path from DDS, so
  this is mostly for the remaining topics.

### E. Robustness — belt & suspenders
- **E1.** Keep `dock_trigger`'s coast-through-dropout + odom dead-reckoning; with A–B the
  detector should no longer starve, but the tolerance stays as a safety net.

### F. Verification protocol (run before/after EACH change)
- `bash /tmp/cpusnap.sh "<label>"` (load + top procs, builds a comparison table).
- `python3 ~/apriltag_latency.py` (detector rate + latency; target < ~120 ms).
- `vmstat 1 3` (watch **context switches** drop — the real KPI here) + `mpstat -P ALL 1 1`.
- Dedicated docking log: `tail -f ~/docking.log` (standalone stack via `~/dock_stack.sh`).

---

## 5. Sketch — composed launch (A1)

```python
# openamrobot_docking/launch/apriltag_composed.launch.py  (sketch)
from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

def generate_launch_description():
    container = ComposableNodeContainer(
        name='vision_container', namespace='', package='rclcpp_components',
        executable='component_container_mt',           # multithreaded
        composable_node_descriptions=[
            ComposableNode(
                package='camera_ros', plugin='camera::CameraNode', name='camera',
                parameters=[{'width': 1280, 'height': 720, 'format': 'RGB888',
                             'FrameDurationLimits': [66667, 66667],   # 15 fps (B1)
                             'camera_info_url': 'file://.../camera_info.yaml'}],
                extra_arguments=[{'use_intra_process_comms': True}]),
            ComposableNode(
                package='apriltag_ros', plugin='AprilTagNode', name='apriltag',
                namespace='apriltag',
                parameters=['.../config/tags_36h11.yaml'],
                remappings=[('image_rect', '/camera/image_raw'),
                            ('camera_info', '/camera/camera_info')],
                extra_arguments=[{'use_intra_process_comms': True}]),
        ], output='screen')
    return LaunchDescription([container])
# On-demand (A2): load/unload the apriltag ComposableNode via the container services
# instead of the Python gate.
```

## 6. Recommended order
1. **B1** (cap fps) — 1 line, measure the ctx/s drop. (5 min)
2. **A1** (compose camera+apriltag, intra-process) — the root-cause fix. Measure ctx/s +
   latency; expect the biggest win.
3. **A2** (retire the Python gate; on-demand via load/unload). 
4. **C1** (nav deactivate during docking) — trim the rest.
5. **D1** only if ctx/s is still high.

Target after A+B: docking with detections fresh (<120 ms), ctx/s back to a few thousand,
no camera collapse → the visual servo finally settles. No new hardware.

*Companion: `docs/AUDIT-2026-07-02-vision-latency-and-compute.md`,
`claude-memory/amr-vision-latency-cpu.md`, `~/dock_stack.sh` (standalone docking + log).*
