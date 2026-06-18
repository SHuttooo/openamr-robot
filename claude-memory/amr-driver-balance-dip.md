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

**Piste DIP SW1 (à tester demain)** : SW1 = boucle ouverte/fermée du driver. Actuellement **SW1 ON** (le
driver régule en interne via les Hall) → **double boucle** avec le PID Teensy → peut amplifier les
oscillations. Tester **SW1 dans l'autre position** (driver en boucle ouverte, seul le PID Teensy régule)
sur les **2 drivers identiquement** (24 V coupé) → voir si le tangage baisse. DIP actuels : SW1+SW2 ON,
SW3-6 OFF (SW2=AI2 source vitesse, SW4/5=paires de pôles, SW6=RS485). ⚠️ Tableau = interprétation projet,
pas le datasheet officiel — vérifier le datasheet avant de toucher SW4/SW5 (paires de pôles).

Outils de test réutilisables (sur Ubuntu, en Cyclone domain 0) : `/tmp/ol20.py` (boucle ouverte 20s
stream G/D), `/tmp/pwm_step.py` (boucle fermée PWM+rpm), `/tmp/forward50.py` (avance Xcm boucle fermée
odom). PWM via `/debug/openloop`. Cf [[amr-left-wheel-faux-contact]] (le câble gauche bloque tout).
