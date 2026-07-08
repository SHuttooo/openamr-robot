# PLAN — fix everything (tracking)

> Derived from the adversarial audit 2026-06-26 (3 agents + checks). Check off as you go.
> Critical problems numbered 🔴1…🔴10 (see conversation / docs/ARCHITECTURE.md §6).

## PHASE A — Software fixes (without robot, validated in sim)
- [x] **A1** Reintegrate `velocity_smoother` + `collision_monitor` into `navigation_launch.py` — 🔴1 ✅ 2026-06-26
- [x] **A2** Timeouts on `dock_trigger.py` action waits — 🔴2 ✅ 2026-06-26
- [x] **A3** Align code↔YAML dock pose defaults — 🔴3 ✅ 2026-06-26
- [x] **A4** Fix the obstacle cone direction (lidar yaw=π) — 🔴4 ✅ 2026-06-26
- [x] **A5** Parameterizable AMCL initial pose (not pinned to 0,0 in real) — 🔴5 ✅ 2026-06-26
- [x] **A6** Anti-double-transmitter guard (relay + dock_trigger) — ✅ 2026-06-26 (validated: detects 2 dock_triggers)
- [x] **A7** Clean up the `nav2_params_map_*` tempfile — minor ✅ 2026-06-26

## PHASE B — Config to measure (physical need)
- [ ] **B1** Measure the tag's black square → `tags_36h11.yaml:size` — 🔴6
- [ ] **B2** Measure the real dock pose → `dock_trigger.yaml` — 🔴C
- [ ] **B3** Verify the footprint (0.78×0.58) → `nav2_params.yaml` — 🔴8

## PHASE C — Consolidation / end of migration
- [ ] **C1** Resync the firmware mirror (`openamr/firmware/` ← Pi) — needs the Pi (off, charging)
- [x] **C2** Mark `odom_tf_relay.py` legacy + obsolete scripts — ✅ 2026-06-26
- [x] **C3** Harden `bringall.sh` (anchored pkill, `[ -f ]` guards) — ✅ 2026-06-26
- [ ] **C4** Migration steps 3-4 (repoint bringall → bringup, remove old) — AFTER robot validation

## PHASE D — Hardware / safety
- [ ] **D1** Charge battery ≥25 V — 🔴10 (BLOCKER, in progress)
- [ ] **D2** Re-solder left wheel cable — 🔴7 (BLOCKER #1)
- [ ] **D3** Fix Pi 5 brownout — 🔴9 (BLOCKER)
- [ ] **D4** Fuse + emergency stop + 24 V battery cutoff — safety
- [ ] **D5** Enable firmware hardware watchdog (`WDT_TIMEOUT`)

## PHASE E — Robot validation (when D1-D3 OK)
- [ ] **E1** Power-cycle 24 V + wheel test (`/debug/openloop x:100`)
- [ ] **E2** `bringup.launch.py sim:=false` → filled costmaps, collision_monitor active (A1), cmd_vel vs odom
- [ ] **E3** Tune PID if asymmetry
- [ ] **E4** Real docking (after B1-B3)

## Order
NOW: A1→A2→A3→A4→A5, then C1,C2,A6,A7 (validated in sim) → commit.
BATTERY+CABLE OK: E1→E2.
DOCK+TAG OK: B1→B2→B3→E4.
INTEGRATION PROVEN: C3→C4.
