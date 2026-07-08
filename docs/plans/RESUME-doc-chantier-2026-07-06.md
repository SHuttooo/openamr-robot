# Reprise — chantier documentation platform (SW/FW/HW) + PR

Point d'arrêt 2026-07-06, **mis à jour 2026-07-07**. Ce fichier = état + ce qui reste à faire.
**Auto-suffisant** : une session fraîche (Sonnet) doit pouvoir reprendre sans autre contexte.

## 🧭 CONTEXTE POUR UNE SESSION FRAÎCHE (repos, remotes, méthode)
- **Repos** (tous sur le fork perso `SHuttooo`, l'utilisateur ouvre les PR vers upstream `openAMRobot` lui-même — Claude n'a PAS accès upstream) :
  - `~/Documents/openamr` = repo NOTES/DOC/MÉMOIRE perso (`origin` = SHuttooo/openamr-robot, branche `master`). Sessions journalières + `claude-memory/`.
  - `~/Documents/openAMRobot/openamr-platform-sw` = code SW (Nav2/docking/perception/bringup). `origin`/`upstream`.
  - `~/Documents/openAMRobot/openamr-platform-fw` = firmware Teensy.
  - `~/Documents/openAMRobot/openamr-platform-hw` = hardware (électrique, méca, BOM). **Schéma câblage = `electrical/wiring/wiring-pinout.md`** (texte + carte ASCII, vérifié 19-06 ; PAS de schéma graphique).
  - `~/Documents/openAMRobot/openamrobot-ui` = UI (React+rosbridge). **⚠️ NE PAS TOUCHER / NE PAS PUSHER** (consigne utilisateur).
- **Règles** : commits **sans mention Claude** ([[amr-commit-no-claude]]) ; **PAS de force-push** (fast-forward only) ; commandes toujours complètes/copiables.
- **Méthode qui marche** (voir bas de fichier) : rédaction par agents parallèles (fichiers disjoints) → **audit adversarial** (chaque valeur vérifiée contre le code source) → fixes → commit. Ne PAS sauter l'audit (a trouvé de vrais faits faux).

## 📤 ÉTAT PUSH AU 2026-07-07 (ce qui est DÉJÀ sur le fork)
- ✅ **FW** `feature/teensy-4-0-linorobot2-overlay` — poussé.
- ✅ **HW** `feature/hardware-audit` — poussé.
- ✅ **NOTES** `openamr` master — poussé.
- ✅ **SW** poussées : `feature/docking-apriltag-gate`, `feature/vision-composition`, `feature/diagnostics`, `feature/real-robot-docs` (docs SW), `fix/docking-near-servo-af` (docking du 07-07, backup).
- ⚠️ **SW REJETÉES (non-fast-forward, à réconcilier — JAMAIS en force)** : le fork distant a des commits que le local n'a pas :
  - `feature/perception-scan-body-filter` : local +2 / **remote +1**
  - `feature/nav2-real-tuning` : local +3 / **remote +4** (le plus divergent)
  - `feature/real-bringup` : local +2 / **remote +2**
  → Reprise : `git fetch`, inspecter ce que le remote a en plus (`git log local..origin/<b>`), décider merge/rebase à la main. Ne pas écraser.

---

## ✅ FAIT (committé, propre)

### FW — repo `openamr-platform-fw`, branche `feature/teensy-4-0-linorobot2-overlay` (5 commits)
- Doc firmware complète créée de zéro : `docs/architecture/` (control-loop, debug-telemetry, encoder-calibration), `docs/bringup/`, `docs/flashing/`, `docs/safety/`, `docs/troubleshooting/`.
- Code overlay **rafraîchi** au firmware déployé 2026-06-29 (K_P 2.0/0.1/0.1, MOTOR2_GAIN 1.000, feedforward, dither, table enc_cal, /debug/tune, openloop borné, back-calc anti-windup).
- Fixes d'audit : topic IMU `/imu/data_raw`+`/imu/mag`, anti-windup=back-calculation, bloc env agent, commande `align_enc_cal.py --arm 250`, exemple `/debug/tune`, reframe encodeur (table hot-loaded + align par boot, PAS filtre vitesse).

### HW — repo `openamr-platform-hw`, branche `feature/hardware-audit` (4 commits)
- Findings intégrés : thermique Pi5 (pas de cooler, 83°C, throttle), brownout alim, fault-codes LED ZBLD (nouveau), profil erreur encodeur, planchers vitesse, couleurs câbles.
- Fixes d'audit : IMU+encodeurs en **3.3V** (pas 5V), reframe encodeur (align-table), DIP SW4/SW5 ON/ON, RAM 8Go, fault-code désambiguïsé, **dimensions méca** (rayon 0.046533 m, voie 0.4075 m), résolution caméra, FR→EN, liens.
- ⚠️ Limite : table complète codes ZBLD (15,17,18,20-26,28) nécessite le manuel `ZBLD.C20.pdf`.

### SW code — repo `openamr-platform-sw`, 5 commits du jour répartis sur branches propres (LOCAL, pas poussé)
- `feature/docking-apriltag-gate` (+normale frame-robot/PWM/floors, +throttle gate) — 3 commits
- `feature/perception-scan-body-filter` (+tuning scan, +cap caméra 15fps) — 3 commits
- `feature/nav2-real-tuning` (+speedup planner, +fix commentaire roue) — 3 commits
- `feature/real-bringup` (+goal relay) — 5 commits
- `feature/vision-composition` (**NOUVELLE** — 3 launches composés) — 1 commit
- `feature/diagnostics` (inchangée) — 1 commit
- `local/test-all` = intégration (14 commits, PAS une PR)

### SW docs — branche `feature/real-robot-docs` (commit 30ad811, base = local/test-all)
- `docs/navigation/` (7+README), `docs/safety/` (3+README), `docs/real_robot/` (8+README) = **21 fichiers, ~19k mots**.
- Écrites depuis RUNBOOK/audits/mémoire, **auditées** contre le vrai `nav2_params.yaml`/launches, **fixées** (pipeline composé = always-on, liens réparés, commandes complètes, footprint 0.42, wording roue neutralisé).
- ⚠️ Le worktree existe encore : `scratchpad/wt/sw-docs` (branche sauvegardée en git — le worktree peut être supprimé).

### Autres
- `docs/PR-PLAN-2026-07-06.md` = les 8 PR (titres + descriptions + ordre merge + commandes push).
- Repo de travail : mémoire corrigée (gains PID, openloop, fix encodeur), `piece_actuelle.yaml`→`maps/`, `cyclonedds_pc.xml` supprimé.

---

## ⏳ À FAIRE (reprise)

1. **Neutraliser le commentaire roue dans `nav2_params.yaml`** (branche `feature/nav2-real-tuning`, ligne 90) : j'avais mis "left-wheel (loose-contact) fault". Réalité (confirmée par l'utilisateur) = **plus de panne d'une roue précise** ; parfois un **câble se débranche** (rebrancher) ou une **roue cale au démarrage** (relancement général). → mettre neutre : « when a wheel momentarily stalls (a loose motor cable, or start-up stiction) ». Amender/nouveau commit.

2. **Indexer les nouvelles docs SW** : le README racine + `docs/` n'ont PAS encore de liens vers `navigation/`, `safety/`, `real_robot/`. Ajouter les liens (barre de nav + index).

3. **Base propre pour la PR docs SW** : `feature/real-robot-docs` est basée sur `local/test-all` (pas une base PR propre). Pour une PR vers `upstream/main` : cherry-pick le commit docs (30ad811) sur une branche neuve off `upstream/main` (docs-only → cherry-pick propre car additif). L'ajouter au PR-PLAN comme PR #9.

4. **Mémoire** : `amr-left-wheel-faux-contact.md` + `MEMORY.md` → marquer le faux-contact **RÉSOLU** ; réalité actuelle = câble occasionnel (rebrancher) + cale au démarrage (relancer). *(fait en partie ce jour — vérifier.)*

5. **Pousser les branches** — ✅ **FAIT en grande partie le 07-07** (voir "ÉTAT PUSH" en haut). Reste : réconcilier les 3 branches SW rejetées (perception-scan-body-filter, nav2-real-tuning, real-bringup) — le remote a des commits en plus, à merger/rebaser à la main, PAS en force.

6. **(optionnel)** READMEs des packages SW touchés (nav2/bringup/docking/perception) ; slots `docs/simulation/` + `docs/docking/` racine (vides, basse priorité — docking a déjà sa série package).

7. **Nettoyer le worktree** : `git worktree remove` sur `scratchpad/wt/sw-docs`.

8. **(07-07) Branche docking `fix/docking-near-servo-af`** (poussée, backup) — contient de VRAIS fixes correcteur (dérivée dt, compensation profondeur, report orientation odométrie, gel normale) VALIDÉS "c'est aligné" (état commit `31fe8b1`), MAIS aussi du bruit annulé (2 tentatives gate cassées, réglages scan). L'**autofocus continu** (`camera.launch.py`, `AfMode:2`) est un bon fix perception à isoler dans une PR propre. À froid : extraire les bons commits correcteur + l'autofocus en branche(s) propre(s) pour PR. Chantier gate 4Hz encore ouvert (cf [[amr-docking-gate-4hz-bottleneck]]). Détail : `docs/history/2026-07-07-docking-corrector-rewrite.md`.

---

## Méthode qui a marché (à réutiliser)
Rédaction par agents parallèles (fichiers disjoints) → **audit adversarial** par agents (vérif chaque valeur contre le code source) → application des fixes → relecture → commit. Les audits ont trouvé de **vrais faits faux** (topic IMU, anti-windup, pipeline composé "always-on", 5V vs 3.3V, roue) — ne pas sauter l'étape audit.
