---
name: amr-pid-tuning
description: "Réglage PID moteurs — gains trouvés, interface pid_tuner, et le cycle limite de la roue gauche"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Réglage PID des moteurs (Teensy, via `scripts/pid_tuner.py` sur le PC + agent micro-ROS sur le Pi).

## CONFIG FINALE FIGÉE (2026-06-29) — boucle de vitesse FF + PID + dither
**Chaîne complète mise au point et flashée comme défauts firmware :**
- **K_P=2.0 / K_I=0.10 / K_D=0.10** (`lino_base_config.h`). Ki BAS car le FF fait le maintien.
- **Feedforward `KFF_DEFAULT=7.87` PWM/rpm + `FF_OFFSET_DEFAULT=21`** (`firmware.ino`) : PWM=Kff×cible+PID.
  ⇒ **réponse IDENTIQUE à toutes les vitesses** (sans FF, l'intégrale devine le PWM → dépassement variable).
- **`MOTOR2_GAIN=1.000`** (le FF + intégrale gèrent l'asymétrie).
- **Anti-windup back-calculation** (`pid.cpp`) : vide l'intégrale en saturation (≠ gel) → plus de dépassement à haute vitesse.
- **Estimateur vitesse petite fenêtre 12 counts** (`firmware.ino`) : vitesse propre à basse vitesse (l'instant getRPM = ±70 % de bruit à 4 rpm).
- **Dither anti-stiction `DITHER_DEFAULT=92` PWM**, actif **<13 rpm seulement** : ±92 alterné à 25 Hz casse le stick-slip → **mouvement lisse jusqu'à ~0,06 m/s** (docking). Sans lui : oscillation 0→9 rpm.
- **Plancher mécanique : ~0,09 m/s sans dither, ~0,06 m/s avec.** En dessous = stick-slip (zone morte moteur ~120 PWM). Nav à 0,16, docking à ≥0,06.
- **`/debug/tune` (Twist) live-tune :** linear=Kp,Ki,Kd ; angular.x=R-gain ; **angular.y=Kff** ; **angular.z=dither**.
  Le `pid_tuner.py` a des sliders pour tout (dont Kff et Dither). Live = RAM ; les défauts ci-dessus sont compilés.
RAPPEL : après chaque power-on Teensy, recaler l'encodeur (`align_enc_cal.py`, ~8 s) sinon le ripple revient.

## Historique du diagnostic (pour comprendre)
**Premiers gains (avant FF) ≈ Kp 0.8 / Ki 0.2 / Kd 0.5** : droite OK, mais la GAUCHE gardait un cycle limite.

**Le point dur = la roue GAUCHE** : garde un **cycle limite lent (~1 s, ±6 rpm) qui ne réagit quasi
pas au Kd** → ce n'est PAS un réglage linéaire mais un **non-linéaire** : stick-slip (entretenu par
l'intégrale) et/ou le **câble gauche en faux-contact** (voir [[amr-left-wheel-faux-contact]]).
Test discriminant : baisser **Ki 0.2 → 0.1 → 0.05** ; si l'oscillation s'effondre = intégrale/stick-slip
(garder Ki bas) ; si elle persiste à Ki≈0 = **c'est le câble**, aucun gain ne le corrige.

**Principe diff-drive (important) :** garder **UN seul Kp/Ki/Kd commun** aux deux roues (même
dynamique en boucle fermée → robot va droit), réglé pour la **pire roue (la gauche)** ; compenser
l'asymétrie établie avec le **feedforward R-gain (MOTOR2_GAIN)**, PAS des gains PID par roue (sinon
le robot dévie au démarrage). Le firmware fait déjà ça.

**CAUSE TROUVÉE (2026-06-29) — encodeur gauche décentré.** `scripts/encoder_calib.py` (open-loop,
vitesse constante, range la vitesse mesurée par angle de roue = counts mod 1024) montre que la roue
GAUCHE a une **erreur géométrique 2 cycles/tour de ~40 % crête-à-crête** (0,85→1,22), **identique aux
3 vitesses** (120/180/250) → calée sur l'angle, pas sur le temps = **aimant de l'encodeur gauche
décentré/incliné** (AS5040). La DROITE n'a que ~±4 % (bien alignée). Donc l'« oscillation » de la
gauche n'était PAS réelle : le PID pourchassait un ripple de MESURE de 40 %. Aucun gain ne corrige ça.
**CORRECTION par table — ESSAYÉE PUIS ABANDONNÉE (2026-06-29).** Table par roue `LEFT_CAL/RIGHT_CAL[36]`
dans `firmware.ino` (`calib_rpm()` : vraie = mesurée / cal[counts mod 1024]). v1 : gauche devenue plate
(2,3 %) mais droite ratée (anti-phase, 19 %). v2 (tables raffinées) : **les DEUX ont rebougé** (gauche
±5 %, droite ±8 %) → **ÉCHEC, n'a pas convergé**. **CAUSE FONDAMENTALE : l'encodeur est lu en
INCRÉMENTAL → les counts repartent de 0 à CHAQUE boot, à la position où la roue est. Donc
`counts mod 1024` = angle RELATIF au boot, pas absolu. Chaque reflash redémarre le Teensy → le zéro
encodeur se décale d'un angle aléatoire (différent gauche/droite car roues à positions différentes) →
la table figée est appliquée au mauvais angle.** ⇒ **une table position-indexée NE PEUT PAS marcher de
façon fiable avec un encodeur incrémental** (phase perdue à chaque power-cycle).
**FIX FINAL ADOPTÉ (2026-06-29) = TABLE de correction chargée à chaud + recalage de phase rapide par
boot.** (L'estimateur angulaire = vitesse sur 512 counts = demi-tour annulait le ripple mais ajoutait
~0,6 s de LAG → refusé par l'user pour le PID. La table est INSTANTANÉE.) Une table compilée ne marche
pas (le flash reboote → décale le zéro). Donc : le firmware charge la table 36+36 **à l'exécution** via
`/debug/enc_cal` (Float32MultiArray) → `calib_rpm` instantané. La FORME du ripple est fixe (aimant), seule
sa PHASE bouge par boot → on fige la forme 1 fois (`scripts/encoder_ref_table.json`) et à chaque boot
`scripts/align_enc_cal.py` (~8 s) : spin court → mesure brut → corrélation sub-bin (~1°) vs référence →
roule au bon angle → publie. **GROS PIÈGE : l'align DOIT remettre la table à plat (1.0) AVANT de mesurer**,
sinon il mesure le résiduel de la table déjà chargée → mauvais offset → table anti-phase → ripple DOUBLÉ
(~71 % > brut). Symptôme = la vérif montre un ripple PLUS GROS que le brut. Résultat : GAUCHE ±40 %→±4 %,
DROITE ±3,5 %, plat, instant, survit au reboot (re-align). **À relancer après chaque power-cycle Teensy**
(pas par lancement ROS — la table vit dans la RAM Teensy). **Commande (lancée DEPUIS LE PC, dans
`~/Documents/openamr`, PAS sur le Pi ; ROUES EN L'AIR ; bringup lancé pour l'agent micro-ROS ; 24V) :**
`cd ~/Documents/openamr && source /opt/ros/jazzy/setup.bash && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 && python3 scripts/align_enc_cal.py --arm 250` (rapide ~6-8 s) ;
full = `scripts/calibrate_and_apply.sh`. Le script parle au firmware via `/debug/enc_cal` (Cyclone/domain0). **`MOTOR2_GAIN` = 1.000** (config figée 2026-06-29, cf. ligne 17 — le FF+intégrale gèrent l'asymétrie ; l'ancien 1.05/1.10 était pré-feedforward, PÉRIMÉ — vérifié dans `lino_base_config.h`). Données pour
diagrammes : `docs/data/encoder_calib_*.json`. Récit complet : `docs/history/encoder-calibration.md`.

Le firmware a le RPM précis (méthode période) et le live-tune `/debug/tune` qui marche (voir
[[amr-architecture-doc]] §firmware). Détail complet dans `docs/CHANGELOG-FIXES.md`.
