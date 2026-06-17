---
name: amr-runaway-rootcause
description: "Emballement roue droite AMR RÉSOLU — 2 réglages du driver droit (pot VAR + pot ACC/DEC)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

## RÉSOLU (2026-06-17)
Chaque driver ZBLD a DEUX pots : **VAR** (gain/vitesse, en haut) et **ACC/DEC** (rampe accel/decel, près des SW).
Deux réglages du driver DROIT étaient faux (vs gauche, la référence qui marche) :
1. **VAR droit = 10/max** (gauche 3,5) → roue droite ~8× trop rapide → emballement. Corrigé.
2. **ACC/DEC droit = 0/10** (gauche 4/10) → réponse brutale, pas de lissage → à-coups/oscillation en
   BOUCLE FERMÉE (chaque micro-correction du PID passait brute). **C'était la cause du résidu.** Mis à 4.
Après alignement des 2 pots droits sur le gauche : test boucle fermée 0.1 m/s pendant 8 s **sans aucun
abort ni à-coup**, les 2 roues suivent la consigne proprement. Encodeurs/câblage/firmware étaient sains
(prouvé par les tests). C'était de la **config driver**, pas du logiciel.
Résidu mineur : droite ~5 % plus faible à VAR 3,5 (pwm 167 vs 152) ; PID compense ; affiner en montant
le VAR droit vers ~4 si on veut pwm égaux. Reste à valider : marche au sol, rotation, vitesses plus hautes.

---
Diagnostic de l'emballement roue droite (2026-06-17), via le firmware debug (/debug/left|right|pwm,
counts bruts) — voir [[amr-firmware-debug-flashed]].

**Cause principale TROUVÉE et corrigée : potentiomètre du driver droit mal réglé.**
Pot driver GAUCHE = 3,5/10, pot driver DROITE = **10/10 (à fond)**. DIP identiques sur les deux
(SW1+SW2 ON, SW3-6 OFF). Le pot règle le gain/vitesse du driver → à PWM égal la roue droite
tournait ~8× plus vite → emballement. **L'utilisateur a baissé le pot droit à 3,5** (24V coupé).
Résultat : énorme amélioration (avant : emballement instantané ; après : ~4 s de tracking
propre et symétrique à 0.05 m/s). Le droit d'origine était à 10 (pour revenir en arrière si besoin).

**Résidu : oscillation physique (cycle limite) du canal droit.** Même après le pot, la roue droite
fait des à-coups sporadiques violents (excursions +73 / −67 / −129 rpm) alors que la gauche reste
lisse. Capture 50 Hz autour d'un jerk : les counts droits bougent de façon COHÉRENTE sur plusieurs
échantillons (rampe ~−20 puis ~+24…), PAS un pic isolé → c'est un VRAI mouvement (la roue vibre
avant/arrière ~±10-20°), **pas un glitch encodeur/EMI**. Donc encodeur + câblage droit SAINS.
=> instabilité de boucle : le moteur/driver droit a une réponse dynamique différente du gauche ;
les mêmes gains PID stabilisent la gauche mais font osciller la droite.

**Ce qui est écarté** : encodeur droit mort (test A), mauvais signe (_INV ok), dropout/EMI encodeur
(counts cohérents), windup pur (le pwm ne rampait pas lors du jerk à 0.05).

**Test BOUCLE OUVERTE décisif (mode /debug/openloop ajouté au firmware : PWM fixe sur les 2 moteurs,
PID ignoré ; pots égaux 3,5).** À PWM 120 pendant 10 s, LES DEUX roues tournent parfaitement lisses
(counts réguliers ; droite ~12 % plus lente que gauche, mineur). UN seul échantillon droit aberrant
(rpm 55,7 alors que counts +8 = fausse lecture sans mouvement). => **le matériel droit est SAIN**
(moteur, driver, encodeur savent tourner propre). L'à-coup n'existe QU'EN BOUCLE FERMÉE → c'est une
**instabilité de boucle**, pas une panne HW. Mécanisme probable : la mesure de vitesse droite produit
parfois une valeur fausse, inoffensive en boucle ouverte mais que le PID amplifie en à-coup en fermé.
Anti-windup + K_I 0.15 ont bien atténué (tient ~3,8 s, excursions plus douces) mais pas éliminé.

**Pistes pour finir** : (1) rendre la mesure rpm ROBUSTE aux aberrations (filtre/rejet d'outliers sur
current_rpm avant le PID) — cible directe du mécanisme ; (2) intégrité signal encodeur droit (masse
commune, blindage, routage loin des câbles puissance) ; (3) mode boucle du driver (SW1 ouvert/fermé) :
si les ZBLD régulent en interne, double boucle vs PID Teensy. Recaler aussi avec la vraie source firmware.

**Pistes restantes pour le résidu** : (1) tuning PID — anti-windup (pid.cpp n'en a aucun) + baisser
K_I / ajouter de l'amortissement pour amortir le cycle limite droit ; (2) vérifier pourquoi le driver/
moteur droit répond différemment (Hall droit ? réglage interne driver ?) ; (3) attendre la vraie source
firmware (~2026-06-19) qui a la vraie tuning de l'auteur. Reco : ne pas tuner à l'aveugle, recaler avec
la vraie source.

Note : le pot droit pourrait aussi gagner à être affiné (à 3,5 la droite sous-réagit un peu, undershoot).
