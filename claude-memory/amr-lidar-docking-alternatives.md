---
name: amr-lidar-docking-alternatives
description: "Strategic docking alternatives researched 2026-07-02, after camera+AprilTag hit a CPU-latency wall. Most production AMRs dock with 2D-LiDAR: (A) retroreflective markers by intensity, or (B) a V-notch marker by geometry. KEY pro insight: they don't rely on a precise sensor — they put intelligence in the MECHANICS (V-funnel self-centers the last cm + floating connectors + contact/current confirmation), so sensing only needs ~1-2cm. We took the hard path (precise camera+tag, no funnel, saturated Pi)."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Researched after the AprilTag docking hit the vision-latency wall ([[amr-vision-latency-cpu]]).
Deliverables to share with Alex & Raj: `docs/vision-latency-report-2026-07-02.html` (the
day's problem/audit, self-contained) + a 2D-LiDAR docking A/B comparison HTML (V-notch
diagrams). Full analysis: `docs/AUDIT-2026-07-02-vision-latency-and-compute.md` §4–5.

## Why look at LiDAR docking
Camera+AprilTag makes the sensor carry everything (precision AND freshness) → it broke on a
CPU-starved Pi. A 2D-LiDAR dock **sidesteps the CPU problem**: the scan is already processed
for nav, so marker detection is nearly free (no image pipeline, no GPU, invariant to light).

## The two LiDAR methods
- **A — retroreflective markers (intensity):** reflective tape/plates on the dock; the LiDAR
  `intensities` field spikes at them (they "shine"). Threshold → cluster → known spacing
  pattern → dock pose. Needs 2-3 markers AND a lidar with a usable intensity channel.
- **B — V-notch marker (geometry):** a rigid concave V (notch opens TOWARD the robot, apex at
  the back = farthest point). Distance-vs-angle draws a ∧ (peak = apex). Fit 2 lines →
  intersection = apex (position), bisector = approach axis (orientation). **One marker gives
  position + orientation**, apex is very precise (2-line intersection averages noise), unique
  signature, and the concave shape funnels the robot in. Works on distance alone (no intensity).

## For OUR robot
- **RPLIDAR A1 has only a coarse "quality" byte, not calibrated reflectivity** → Method A is
  unreliable for us → **Method B (geometry) is the safe bet**, optionally B + reflective tape
  for redundancy if we later fit a better lidar. Nav2 has `opennav_docking` for this style.
- LiDAR is 2D → marker must be at lidar height (~0.18 m on this unit).

## THE strategic insight (most actionable takeaway of the day)
**Professionals do NOT count on a heroically precise sensor.** They put the intelligence in the
**MECHANICS** and layer the system:
1. **coarse sensing** for the approach (lidar reflector, or even a degraded camera),
2. a **mechanical V-funnel / guide** on the dock that self-centers the robot on the last few cm,
3. **floating connectors** (tolerate small offset) + **contact/current confirmation** of mating.
So the sensor only needs ~1-2 cm accuracy; the funnel does the fine alignment. **We took the
hard path** (precise camera+tag pose, no funnel, on a saturated Pi) → everything rides on the
sensor. A €5 mechanical V-guide + a coarse robust sensor would remove most of our software pain.
Recommend raising this with Alex & Raj.
