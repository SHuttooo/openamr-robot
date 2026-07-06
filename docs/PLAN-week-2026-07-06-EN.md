# Plan — week of 2026-07-06 (Mon → Fri)

For Raj (UI testing + docking testing) and Matthieu. Five days, tight. UI on Monday (demo is
Tue). **Docs and PRs are protected, not deferred**: all PRs open by Wed, Thursday is a dedicated
documentation day.

## Starting state
- ✅ **Vision/CPU optimized** — composed camera+apriltag pipeline (intra-process), detector 15 Hz,
  Pi ~45 % CPU; docking has succeeded several times (`DAY-2026-07-03`).
- ✅ **Robot-frame docking** (dock normal relative to the tag, not the wobbly map): deployed;
  to test/tune + resolve a constant +4.2° offset.
- ✅ **Pi recovered** — new HW + old SSD → reach it at **`botshare.local`** (DHCP IP now
  `172.17.17.64`; old `172.17.201.29` dead).
- ✅ **Right wheel working** (the earlier faux-contact is fine now) — no hardware fix needed; just
  watch for a recurrence during testing.

---

## MONDAY — UI (demo prep)
- [ ] **Point the UI at the new Pi** (`.env` + `web/src/shared/constants/index.js` → `172.17.17.64`).
- [ ] **Demo branch**: merge the voice feature (`origin/main`) into `feat/real-robot-integration`.
- [ ] **Claude key** in `ros2/src/openamr_ui_package/.env`; **create "Station 4"** location.
- [ ] **Test voice→blocks** in Chrome (backend + mic, no robot).
- [ ] **Commit today's docking code** to clean branches (prep for Tue/Wed PRs).
- **Done: voice→blocks works on screen, robot spins cleanly.**

## TUESDAY — Demo + finalize the docking
- [ ] **Full bring-up** on `botshare.local`; recalibrate "Station 4" on the real map.
- [ ] **Record + send the demo** to Alex (voice → blocks → robot heads to Station 4).
- [ ] **Finalize the docking** (robot-frame approach): run it, watch `norm=`, alignment, oscillation.
- **Done: demo sent, docking working.**

## WEDNESDAY — Docking reliability + PRs
- [ ] **Resolve the +4.2°** (perpendicular robot → read `norm=` → ~0 control issue / ~+4° camera bias
      → `normal_yaw_offset`); **5–10 dockings** for repeatability; freeze perpendicular heading in
      NEAR if still off-axis.
- [ ] **Open the PRs** for the docking / vision / nav work.
- **Done: ≥ 8/10 dockings < 2° alignment; PRs open.**

## THURSDAY — Documentation day + real-robot UI
- [ ] **Documentation (dedicated)**: consolidate day summaries + CPU audits, update the runbook,
      the touched packages' READMEs, and the UI real-robot README; make sure each PR has a clear
      description. This is the day docs actually get finished.
- [ ] **Real-robot UI testing**: map / camera / joystick via rosbridge on `botshare.local`
      (watch the Cyclone/domain-0 DDS gotcha).
- **Done: docs consolidated & pushed; UI shows the robot's map + camera.**

## FRIDAY — Finalize PRs + close #13 + wrap-up
- [ ] **Address review** + merge order (perception → real-bringup → rest).
- [ ] **End-to-end "navigate to Station 4"** block from the UI on the real robot.
- [ ] **Close GitHub discussion #13**: comment with repo/directory links, mark done, list
      limitations/issues (faux-contact, +4.2°, nav in tight spaces) + future plans.
- [ ] **Wrap-up status** to Alex/Raj.
- **Done: PRs merging, #13 closed, status sent.**

---

## Through-line
- **PRs Tue + Wed** (all 8 open by Wed); **Thursday = dedicated docs**. Neither slips to Friday.
- **Always `botshare.local`** (DHCP IP changes); complete copy-paste commands; commits with no
  Claude attribution + DCO sign-off.
- **Risks**: the faux-contact recurring (watch `/debug/right` if the robot misbehaves); DHCP
  changing the IP again; the +4.2° being a camera-mount bias; the demo depending on Chrome + mic
  + a valid Claude key.

## External dependencies
- A valid **`ANTHROPIC_API_KEY`** for the voice demo — confirm we have one.
- **Upstream write access** to open the PRs.
