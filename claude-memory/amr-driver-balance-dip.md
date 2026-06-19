---
name: amr-driver-balance-dip
description: Équilibrage roues (pot VAR droit) + piste DIP SW1 boucle ouverte/fermée + limite de mesure rpm
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Tuning drivers ZBLD C20-120L2R (2026-06-19), sur **alim secteur**, roues en l'air, en **boucle ouverte**
(`/debug/openloop` PWM fixe, PID court-circuité) en streamant rpm gauche/droite.

**Asymétrie = cause du "tangage" (le robot serpente tout droit)** :
- Au départ, à PWM 200 : **gauche ~14,6 rpm, droite ~11,7 rpm → droite 20 % plus lente** (hardware).
- En boucle fermée, le PID compense (donne plus de PWM à droite ~230 vs gauche ~200) mais la droite
  **dépasse/oscille** → serpentage.
- **Fix = monter le pot VAR du driver DROIT** : en le montant (vers le max) la droite accélère et rejoint
  la gauche (~14 des deux côtés = équilibré). Confirmé : le pot agit (droite 10→20 rpm en tournant).
  Au **max** c'était bien équilibré ; trop bas → droite redevient lente.

**⚠️ Limite de mesure** : le rpm est **quantifié par pas de ~2,9 rpm** (≈20 % à 14 rpm) → les petits
réglages de pot **se noient dans le bruit** (« j'ai l'impression que ça change rien »). Pour voir fin :
tester à **PWM plus élevé** (ex. 400 → plus de rpm → quantif moins gênante).

**DIP — analyse + config cible (audit câblage 2026-06-19).** Fonctions (sérigraphie driver) : SW1=boucle
ouverte/fermée, SW2=source vitesse (AI1 pot interne / AI2 externe), SW3=secondaire (sans effet ici),
SW4+SW5=**paires de pôles** (2/3/4/5, **utile QUE en boucle fermée**), SW6=terminaison RS485.

🔶 **Défaut trouvé** : moteur = **P=5** (plaque : Z4BLD60-24GN-30S, P=5), mais **SW4/SW5 OFF/OFF = 2 paires**
→ en boucle fermée le driver calcule la vitesse ~2,5× faux → mauvaise régulation (contribue au tangage,
pot VAR peu réactif). ⚠️ Mapping ON/OFF→pôles lu sur photo floue (ON/ON supposé = 5) → confirmer avant.

**Quel correcteur ? → le PID Teensy est le meilleur** (lit l'AS5040 1024 cnt/rev = roue, fin, réglable
±2%, alimente /odom ; le driver lit l'arbre moteur via Hall grossiers, opaque). **Reco : driver en boucle
ouverte (SW1=OFF)** = Teensy seul maître, supprime la double boucle + rend les pôles sans effet. Plan B si
à-coups basse vitesse : revenir SW1=ON **avec SW4/SW5=ON/ON (5 paires)** = vraie cascade.

**CONFIG CIBLE (2 drivers identiques, 24 V coupé) : `SW1 OFF · SW2 ON · SW3 OFF · SW4 ON · SW5 ON · SW6 OFF`.**
Changements depuis l'état actuel (SW1+SW2 ON, reste OFF) : **SW1→OFF, SW4→ON, SW5→ON**. Cf
docs/hardware/motors-drivers.md + [[amr-encoder-5v-overvoltage]].

Outils de test réutilisables (sur Ubuntu, en Cyclone domain 0) : `/tmp/ol20.py` (boucle ouverte 20s
stream G/D), `/tmp/pwm_step.py` (boucle fermée PWM+rpm), `/tmp/forward50.py` (avance Xcm boucle fermée
odom). PWM via `/debug/openloop`. Cf [[amr-left-wheel-faux-contact]] (le câble gauche bloque tout).
