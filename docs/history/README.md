# History — chronological record of the OpenAMR project

Everything that documents **what was done, and when**. The project started on **2026-06-17**.
Daily session write-ups, dated audits, the fix log, and the cross-cutting technical records live here,
in chronological order. Forward-looking plans are in [`../plans/`](../plans/); timeless reference is in
[`../reference/`](../reference/); rendered HTML deliverables are in [`../reports/`](../reports/).

> Note: the earliest weeks (**2026-06-17 → 2026-06-25**) do not have a dedicated day-by-day journal —
> that work (bring-up, wiring, first firmware, encoder/IMU debugging) is captured across the
> **fix log**, the **audits**, the **diagnostics** record, and the **internship report** below.

## Timeline

| Date | Document | What it covers |
|---|---|---|
| 2026-06-26 | [fix log](2026-06-26-fix-log.md) | Change-tracking log of every fix executed against `FIX-PLAN` (files, what, **why**, how to verify). Spans the late-June work. |
| 2026-06-26 | [launch-architecture audit](2026-06-26-launch-architecture-audit.html) | Audit of the launch architecture (HTML). |
| 2026-07-01 | [project audit](2026-07-01-project-audit.md) | Whole-project audit: state, gaps, decisions. |
| 2026-07-02 | [audit — vision latency & compute](2026-07-02-audit-vision-latency-and-compute.md) | AprilTag docking, vision latency, and the compute platform. |
| 2026-07-03 | [audit — CPU / vision-pipeline](2026-07-03-audit-cpu-pipeline-optimization.md) | CPU / vision-pipeline optimization. |
| 2026-07-03 | [day — docking rework + CPU](2026-07-03-docking-rework-and-cpu.md) | Vision-CPU optimization + camera-frame docking rework. |
| 2026-07-06 | [session — nav, gyro, UI](2026-07-06-nav-gyro-ui.md) | Nav unblocked (0.025 deadlock), gyro bias, cooler, UI working. |
| 2026-07-06 | [day — UI integration, network, thermal](2026-07-06-ui-integration-network-thermal.md) | UI voice-demo integration + network & thermal blockers. |
| 2026-07-07 | [session — docking corrector rewrite](2026-07-07-docking-corrector-rewrite.md) | NEAR corrector rewrite, the gate saga, and the battery lesson. |
| 2026-07-08 | [session — release prep](2026-07-08-release-prep-diagrams-audits.md) | PR consolidation, licences, diagrams, cross-repo audits. |
| 2026-07-08 | [session (soir) — test terrain + vitesses Nav2](2026-07-08-nav-speed-tuning-field-test.md) | Faux coupable LIDAR fantôme (pas le tuning), plancher basse vitesse, et la leçon DWB : les vitesses max ne se changent pas à chaud → relance. |
| 2026-07-09 | [session — docking : ligne toujours en odom](2026-07-09-docking-unified-odom-line.md) | Fin de l'oscillation d'approche : la ligne du dock vit désormais en `odom` (refine lag-correct), plus de bascule base_link↔odom. + undock robuste, arrêt lidar, dock_pose hors carte, coup de rein pour la marche. |
| 2026-07-10 | [session — docking final, CPU/caméra, audit doc, sim, prépa PR](2026-07-10-docking-final-cpu-docs-audit-sim.md) | Derniers réglages docking (collision_monitor pause, arrêt lidar 0.13, recherche non-figée, `log_splitter`) ; **le vrai bloqueur = mauvais profil** (gate Python → composé par défaut) + Pi5 saturé ; **audit multi-agents de 59 docs → 45 corrections** ; sim relancé (fragmentation branches, offload NVIDIA PRIME) ; 4 branches poussées + descriptions PR + texte Alex. |

## Cross-cutting records (not a single day)

| Document | What it is |
|---|---|
| [diagnostics.md](diagnostics.md) | The running "why" — diagnostics & decisions across the whole build. |
| [encoder-calibration.md](encoder-calibration.md) | Encoder velocity-ripple investigation + the motor velocity-control chain. |
| [rapport-stage-technique.md](rapport-stage-technique.md) | Technical internship report — the whole AMR project, narrated. |

---

*New day? Add `YYYY-MM-DD-slug.md` here and a row in the timeline above.*
