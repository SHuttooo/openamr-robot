# Day summary — 2026-07-06 (Mon): UI voice demo integration + network & thermal blockers

Monday of the demo week. The plan was UI-first (Alex needs a voice→blocks→robot demo
video for LinkedIn, Tuesday). We integrated the voice feature and validated the pipeline,
but the day was dominated by **two infrastructure blockers** that surfaced on the real
robot: the **Wi-Fi (Motionlab-Guest)** collapsing under the camera stream, and the **Pi 5
overheating (no cooler)** and thermally throttling navigation. Both are now understood and
documented; the thermal one is a hardware wait (cooler ordered from Alex).

Robot: Raspberry Pi 5 (8 GB), Teensy (micro-ROS), RPLIDAR A1, IMX708 via `camera_ros`,
ROS 2 Jazzy, Nav2, CycloneDDS domain 0. Reached at `botshare.local` (DHCP IP `172.17.17.64`).
UI repo: `openamrobot-ui` (React + rosbridge, Docker), branch `feat/real-robot-integration`.

---

## 1. UI voice-demo integration (the actual goal)

- **Merged the voice feature** from `origin/main` into `feat/real-robot-integration`
  (Alex's `voiceCapture.js` / `voicePlan.js` + `flask_app.py` `/api/voice-plan`). Clean
  merge, **no conflicts**.
- **IP update**: `.env` / `.env.example` `REACT_APP_ROSBRIDGE_IP` → `172.17.17.64`.
- **Added "Station 4"** as a default named location in both places (frontend
  `blockDefinitions.js` `DEFAULT_OPEN_AMR_LOCATIONS` + backend `flask_app.py`
  `DEFAULT_BLOCK_LOCATIONS`). **Coords are placeholder** (`x:2, y:1, yaw:1.57`) — must be
  recalibrated on the real map before a real drive.
- **Claude key**: created `ros2/src/openamr_ui_package/.env` with a valid `ANTHROPIC_API_KEY`
  (user did it directly; verified gitignored via `.gitignore:22`; never committed).
- **Voice pipeline validated end-to-end** by POSTing the demo phrase directly to
  `/api/voice-plan` — the backend + Claude key produced the correct **5-step plan**:
  `navigate_named(Station 4) → wait_nav_complete → wait(10s) → navigate_named(Home) →
  wait_nav_complete`. So backend + key + block generation all work. Note: *"then return"*
  is interpreted as **Home**, not Station 4.

### Browser / speech-recognition reality
The Web Speech API is browser-side and **not local** — it ships audio to Google's servers.
Learned the hard way:
- **Firefox**: `webkitSpeechRecognition` absent → "not supported".
- **Chromium** (snap): the object exists, but the open-source build **has no Google Speech
  API key** → every attempt fails with **`network`** error. → need **real Google Chrome**.
- **Google Chrome + en-US recognizer**: recognition works, but the **French wake word
  "Monsieur"** is unreliable — en-US mis-transcribes it, so the strict `\bmonsieur\b` gate
  rejected the command ("Didn't hear the wake word").
- I built a **robust wake-word fix** (accept en-US variants + fall back to the whole
  transcript + show the live transcript) — it worked, but the user asked to **revert to the
  original**, so `voiceCapture.js` / `BlocksPage.jsx` are back **identical to `origin/main`**
  (confirmed by empty `git diff`). Open question for the demo: how to reliably say/handle
  "Monsieur" with the en-US recognizer.

---

## 2. Network blocker — Wi-Fi Guest + the camera saturates the link

The robot is on **`Motionlab-Guest`**, an isolated + unstable guest network. Several
"robot/lidar is broken" scares today were actually **the Wi-Fi**:

- A Wi-Fi meltdown broke **mDNS** (`botshare.local` didn't resolve) and **DDS discovery**
  (PC `ros2 topic` timeouts, 100 % ping loss) — but the **lidar was fine the whole time**
  (`/scan` ~6.8 Hz, checked directly on the Pi). **Reflex: check the network before blaming
  the software** (`getent hosts botshare.local` + `ping`).
- **The camera is what saturates the link.** The IMX708 publishes 1280×720 **RELIABLE**.
  On a healthy link (earlier sessions) there's ~0 % loss so it's fine; on the **degraded
  guest Wi-Fi** any packet loss triggers a **DDS reliable-retransmit storm** on the big
  image frames → saturates the airtime → ping/SSH/DDS all collapse. **It's not that the
  camera changed — the network degraded.** Trigger today: clicking **"Start Camera"** in the
  UI (which starts `web_video_server` pulling the stream over Wi-Fi).
- **The UI Docker on the PC also saturates the link**, even without the camera: its
  rosbridge + relays subscribe *from the PC* to big RELIABLE topics (`/global_costmap/costmap`,
  `/map`, `/tf`, `/scan`) → same retransmit storm → **Nav2 goals stopped reaching the Pi**
  (no path in RViz, `/cmd_vel_nav` silent). `docker compose down` → **navigation works again**
  immediately.
- **Design intent**: the UI is meant to run **on the robot** (README Option B = "robot
  computers"): Flask + rosbridge local to the Pi, all DDS local, only the **browser** crosses
  Wi-Fi (one lightweight websocket). Running it on the PC (Option A, "quick demos") is what
  conflicts with nav on this network. Pi currently has **no UI installed** (no repo, no
  docker, no colcon build) → UI-on-Pi = from-scratch deploy (later this week or Ethernet).
- **DDS domain/RMW gotcha**: `docker compose up` **without** the `RMW_IMPLEMENTATION=…
  ROS_DOMAIN_ID=0` prefix → the container inherited the shell's **FastDDS / domain 42** and
  saw **zero** robot topics ("Map not received", "Localization pose missing"). Fixed by
  launching with the prefix → Cyclone / domain 0. The prefix is **mandatory**.

---

## 3. Thermal blocker — the Pi overheats and throttles nav (THE blocker)

- **Hardware**: Raspberry Pi 5 Model B Rev 1.1, 4× Cortex-A76 up to 2.4 GHz, **8 GB RAM**
  (6.4 GB free — RAM is *not* the issue).
- **No fan / active cooler.** Measured live under the full stack: **83.4 °C**,
  `throttled=0x80008` → **soft thermal limit actively engaged** (bit 3) + has-occurred (bit
  19). No under-voltage (power is fine). At 83 °C the Pi 5 caps its clock (~2.1 vs 2.4 GHz)
  to avoid the 85 °C hard limit → **navigation planning/costmaps slow down**. It's not a
  software bug; the CPU is being clock-limited by heat.
- **CPU also oversubscribed** by work nav doesn't need: `dock_trigger.py` **36 %** +
  `camera_node` **19 %** + `apriltag_gate.py` **19 %** = ~74 % of a core for docking/vision,
  starving the planner/controller → **load 5.2 on 4 cores**. (Consistent with the 07-03
  finding that `dock_trigger.py` burns ~30 % even while idle.)
- **Mitigation**: run the **light bring-up** — `use_camera:=false use_docking:=false` — which
  kills those three processes (~74 % freed), drops load well under 4, and lets the Pi cool.
  This is the right default on this network anyway (no camera flood).
- **Sent Alex a message** asking for the **official Raspberry Pi 5 Active Cooler** (~€5–10
  clip-on; keeps it ~50–60 °C under load, removes the throttling).

---

## 4. Navigation debugging

- Robot **localizes fine** (valid `/amcl_pose`), **costmaps populate** (55k cells).
- "Nav doesn't move" was **not** stiction or collision_monitor: `/cmd_vel_nav` and `/cmd_vel`
  were **silent** → **no goal was being executed**. Root cause = the **UI-on-PC Wi-Fi
  saturation** above blocking `/goal_pose` from reaching the Pi. Goal routing confirmed
  correct: RViz "2D Goal Pose" → `/goal_pose` → `goal_pose_relay` (topic_tools) →
  `/goal_pose_nav` → bt_navigator (nav-only mode, `use_docking:=false`).
- Still-open nav item from earlier: the controller emits **sub-stiction yaw** (`/cmd_vel`
  `z≈0.025 rad/s`, below the 0.15 rad/s floor) on fine corrections → robot doesn't turn,
  goal eventually aborts. Fix pending: floor the DWB angular output in `nav2_params.yaml`.
- **RViz config path fix**: the working config is `~/Documents/openamr/scripts/openamr_nav.rviz`
  (I had given the wrong path once → RViz opened with no Map panel).

---

## 5. Encoder calibration — clarified how verification works

- Question: does `encoder_calib.py` measure **with** the calibration table applied?
  **Yes.** The firmware applies the ripple table *before* publishing the debug rpm:
  `firmware.ino:590` `calib_rpm(…, LEFT_CAL)` → `:653` `debug_cur_rpm1 = current_rpm1` →
  `:706` `debug_left_msg.y = debug_cur_rpm1`. So `/debug/left|right.y` is the **corrected**
  rpm → `encoder_calib.py` (which bins `m.y` by `m.z` counts) measures the **residual** once
  a table is loaded (passthrough 1.0 until then).
- Measured error profile (3 speeds 120/180/250 **overlap** → speed-independent geometric
  error): **LEFT ±11 %** (0.91–1.13), **RIGHT ±6 %** (0.94–1.06). Left is the known
  off-centre encoder.
- **"Is it sufficient?" → Yes for nav.** The profile is normalized to mean = 1.000 over a
  full revolution → the error **averages out per revolution**, so odometry/position doesn't
  drift; it only causes **intra-revolution velocity ripple** (the low-speed left "oscillation").
  It won't stop the Station-4 nav. The accepted long-term fix remains a **velocity filter**,
  not the runtime table (incremental encoder loses table phase at each Teensy power-cycle).

---

## State at end of day

**Ready / working:**
- Voice → blocks pipeline: backend + Claude key + 5-step plan generation validated.
- UI Docker builds and runs (on Cyclone/domain 0 with the env prefix); "Station 4" present.
- Robot bring-up, localization, nav all functional in **light mode** (no camera/docking).
- Lidar, encoders, motors all confirmed healthy.

**Blockers / open:**
1. **No Pi cooler** → thermal throttling → slow nav. Waiting on Alex for the Active Cooler.
   **This is why we're pausing on-robot work and switching to documentation.**
2. **Wi-Fi Guest** can't carry camera stream or UI-on-PC + nav together. Real fix = UI on the
   Pi, or Ethernet.
3. Voice wake-word "Monsieur" unreliable on the en-US recognizer (robust fix built then
   reverted per request).
4. Sub-stiction nav yaw floor not yet applied in `nav2_params.yaml`.
5. "Station 4" coords are placeholder — recalibrate on the real map.

**Files touched today (UI repo `openamrobot-ui`, branch `feat/real-robot-integration`):**
- `.env`, `.env.example` — IP → 172.17.17.64
- `web/src/features/blocks/blockDefinitions.js` — added "Station 4"
- `ros2/src/openamr_ui_package/openamr_ui_package/flask_app.py` — added "Station 4"
- (merge of `origin/main` voice feature)
- `voiceCapture.js` / `BlocksPage.jsx` — robust wake-word fix **made then reverted** (now == origin/main)

Related: `claude-memory/amr-wifi-guest-flaky.md` (network + camera + UI findings), the plan
`docs/PLAN-week-2026-07-06-EN.md`, prior audit `docs/DAY-2026-07-03-docking-rework-and-cpu.md`.
