---
name: amr-platform-sw-prs
description: "État GitHub openamr-platform-sw au 2026-06-30 : 5 feature-branches propres poussées sur le fork SHuttooo = 5 PR vers openAMRobot:main. Gate apriltag + nav tuning + WIP redistribué par sous-système. local/test-all = branche d'intégration (pas une PR). Chevauchement perception ⊂ real-bringup à clarifier."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Repo `openamr-platform-sw`** (`~/Documents/openAMRobot/openamr-platform-sw`). Remotes : `origin`=SHuttooo
(fork, on push ici), `upstream`=openAMRobot (cible des PR), `raj`=rajindulkar22 (reviewer).

## 5 feature-branches propres sur origin (SHuttooo) = 5 PR potentielles vers upstream/main
1. **feature/docking-apriltag-gate** (1 commit, NEUVE) — le gate apriltag on-demand [[amr-apriltag-on-demand-gate]].
   PR à créer : https://github.com/SHuttooo/openamr-platform-sw/pull/new/feature/docking-apriltag-gate
2. **feature/perception-scan-body-filter** (2) — camera.launch paramétré + scan filter.
3. **feature/nav2-real-tuning** (3) — nav2_params testé + velocity_smoother/collision_monitor dans navigation_launch.
4. **feature/real-bringup** (5) — bringup sim/real unifié + drivers + goal_relay.
5. **feature/diagnostics** (1) — scripts diagnostic (pas touchée cette session).

⚠️ **Chevauchement** : `feature/real-bringup` contient aussi le commit perception → recoupe `feature/perception`.
À décider : perception en PR séparée mergée d'abord, puis rebase real-bringup par-dessus.

## Méthode utilisée (à réutiliser)
Working tree `local/test-all` sale (WIP non commité) → j'ai committé **en worktrees isolés** (un par
feature-branch, base = `origin/<branche>`), push fast-forward (jamais de force). `local/test-all` = branche
d'**intégration/test** (merge des features), **PAS une PR**. Le WIP y est encore présent (copié, pas déplacé)
→ peut être jeté (`git checkout -- . && git clean -fd`) car déjà sur les branches.

## À nettoyer côté repo
`matthieu/bundle-docking` = vide (== upstream) à supprimer ; `matthieu/contribution` = grosse branche
fourre-tout (10 commits) à archiver. Commits sans Claude [[amr-commit-no-claude]], sign-off DCO (`-s`).
