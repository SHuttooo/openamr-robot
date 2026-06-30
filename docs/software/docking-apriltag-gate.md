# On-demand AprilTag gate (docking perception)

**Status:** implemented & verified on the real robot — 2026-06-30.
**Where:** `openamr-platform-sw` → `openamrobot_docking`.

## Problem

`apriltag_node` runs the quad detector on **every** camera frame and costs
**~1.6 cores (≈166 % CPU)** on the Pi 5. It is only needed during the **final
dock approach**, yet the docking launch started it **always-on**. During
navigation that left the Pi at **load ~8 on 4 cores** → the Nav2 planner /
controller were starved → **a goal took several seconds to start** (it looked
like the robot was "thinking"; it was actually CPU-starved).

Measured: killing `apriltag_node` dropped the load **8.3 → ~4** and the planning
delay disappeared.

## Goal

Run AprilTag detection **only when docking asks for it**, with **no latency** at
trigger time (no process start, no camera warm-up).

## Design

A tiny gate node sits between the camera and `apriltag_node`:

```
/camera/image_raw ──(apriltag_gate, republishes only while ENABLED)──▶ /apriltag/image_in ──▶ apriltag_node
```

- `apriltag_node` **stays alive** the whole time (already initialised, already
  subscribed to `/apriltag/image_in`).
- The gate keeps **one permanent subscription** to the camera and republishes to
  `/apriltag/image_in` **only while enabled**. Disabled → frames are dropped at
  the gate → `apriltag_node` receives nothing → **~0 % CPU** (verified: 1 %).
- Toggling is just flipping a boolean → **effectively instant (< 100 ms)**.

The toggle is a `std_srvs/SetBool` service, **`/apriltag/set_enabled`**.
`dock_trigger` calls it automatically:
- **ENABLE** once the robot reaches the staging zone (Phase 1 done) — *not*
  during the Nav2 drive there, so the planner keeps the CPU.
- **DISABLE** when the sequence ends (docked / failed / undock — in the
  `finally`, so it always turns off).

> Why not create/destroy the subscription on toggle (to also save the gate's own
> receive cost)? Creating a subscription **inside the service callback**
> (single-threaded executor) is unreliable — the subscription is discovered by
> DDS but its callback is never serviced, so no frames flow. The gate's own
> receive cost is negligible next to apriltag's detection, so we keep one
> permanent subscription and gate the *republish*.

### QoS gotcha (important — do not "optimise" away)

The gate first used **best-effort** for the camera subscription. It worked
alone, but **once `apriltag_node` was also running the best-effort reader got
starved** — frames stopped arriving at the gate (`rx` froze), so apriltag never
processed anything. The camera (`camera_ros`) publishes **RELIABLE, KEEP_LAST
1**; apriltag's `image_transport` subscriber is **RELIABLE, KEEP_LAST 10**.

**Fix:** the gate uses **RELIABLE** on both its subscription and its publisher,
matching both ends. A comment in `apriltag_gate.py` says not to revert this.

## Files

| File | Change |
|---|---|
| `scripts/apriltag_gate.py` | **new** — the gate node (RELIABLE in/out, `SetBool` service) |
| `launch/apriltag.launch.yml` | adds the gate (starts **disabled**); apriltag now reads `/apriltag/image_in` |
| `scripts/dock_trigger.py` | service client + `_set_apriltag(True)` at staging, `_set_apriltag(False)` in `finally` |
| `launch/docking_real.launch.py` | passes `use_apriltag_gate:=true` (real only; sim keeps apriltag always-on) |
| `CMakeLists.txt` / `package.xml` | install the gate + `std_srvs` dependency |

`dock_trigger` params: `use_apriltag_gate` (default **false** → opt-in; the real
launch sets it true), `apriltag_gate_service` (default `/apriltag/set_enabled`).
If the service is absent (e.g. simulation) `_set_apriltag` logs a warning and is
a no-op, so the dock sequence is unaffected.

## Verification (2026-06-30, real robot)

End-to-end, measuring `apriltag_node` CPU through a full toggle cycle:

```
apriltag CPU DISABLED:        1 %
  → enable /apriltag/set_enabled
apriltag CPU ENABLED:       102 %
  → disable
apriltag CPU DISABLED again:  1 %
```

The 1 % → ~100 % → 1 % swing proves the gate forwards only while enabled and the
whole path (camera → gate → apriltag) works.

## Usage

**Automatic (normal operation).** Nothing to do — bring up with docking on and
`dock_trigger` handles enable/disable:

```bash
ros2 launch openamrobot_bringup bringup.launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true
```

**Manual** (test detection, or an operator-UI "perception on" button):

```bash
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"    # on
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: false}"   # off
```

For standalone apriltag testing without `dock_trigger`, launch
`apriltag.launch.yml` with `start_enabled:=true` (or call the service).

## Before / after (operator commands)

| | Before (apriltag always-on) | After (on-demand gate) |
|---|---|---|
| Bring up for nav + docking | `bringup … use_docking:=true` → apriltag at 166 % during nav | same command — apriltag idle (~0 %) until docking |
| Free CPU for nav tuning | **manual** `pkill -f "[a]priltag_node"` after each bringup (then no apriltag left for docking) | **nothing** — it is already idle |
| Get apriltag back for docking | relaunch the docking stack | **nothing** — `dock_trigger` turns it on at the staging zone |
| Toggle by hand | n/a (kill / relaunch) | `ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true/false}"` |

**Net:** the launch command is unchanged; the `pkill` workaround is gone, and
apriltag's 1.6-core cost only appears during the few seconds of the dock
approach.

## Note

The camera frame rate was observed to be **variable (≈6–19 Hz)** during testing.
That is a separate camera-health item to watch before relying on the visual
servo (which likes a few stable Hz); it does not affect the gate.
