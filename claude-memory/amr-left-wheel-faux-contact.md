---
name: amr-left-wheel-faux-contact
description: "BLOQUEUR n°1 — roue/moteur GAUCHE intermittent (faux-contact câble), à réparer physiquement"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Le problème matériel n°1 du robot AMR (2026-06-18/19) : la chaîne GAUCHE coupe par intermittence.**

**Symptôme** : la roue gauche marche, puis s'arrête (rpm 0), puis revient — **toute seule**, sans
changement logiciel. Prouvé en **boucle ouverte** (PWM fixe via `/debug/openloop`, PID court-circuité) :
gauche passe de ~14 rpm → 0 → ~14 alors que la droite tourne normalement. Donc **ce n'est NI le PID, NI
le firmware, NI la batterie, NI le RMW**. Quand elle est morte, le firmware envoie du PWM **saturé**
(monte à 600-700) mais rpm reste 0 = **pas de puissance au moteur gauche**.

**Diagnostic** : **faux-contact / fil aux brins cassés** dans le faisceau gauche (24 V ou phases moteur),
qui fait/coupe au moindre flex/vibration. Le wiggle des connecteurs ne l'a pas localisé proprement
(parfois revient en bougeant, parfois pas, parfois sans rien toucher) → typique d'un **fil coupé à
l'intérieur de la gaine** ou d'un contact oxydé. Pas réparable à distance.

**À FAIRE DEMAIN (Matthieu, manuel) :**
1. **Réparer le faisceau gauche** : multimètre en continuité **en pliant** chaque fil (24 V + phases
   U/V/W) → trouver le brin cassé → **re-souder / remplacer** (ne pas juste re-sertir, ça revient).
2. **Test d'échange driver G↔D** si doute : si le défaut suit le driver → driver gauche HS ; s'il reste
   à gauche → moteur/câblage gauche.
3. Vérifier driver gauche : LED/fault, chaud ? (piste thermique).

C'EST LE SEUL BLOQUEUR RESTANT. Tout le logiciel est prêt (cf [[amr-session-2026-06-18]]).
Voir aussi [[amr-pid-tracking-observation]], [[amr-runaway-rootcause]], docs/hardware/motors-drivers.md.
