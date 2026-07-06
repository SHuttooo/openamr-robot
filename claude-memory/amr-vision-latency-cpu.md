---
name: amr-vision-latency-cpu
description: "THE real docking blocker found 2026-07-02: AprilTag detection latency 250-700ms from Pi5 CPU saturation (load ~8 on 4 cores), NOT the control law. A visual servo fed 300ms-stale tag positions chases/oscillates/loses lock. Culprits: camera 37%, apriltag_gate.py 35% (python full-res republish), apriltag 20%, Nav2 ~45% idle-during-approach, web_video_server 54%. Fixes: gate max_fps throttle (10fps), decimate 2.0, kill viz tools, pause Nav2 during Phase 5."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Full write-up: `docs/AUDIT-2026-07-02-vision-latency-and-compute.md`. Related:
[[amr-docking-bundle-setup]], [[amr-min-velocity-floors]], [[amr-apriltag-on-demand-gate]].

## The finding (chased all the servo symptoms back to this)
The visual servo's oscillation / drift-into-wrong-tag / "aligns but advances badly" /
false **"tag 1 lost"** were all downstream of **stale detections**, not the gains.
Measured with a zero-overhead probe (`scripts/apriltag_latency.py`, reads ONLY
`/apriltag/detections`, no image → adds ~0 CPU so its number is trustworthy):
- `/apriltag/image_in` age ≈ **60 ms** (image feeding the detector is FRESH),
- but `/apriltag/detections` age = **250-400 ms** (was 700 ms + growing at decimate 1.0).
→ the detector's **input queue is backed up**: fed faster than it processes because it
is **CPU-starved**. When latency crossed `detection_max_age` (1.5 s) the tag TF went
stale → `_lookup_tag_cam` returned None → "tag 1 lost".

## CPU snapshot during a real dock — load 8.0 on 4 cores (2× oversubscribed)
camera_node 37% · **apriltag_gate.py 35%** (python re-publish of every full-res frame!)
· apriltag_node 20% · dock_trigger 18% · Nav2 (controller/planner/bt/behavior/collision/
lifecycle/costmaps) ~45% **running idle during the visual approach** · web_video_server
54% (diagnostic streamer). Vision INPUT alone (camera+gate) ≈ 72%.

## Fixes (2026-07-02)
- **Gate throttle DEPLOYED**: `apriltag_gate.py` new param `max_fps` (default 10) — forward
  at most ~10 fps to apriltag so its queue never overflows. **Keeps FULL resolution → no
  tag-precision loss** (unlike lowering camera res, which DOES cost pose precision).
- **decimate 2.0** in `tags_36h11.yaml` (½-res quad detect, refine=True full-res corners)
  = the sweet spot (250ms, good detection). decimate 1.0 = 700ms; decimate 3.0 = faster
  but detection degrades. threads 3.
- **Kill the viz tools for real runs** — `web_video_server` alone = 54% CPU. They inflate
  the latency they measure.
- **NOT YET DONE, highest-value left: pause/deactivate Nav2 during Phase 5** (it uses
  cmd_vel directly, the ~45% nav stack is idle) → frees ~1.5 cores for the detector.

## How to measure (bounded, no `topic hz` over SSH — it hangs)
`python3 ~/apriltag_latency.py` → `DET ..Hz lat=..ms id-Hz={0:..,1:..,2:..}` (freq +
which tags + latency, text-only, ~0 CPU). `ssh ... uptime` → load must be ≤~4.
Enable apriltag first: `ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"`.

## Platform verdict + how others do it
Pi 5 is not "too weak" — it is **over-subscribed** running Nav2 + full-res AprilTag +
camera concurrently, with **no GPU accel for AprilTag** on the Pi. Others: Jetson Orin +
`isaac_ros_apriltag` (GPU, <10ms, off CPU); x86 mini-PC; or **most production AMRs dock
with 2D-LiDAR reflective markers** (reuses the RPLIDAR, no camera compute, Nav2
`opennav_docking`) — the robust/light path if docking must be bullet-proof.
