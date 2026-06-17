---
name: amr-encodeurs-ok-test-a
description: "Résultat tâche A — les DEUX encodeurs du robot AMR comptent, hypothèse \"encodeur droit mort\" réfutée"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2cacdf32-9177-478e-aa34-23589a0b332a
---

Test A (2026-06-17, roues en l'air, tournées à la main, sans alim 24V) : test guidé qui reconstruit
la vitesse par roue depuis `/odom/unfiltered`. Résultat sans ambiguïté :
- Roue gauche tournée → v_gauche réagit (max 0.153), v_droite reste 0.
- Roue droite tournée → v_droite réagit (max 0.368), v_gauche reste 0.

**Conclusion : les deux encodeurs comptent, mapping gauche/droite (MOTOR1/MOTOR2) correct.**
L'hypothèse principale du brief (« encodeur droit mort ») est RÉFUTÉE. L'odométrie « figée »
vue avant n'était que le robot au repos (0 = normal).

**Why:** ça réoriente tout le diagnostic de l'emballement de la roue droite.
**How to apply:** chercher la cause de l'emballement ailleurs — piste forte = erreur de SIGNE
dans la boucle PID droite (contre-réaction positive) : `MOTOR2_ENCODER_INV` et/ou `MOTOR2_INV`
incohérents (le côté droit a des `_INV` opposés au gauche). Autre suspect : driver ZBLD en
boucle fermée (DIP SW1) qui se bat avec le PID. La moitié "encodeur" du signe se teste sans
puissance (rouler chaque roue en avant → vitesse mesurée doit être positive des deux côtés) ;
la moitié "moteur/driver" nécessite un test sous 24V (roues en l'air, coupure rapide prête).

Scripts de diag sur le Pi (~/) et en local (Documents/projet/openamr/) : `guided_encoder_test.py`
(test A guidé), `sign_test.py` (signe), `encoder_timeline.py`, `encoder_capture.py`.
NE PAS reflasher (firmware en place fonctionne ; vraie source firmware attendue ~2026-06-19).
Accès Pi : [[pi-ssh-access]].
