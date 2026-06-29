# Real-robot runbook & troubleshooting

*How to launch the integrated stack (`openamr-integration` on the Pi) and every pitfall we hit, with its
fix. Read before each test session.*

*Last updated: 2026-06-25.*

Conventions used below:
- **Pi** = the robot's Raspberry Pi (`botshare@172.17.201.29`). **PC** = the Ubuntu dev machine (RViz).
- Each Pi terminal starts by connecting: `ssh botshare@172.17.201.29` (enter the password, wait for the
  prompt) **and only then** paste the rest. Do not paste `ssh` + commands as one block — `ssh` waits for
  the password and the following lines are lost.

### Repositories & paths (do not confuse them)

The navigation software is **one repo, `openamr-platform-sw`**, deployed on both machines under different
paths. A separate repo (`openamr`, *this* one) holds the docs, scripts, RViz config and maps.

| What | Repo | Path |
|---|---|---|
| ROS 2 / Nav2 integration on the **Pi** | `openamr-platform-sw` | `~/openamr-integration/ros2/install/` |
| ROS 2 / Nav2 integration on the **PC** (sim + RViz) | `openamr-platform-sw` | `~/Documents/openAMRobot/openamr-platform-sw/ros2/install/` |
| Docs, scripts, RViz config, maps | `openamr` (instance) | `~/Documents/openamr/` (PC) |

So the `source ...` lines differ between Pi blocks (`~/openamr-integration/...`) and PC blocks
(`~/Documents/openAMRobot/openamr-platform-sw/...`) **on purpose** — same code, two machines.

---

## 1. Launch (overview)

The supported method is **one launch per terminal** (classic ROS, see §12 for navigation and §11 for
mapping). A one-shot helper script (`~/iboot.sh`) also exists on the Pi but the per-terminal method is
preferred for interactive work.

**PC — RViz:**
```bash
source /opt/ros/jazzy/setup.bash
source ~/Documents/openAMRobot/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
Then **2D Pose Estimate** (place the robot; the green scan should snap to the walls) → **2D Goal Pose**
(send a goal) → see §10 to stop a goal.

**Camera** (PC, in a browser — NOT RViz, see §8b):
```
http://172.17.201.29:8080/stream?topic=/camera/image_raw&type=mjpeg
```

**"Everything is up" checks:**
```bash
ros2 topic info /scan            # publisher 1  (lidar)
ros2 topic info /scan_filtered   # publisher 1  (NOT 2 — otherwise duplicate, §4)
ros2 topic info /map             # publisher 1
ros2 lifecycle get /planner_server   # active   (otherwise §3)
```

---

## 2. Lidar: `/scan` = 0 ("cannot bind" / `80008000` / timeout)

**Symptom:** no green scan in RViz, `ros2 topic info /scan` → publisher 0. In the logs:
`Error, cannot bind to the specified serial port` or `Error, operation time out. RESULT_OPERATION_TIMEOUT!`

**Causes** (two distinct ones):
- **Zombie rplidar:** an old `rplidar_composition` (from a previous launch) still holds the port
  `/dev/ttyUSB0`, so the new one cannot connect (`cannot bind`).
- **Hardware timeout** (`80008000`): the RPLIDAR firmware hangs (a recurring A1 issue). The log stops
  right after `RPLIDAR running ... SDK Version: '1.12.0'` without crashing — the firmware is frozen.

**Fix:**
```bash
# 1) kill the rplidar driver(s) -> the launch respawns a clean one that takes the port
pkill -9 -f rplidar_composition
sleep 7
ros2 topic info /scan        # should become 1
# 2) if still 0 -> unplug/replug the lidar USB (power-cycles the A1), wait ~10 s, repeat the pkill
```
> The driver runs with `respawn=True`: once the port is free / the lidar returns, it reconnects on its
> own. For the `80008000` hang, `pkill` alone is not enough — the USB must be physically power-cycled.

---

## 3. No costmap / "Global Status: Error" in RViz

**Symptom:** the map shows but **not the costmaps**; RViz shows `Global Status: Error`;
`ros2 lifecycle get /planner_server` → **inactive**.

**Cause:** navigation started **before** `map→odom` existed. `planner_server` tries to activate its
global costmap, which needs the `map→base_link` transform (i.e. AMCL localized). With no initial pose,
activation fails → `planner_server` stays **inactive** → no global costmap. (`Global Status: Error` = the
`map` frame does not exist yet.)

**Immediate fix** (navigation already launched): do the **2D Pose Estimate** in RViz (→ AMCL publishes
`map→odom`), then activate the nodes that stayed inactive:
```bash
for n in planner_server smoother_server behavior_server waypoint_follower bt_navigator; do
  ros2 lifecycle set /$n activate
done
ros2 lifecycle get /planner_server   # -> active
```
**To avoid it:** do the **2D Pose Estimate early** (right after launch), before the planner gives up.

### 3b. Costmap warning "No map received" (different from the case above)

**Symptom:** `planner_server` **active**, `map→odom` OK, but the **Global/Local Costmap** display stays
**orange** with **"No map received"**; no cyan/magenta.

**Cause:** by default `always_send_full_costmap: False` → the full grid is sent only **once**
(latched/transient_local), then only deltas. RViz connecting **after** that one-shot — especially over
**WiFi**, where the latched sample is not always delivered to a late joiner — never receives the full grid.

**Permanent fix** (already applied in `nav2_params.yaml`): `always_send_full_costmap: True` for
`local_costmap` **and** `global_costmap` → the full grid is republished every cycle (`publish_frequency`
5 Hz / 2 Hz), so RViz always has it. Negligible network cost.

**Live fix** (no restart, should it ever come back):
```bash
ros2 param set /global_costmap/global_costmap always_send_full_costmap true
ros2 param set /local_costmap/local_costmap  always_send_full_costmap true
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
ros2 service call /local_costmap/clear_entirely_local_costmap  nav2_msgs/srv/ClearEntireCostmap "{}"
```

> In RViz, also set the costmap display to **Durability: Transient Local** + **Reliability: Reliable**,
> then **Ctrl+S** to save the config.

---

## 4. `/scan_filtered` has 2 publishers (duplicate filter)

**Symptom:** `ros2 topic info /scan_filtered` → **publisher count 2**; spurious obstacles.

**Cause:** two filters publish `/scan_filtered`: our `scan_body_filter` node (perception) **and** the
`laser_filters` chain that `navigation_launch.py` starts by default (the simulation profile).

**Fix:** launch navigation with **`use_scan_filter:=false`** (the real robot already uses the perception
node):
```bash
ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false use_scan_filter:=false
```
> After launch, check `/scan_filtered` is at **1**.

---

## 5. Zombies / processes piling up (launched several times)

**Symptom:** after several launches, a huge `ros2 node list`, **multiple `map_server`/`rplidar`**,
crashes `Failed to find a free participant index for domain 0` (DDS exhaustion).

**Cause:** nodes run with **`respawn=True`** (lidar, camera, filter). Killing a **node** makes its
**launch parent respawn it** → the kill does not stick → accumulation. Launching twice = two stacks =
DDS exhaustion. Two rplidar drivers also fight over the USB port → `/scan` drops to 0.

**Fix:** **ordered kill** — the **`ros2 launch` parents FIRST** (stops the respawn), **then** the nodes:
```bash
pkill -9 -f "ros2 launch"; pkill -9 -f "ros2 run topic_tools"; sleep 3
pkill -9 -f "/opt/ros/jazzy/lib"; pkill -9 -f "[m]icro_ros_agent"; pkill -9 -f rplidar_composition
ros2 daemon stop; sleep 6
```
> ⚠️ Do **not** launch the stack twice. Always clean-kill before relaunching, and run each command **once**.
> ⚠️ When killing over SSH, a broad `pkill` can drop the SSH session (the pattern matches the connection)
> and leave the kill half-done. If processes persist, a Pi **reboot** is the reliable clean slate (it also
> power-cycles the lidar).
> ⚠️ Counting trap: `ps -ef | grep -c "[r]plidar"` over SSH can count its own command line (the pattern is
> in the command). Count real nodes with `ros2 node list`, not such a grep.

---

## 6. One-shot launcher (`~/iboot.sh`, optional)

`~/iboot.sh` does an ordered kill then launches the whole staged stack (bringup → localization →
navigation → goal relay → web_video_server). It is a convenience only; the per-terminal method (§12) is
preferred. If used:
```bash
nohup setsid bash ~/iboot.sh >/dev/null 2>&1 &   # detached so it survives an SSH drop
tail -f /tmp/iboot.log                            # follow until "### DONE"
```
The map it loads is set inside the script (`localization_launch.py map:=...`).

---

## 7. Known bug: the `bringup.launch.py sim:=true|false` selector

On the **real robot**, `bringup.launch.py` does not load the map (`map_server` stays `unconfigured`,
empty `yaml_filename`) whereas `localization_launch.py` launched directly works. The `map` value does
reach localization (verified) — a subtle include bug under the full stack, **unresolved**. Until then,
launch per-terminal (§12). The **simulation** (`sim:=true`) is not affected.

---

## 8. Command reference

**Sourcing (4 workspaces — otherwise `ros2` cannot find the packages):**
```bash
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash      # micro_ros_agent
source ~/camera_ws/install/setup.bash           # camera_ros
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
```

**Costmaps at runtime:**
```bash
ros2 param set /global_costmap/global_costmap inflation_layer.inflation_radius 0.35
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
```

> Saved maps live in `~/maps/` on the Pi. The current working map is `piece_actuelle.yaml`; older ones
> include `coin_ok.yaml`, `coin2.yaml`, `coin1.yaml`.

---

## 8b. Viewing the camera (web_video_server, NOT RViz)

**Symptom:** adding an *Image*/*Camera* display in RViz on `/camera/image_raw` → **"No Image"**, or
`ros2 topic hz /camera/image_raw` (and even `/compressed`) is **silent on the PC** while the camera runs.

**Cause:** the images **do not cross WiFi over DDS**. Raw = 1280×720×3 ≈ 2.7 MB × 24 Hz ≈ **65 MB/s**
(impossible). Compressed (~50 KB) does not cross either: the `image_transport` publisher is **lazy** +
QoS **RELIABLE** → matching with the **remote** subscriber fails over WiFi. (Locally on the Pi everything
works: ~24 Hz raw / ~31 Hz compressed — so the camera + libcamera are fine; the **network transport** is
the problem.) Also, **RViz 2 has no "Transport Hint"**: its Image display reads only **raw** → unusable
over WiFi.

**Fix: `web_video_server`** — runs **on the Pi**, reads the camera **locally** (no DDS/WiFi), and serves
an **MJPEG HTTP** stream only **on demand** (browser closed = no traffic). Install with
`sudo apt install ros-jazzy-web-video-server`; it is also launched by `~/iboot.sh`.

On the **PC**, in a browser:
```
http://172.17.201.29:8080/stream?topic=/camera/image_raw&type=mjpeg
```
(or `http://172.17.201.29:8080` for the topic list).

**Lower the bitrate** (weak WiFi) — directly in the URL, nothing to restart:
```
http://172.17.201.29:8080/stream?topic=/camera/image_raw&type=mjpeg&quality=40
```

**Recommended split:** camera → **browser**; map/lidar/costmap → **RViz**, side by side. RViz is not made
for streaming video over WiFi.

> ⚠️ Do **not** start a second `web_video_server`, an `image_transport republish`, or "wake-up"
> `ros2 topic hz` calls by hand: they duplicate the image path for nothing.

---

## 9. Hardware reminders
- **24 V ≥ 25 V** for the robot to **move** (otherwise weak torque; see [power.md](../hardware/power.md)).
  A low battery also collapses under load → see §14.
- **2D lidar at ~18 cm:** an obstacle < ~18 cm tall is invisible (test with obstacles > 20 cm).
- **`/scan_filtered` in RELIABLE** (QoS fix): otherwise the costmaps stay empty.

---

## 10. Stopping / cancelling a running goal

**2D Goal Pose** starts a `navigate_to_pose` action on `bt_navigator`. To **stop** the robot mid-route,
**cancel that action** (cutting `/cmd_vel` is not enough — the behavior tree keeps issuing commands).

**Cleanest — the cancel command** (robot stops **and navigation stays active**, ready for a new goal). A
ready-made script on the PC:
```bash
bash ~/Documents/openamr/scripts/stop.sh
# (handy alias:  echo "alias stop='bash ~/Documents/openamr/scripts/stop.sh'" >> ~/.bashrc )
```
What it does (empty uuid+stamp = cancel ALL goals):
```bash
ros2 service call /navigate_to_pose/_action/cancel_goal action_msgs/srv/CancelGoal "{}"
# return_code=0 + goals_canceling=[...] => OK, goal cancelled
```

**Nav2 panel in RViz** — **Panels → Add New Panel → `nav2_rviz_plugins` → Navigation 2**:
- Depending on the version there is **no "Cancel" button**; the stop button is **`Pause`** (it pauses
  navigation → you must click again (Resume) to continue — heavier than the command above).
- Do **not** touch `Reset` / `Shutdown`: they drive the lifecycle manager and **shut navigation down**.
- The panel is still useful to **see state**: Navigation/Localization active, Distance remaining, ETA,
  Recoveries.

**Hard emergency stop** (forces velocity to 0 while you keep it running — the BT keeps running behind, so
pair it with the cancel):
```bash
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/Twist "{}"
```

---

## 11. Mapping a new room (SLAM)

Required when the robot is **not in a known map**: otherwise AMCL mislocalizes → phantom walls in the
costmap → `No valid trajectories` → the robot refuses to move although the space is clear.
**The "it does not move / drifts" symptom can ALSO be mechanical** (e.g. a disconnected motor cable, a
flaky left-wheel contact) — confirm that **both wheels turn** before blaming the software.

**Prerequisite (once):** `sudo apt install ros-jazzy-teleop-twist-keyboard` on the Pi.

### Terminal 1 (Pi) — motors + lidar
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_bringup real_bringup.launch.py
```

### Terminal 2 (Pi) — check the lidar, THEN start SLAM
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 topic info /scan          # must show "Publisher count: 1"
```
If `0`: `pkill -9 -f rplidar_composition`, wait 8 s, retry `ros2 topic info /scan` (see §2).
When `/scan` = 1, in the **same** terminal:
```bash
ros2 launch openamrobot_nav2 online_async_launch.py use_sim_time:=false
```

### Terminal 3 (Pi) — drive the robot
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
Keys: `i` forward · `,` back · `j`/`l` turn · `k` stop · `q`/`z` speed. Drive **slowly** across the whole
room, hugging the walls.

### Terminal 4 (PC) — RViz (watch the map build)
```bash
source /opt/ros/jazzy/setup.bash
source ~/Documents/openAMRobot/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
> ⚠️ Never run `rviz2` alone (opens an empty RViz) — always `-d ...openamr_nav.rviz` (Map + LaserScan
> already configured). Fixed Frame = `map`.

### Terminal 5 (Pi) — save the map (when the room is complete)
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 run nav2_map_server map_saver_cli -f ~/maps/piece_actuelle --ros-args -p save_map_timeout:=20.0
```
→ creates `~/maps/piece_actuelle.yaml` + `.pgm`.

> ⚠️ Run **each command once**. Never relaunch `real_bringup` or SLAM a second time without stopping
> everything first — otherwise **two lidar drivers fight over the USB port** → `/scan` drops to 0 (§5).

### Cleaning the black specks in the map (lidar noise / moving objects)
A SLAM map often has **isolated black specks** in the middle (reflections, objects that moved) = phantom
obstacles that make the robot avoid empty space. Automatic script (erases small blobs, keeps walls):
```bash
# on the PC: copy the map from the Pi
scp botshare@172.17.201.29:~/maps/piece_actuelle.pgm  ~/Documents/openamr/maps/
scp botshare@172.17.201.29:~/maps/piece_actuelle.yaml ~/Documents/openamr/maps/
# clean (min_size = pixel threshold; raise it if specks remain, lower it if a small wall disappears)
cd ~/Documents/openamr/maps
python3 ~/Documents/openamr/scripts/clean_map.py piece_actuelle.pgm piece_actuelle_clean.pgm 12
# check the preview piece_actuelle_clean_apercu.png, then put it back + push it
cp piece_actuelle_clean.pgm piece_actuelle.pgm
scp piece_actuelle.pgm botshare@172.17.201.29:~/maps/
```
> The `.yaml` is untouched. If the map is very sparse (lots of grey/unknown, walls not closed), it is
> better to **re-map** covering the whole room than to clean it.

### Editing the map by hand (erase false walls / draw real walls)
The automatic script **keeps** blobs ≥ min_size (it treats them as walls). To remove a false wall (e.g.
"two walls stuck together" in the centre) **and** add real walls, edit the image in GIMP:
```bash
sudo apt install -y gimp
gimp ~/Documents/openamr/maps/piece_actuelle.pgm
```
In GIMP: **Image → Mode → Grayscale**; the **Pencil** tool (N, not the Paintbrush → sharp pixels); zoom
800 %. Foreground colour: **pure white `ffffff`** = erase (free), **pure black `000000`** = wall, grey
`cdcdcd` (~205) = unknown. **File → Export As** → `piece_actuelle.pgm` → **Raw**. Then push it back:
`scp ~/Documents/openamr/maps/piece_actuelle.pgm botshare@172.17.201.29:~/maps/`
> Stay in **pure black/white** (pencil, not brush) — intermediate grey pixels create half-obstacles.

### Reloading an edited map (without restarting everything)
Option A — **at runtime** (recommended, keeps localization):
```bash
ros2 service call /map_server/load_map nav2_msgs/srv/LoadMap "{map_url: '/home/botshare/maps/piece_actuelle.yaml'}"
ros2 service call /global_costmap/clear_entirely_global_costmap nav2_msgs/srv/ClearEntireCostmap "{}"
ros2 service call /local_costmap/clear_entirely_local_costmap  nav2_msgs/srv/ClearEntireCostmap "{}"
```
Option B — relaunch `localization_launch.py map:=...` (Ctrl+C + relaunch) → but AMCL restarts, so **redo
the 2D Pose Estimate**.

---

## 12. Navigating on a saved map (classic ROS terminals)

The supported, per-terminal method (one launch per terminal). Each Pi terminal starts with
`ssh botshare@172.17.201.29` **alone** (type the password, wait for the prompt) and only then the rest.

### Terminal 1 (Pi) — motors + lidar
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_bringup real_bringup.launch.py
```
Check `/scan` = 1 (see §2) before continuing. For a lighter load (weak power), add
`use_camera:=false`.

### Terminal 2 (Pi) — localization on the map
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_nav2 localization_launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_sim_time:=false
```

### Terminal 3 (Pi) — navigation
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_nav2 navigation_launch.py use_sim_time:=false use_scan_filter:=false
```

### Terminal 4 (Pi) — goal relay (without it, 2D Goal Pose does not reach Nav2)
```bash
ssh botshare@172.17.201.29
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-integration/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 run topic_tools relay /goal_pose /goal_pose_nav
```

### PC — RViz
```bash
source /opt/ros/jazzy/setup.bash
source ~/Documents/openAMRobot/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
Then **2D Pose Estimate** (place the robot on the map) → **2D Goal Pose**. Stopping a goal: §10.

> Rules of thumb: each command **once**; **no teleop** during navigation (it floods `/cmd_vel` with zeros
> and overrides Nav2); after a goal, `ros2 topic echo /cmd_vel` should show a **stable** value (not an
> alternating `0.x`/`0.0`, which means a second publisher is fighting Nav2).

---

## 13. Speed too high / the robot overshoots (inertia & in-place rotation)

The robot is heavy → it **slides** and **overshoots** when speed is high or braking is soft. Tuned in
`nav2_params.yaml` (`controller_server` → `FollowPath`); changeable at runtime, then persisted.

| Param | Value (2026-06-25) | Role |
|---|---|---|
| `max_vel_x` | **0.20** | max forward speed (the -2.5 braking absorbs the inertia) |
| `max_speed_xy` | **0.20** | global cap; must follow `max_vel_x` or it runs away |
| `decel_lim_x` | **-2.5** | strong linear braking — slows down much earlier vs inertia |
| `max_vel_theta` | **0.5** | rotation speed (2.0 was far too fast) |
| `decel_lim_theta` | **-2.0** | rotation braking — stops the turn in time |

Runtime: `ros2 param set /controller_server FollowPath.<param> <val>` (e.g. `... FollowPath.max_vel_x 0.20`).
> Knobs: too fast in a straight line → lower `max_vel_x`; overshoots/turns too fast → lower `max_vel_theta`
> (0.5→0.3) and/or strengthen `decel_lim_theta` (-2.0→-2.5).

### The robot will not rotate in place / a side costmap blocks the rotation
A known **DWB** weakness: it struggles to pivot in place to set off in another direction, and if the
footprint touches an obstacle during the rotation, **all** trajectories are rejected → stuck. Fixed in
`FollowPath` (**requires relaunching `navigation_launch`** — it is a plugin change):

| Setting | Effect |
|---|---|
| `plugin: nav2_rotation_shim_controller::RotationShimController` (+ `primary_controller: dwb_core::DWBLocalPlanner`) | **pivots in place toward the path** before handing off to DWB (`angular_dist_threshold: 0.785` = >45° heading error → rotate first) |
| `vtheta_samples: 40` (was 20) | more rotation options sampled → finds a valid turn more often |

> `min_vel_x` was briefly set to `-0.10` (allow reverse to free itself) but it made the robot **back into
> walls** until its rear footprint was in collision and it could no longer move forward — reverted to
> `0.0`. If still stuck near a wall, lower the **local** inflation (0.15→0.10) or trim the footprint a few
> cm for more room to pivot (at the cost of some collision margin).

After editing: **Terminal 3 → Ctrl+C → relaunch** `navigation_launch.py use_sim_time:=false
use_scan_filter:=false`, then `ros2 lifecycle get /controller_server` must show `active`.

---

## 14. The Pi crashes/freezes under load (power brownout)

**Symptom:** while launching the bringup, the terminal **freezes** (Ctrl+C unresponsive), then the Pi
**drops off the network** (`No route to host`); the lidar stops spinning; a **red LED** blinks on the Pi
and/or a motor driver. It looks like a software crash but it is not.

**Cause:** **power**. When motors + lidar (+ camera) start at once, the current spike collapses the 5 V
rail and the Pi browns out. The robot powers the Pi through a **24 V → 5 V DC-DC converter**; a low 24 V
battery and/or an undersized converter cannot hold the Pi 5's peak draw (5 V @ 5 A = 25 W). At boot the Pi
prints *"This power supply is not capable of supplying 5A; power to peripherals will be restricted"*.

**What it is NOT:** verified 2026-06-25 — the Pi's own SoC is fine (cool, fan works: ~56 °C under CPU
load, `vcgencmd get_throttled` = 0x0 at idle). On a proper 5 V/5 A bench supply the Pi holds. So the
crash is the robot's power path, not the Pi or thermals.

**Fixes (hardware):**
1. **Charge the battery; ≥ 25 V at rest.** A low battery collapses under the current spike (also explains
   weak torque and motor-driver fault LEDs — all undervoltage symptoms).
2. **DC-DC converter rated ≥ 5 A** at 5 V (8–10 A for margin). Common 3 A bucks (e.g. LM2596) are too
   small for a Pi 5. Short, thick 5 V wires; a bulk capacitor (1000–4700 µF) on the 5 V rail helps absorb
   spikes.
3. Lift the USB power cap (the DC-DC is a "dumb" 5 V source with no USB-PD negotiation, so the Pi caps USB
   peripherals at 600 mA): add `usb_max_current_enable=1` to `/boot/firmware/config.txt`, then reboot.
   This only **allows** more current — it helps only if the source can actually supply it.
4. **Diagnostic test:** power the Pi from an official 5 V/5 A USB-C supply (no battery). If it then holds
   the bringup, the battery→Pi path is the weak link.

> While power is marginal, **every launch will crash the Pi** — fix the power before further testing.
> A faulty motor/driver (short, stalled motor, miswired cable) also collapses the shared 24 V and crashes
> the Pi: if a driver LED is red or a component is hot, cut power and check the wiring (brown = +, blue = −).
