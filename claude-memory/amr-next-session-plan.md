---
name: amr-next-session-plan
description: "RESUME after 2026-07-02. Docking sequencer + motor are fine; THE blocker was AprilTag detection latency from Pi5 CPU saturation (see amr-vision-latency-cpu). Fixes DEPLOYED but NOT yet verified: gate max_fps throttle (10fps) + decimate 2.0. Next: restart apriltag, measure latency (apriltag_latency.py + uptime), then re-test the dock. Highest-value TODO = pause/deactivate Nav2 during Phase 5."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**RESUME after the 2026-07-02 session.** Full day write-up: `docs/AUDIT-2026-07-02-vision-latency-and-compute.md`.
Key finding memory: [[amr-vision-latency-cpu]]. Docking state: [[amr-docking-bundle-setup]].
Motor/speed: [[amr-min-velocity-floors]].

## Where we are
- **Docking sequencer + drivetrain: fine.** Motor well-sized; velocity floors measured
  (linear 0.05 clean, angular 0.15). Visual corrector rebuilt (PD on tag-1 bearing +
  hysteresis + coast + odom dead-reckoning).
- **THE blocker = AprilTag detection latency 250-700 ms** from the Pi5 being CPU-saturated
  (load ~8 on 4 cores). A stale-fed visual servo chases/oscillates/loses lock. This
  explained ALL the servo symptoms.
- **Fixes DEPLOYED today but NOT verified** (needs an apriltag restart to load them):
  gate `max_fps` throttle (10 fps, kills the input backlog, keeps full resolution) +
  `decimate 2.0`. LiDAR-cut idea REVERTED (stopping the lidar killed detection ~1s;
  param `stop_lidar_in_approach` default false → lidar stays on).

## NEXT SESSION — in order
1. **Verify the latency fix.** Restart apriltag to load the throttled gate + decimate 2:
   `pkill -f apriltag_node; pkill -f "[a]priltag_gate.py"; sleep 1; ros2 launch openamrobot_docking apriltag.launch.yml`.
   Then measure: `python3 ~/apriltag_latency.py` (enable first with the SetBool service) +
   `ssh ... uptime`. **Target: DET lat < ~120 ms, load ≤ ~4.** Do NOT run web_video_server
   / overlay during the measurement (they cost 50%+ CPU and inflate the number).
2. **Re-test the dock** on fresh data — the PD visual corrector should finally settle.
   Live-tune during the run: `visual_servo_kp` (osc→0.7), `visual_servo_kd` (0.35),
   `visual_align_deadband` (tighter align→0.06). All re-read each loop.
3. **Highest-value change left: pause/deactivate Nav2 during Phase 5** (it drives cmd_vel
   directly; the ~45% nav stack is idle but running). Deactivate the nav lifecycle group
   at Phase-5 entry, reactivate at undock → frees ~1.5 cores for the detector.
4. **Nav lifecycle stall** (recurring): if goals do nothing, the navigation group is
   inactive while localization is active. Recovery: 2D Pose Estimate FIRST, then
   `ros2 service call /lifecycle_manager_navigation/manage_nodes nav2_msgs/srv/ManageLifecycleNodes "{command: 0}"`.
   Real fix (serialize nav activation after map→odom) still pending.
5. **Strategic (see audit §5):** if docking must be bullet-proof → consider **2D-LiDAR
   reflective markers** (reuses RPLIDAR, no camera compute) or offload AprilTag to a
   **Jetson**. Otherwise ship the software fixes (throttle + pause-nav) on the current Pi.

## Clean start (verified commands)
- **Kill everything (Pi):** `pkill -9 -f 'micro_ros_agent|rplidar|component_container|apriltag|dock_trigger|nav2|controller_server|planner_server|bt_navigator|behavior_server|smoother_server|amcl|map_server|lifecycle_manager|ekf_node|robot_state_publisher|static_transform|web_video_server|ros2 launch'; sleep 3`
- **One launch (Pi):** source jazzy+linorobot2_ws+camera_ws+openamr-platform-sw + Cyclone/domain0, then
  `ros2 launch openamrobot_bringup bringup.launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true`.
- **RViz (PC):** `rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz` (NEVER bare `rviz2` — no map). Then 2D Pose Estimate.
- **Dock:** `ros2 topic pub --once /dock_trigger std_msgs/msg/Bool "{data: true}"`.
- Full recipe: `docs/RUNBOOK-real-robot.md`, [[amr-pi-ros-commands]], [[amr-nav2-bringup]].

## NB
- Commits without Claude attribution [[amr-commit-no-claude]]; complete copy-paste commands [[amr-commands-always-complete]].
- Still open from before: 6 PRs ready but not opened [[amr-platform-sw-prs]]; camera AF hunts (deterministic LensPosition TODO); wider tag baseline for a straighter dock.
