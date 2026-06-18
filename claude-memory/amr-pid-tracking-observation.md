---
name: amr-pid-tracking-observation
description: "2026-06-18 — roue GAUCHE en panne matérielle (PWM max, rpm 0) ; PID hors de cause"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

## PID RE-TUNÉ 2026-06-18 (step-response) — K_I était trop bas
Nouveaux gains flashés : **K_P 0.6 / K_I 0.35 / K_D 0.15** (avant 0.3/0.15/0.25). Résultat : erreur
statique **-26% → ±2%** (atteint la consigne), montée **2,9 s → ~1 s**. La cause = **K_I=0.15 trop bas**.
Overshoot droite reste marqué (dynamique driver droit). Méthode : échelon /cmd_vel 0.25 m/s + record
/debug/left|right (50 Hz). Tester à ≥0.25 m/s (à 0.15 la mesure rpm est quantifiée ~2.9 rpm ≈ 20%).

⚠️ **GROS gotcha** : `pio run -e teensy40` utilise **`config/lino_base_config.h`**, PAS
`custom/dev_config.h` (le flag USE_DEV_CONFIG n'est que sur l'env `[env:dev]`). → éditer
**lino_base_config.h**. Aussi : les drivers ZBLD régulent en interne (VAR + rampe ACC/DEC) ; le stiction
(~0.4 s de temps mort) demanderait un **feedforward** firmware pour un départ droit. Repo overlay
firmware mis à jour. (Pas besoin d'attendre la "vraie source auteur" — on a tuné nous-mêmes.)

## CONCLUSION (test step-response 2026-06-18) : roue GAUCHE en panne MATÉRIELLE — PID hors de cause
Test échelon 0,15 m/s sur le sol, capture `/debug/pwm` + `/debug/left|right` :
- **GAUCHE : PWM monte jusqu'à ~316 (saturé) mais rpm mesuré = 0** tout du long → le firmware commande
  bien le moteur (intégrale qui sature faute de réponse), **mais la roue ne tourne pas** = panne
  moteur/driver/câblage/alim côté GAUCHE. **Le PID fait son job, il n'est PAS en cause.**
- DROITE : PWM ~244, rpm ~9-15 (tourne ; un peu molle, ~1,5 s de temps mort, erreur statique ~18 %).
- Explique le « n'avance pas droit » (pivote sur la gauche bloquée) et la **dérive SLAM**.
- Probable **faux contact** (intermittent avant, permanent maintenant), surtout depuis le passage
  **batteries**. Vérifier 24 V coupé : alim driver gauche (marron=+/bleu=−, [[amr-wiring-dc-colors]]),
  COM/masse, connecteurs moteur U/V/W + PWM/IN_A/IN_B, LED fault du driver gauche.
- ⚠️ Impossible d'évaluer/tuner le PID tant que la roue gauche ne tourne pas.

---
Observation initiale (avant le test) : **la vitesse réelle n'atteint pas précisément la `/cmd_vel`
demandée**. Hypothèses d'alors (le test ci-dessus a tranché : c'était la roue gauche morte) :

**À garder en tête (2 causes possibles, ne pas conclure trop vite) :**
1. **PID firmware non optimal** : les gains (K_P 0.3 / K_I 0.4 / K_D 0.25) sont **RECONSTRUITS**, pas
   ceux de l'auteur (cf [[amr-firmware-debug-flashed]]), et pid.cpp n'a pas d'anti-windup propre.
2. **Tension batteries** : depuis le passage sur batteries, si la tension < 24 V, la **vitesse max des
   roues chute** → à cmd_vel élevée les roues **plafonnent** (limite physique, pas le PID). Vérifier la
   tension. La roue droite est aussi historiquement un peu plus faible (cf [[amr-runaway-rootcause]]).

**Reco : NE PAS tuner le PID à l'aveugle.** La **vraie source firmware** (tuning de l'auteur) est
attendue **~2026-06-19** (demain) — comparer avec, plutôt que deviner. En attendant : vitesses modérées.
