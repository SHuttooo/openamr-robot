---
name: amr-encoder-5v-overvoltage
description: "Défaut câblage 2026-06-19 (CORRIGÉ) — encodeurs étaient en 5V (A/B ~4V sur Teensy 3.3V non tolérant) → passés en 3,3V, validé"
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Défaut de câblage trouvé pendant l'audit câblage (2026-06-19).**

Les **encodeurs sont alimentés en 5 V** et leurs **sorties A/B mesurent ~4 V** sur les pins Teensy
(14/15 gauche, 11/12 droite). Or le **Teensy 4.0 n'est PAS tolérant 5 V** (3,3 V max, abs ~3,6 V).
Lire **4 V et pas 5 V** = la **diode de clamp interne du Teensy conduit déjà** → du courant entre dans
le pin en ce moment. Ça "marche" (la diode encaisse) mais c'est **hors spec** : use le pin (dégradation
lente, décrochages encodeur possibles, voire pin mort), peut remonter le rail 3,3 V. **Pas de
level-shifter ni diviseur** en place (sinon on lirait 3,3 V).

**✅ CORRIGÉ 2026-06-19** : l'AS5040 accepte 3,3–5 V (régulateur interne) → son **alim a été déplacée du
5 V (VUSB Teensy) vers le rail 3,3 V**. Vérifié : alim 3,3 V, lignes A/B plafonnent à ~3,3 V (plus de 4 V),
comptage propre sur 3 runs moteurs. Le 5 V (VUSB) n'alimente plus rien (normal). *Alternatives si le 3,3 V
avait fait un brownout : résistance série ~1–2,2 kΩ ou diviseur par ligne A/B, ou level-shifter.*

⚠️ Distinct du **bloqueur câble gauche** (lui = puissance 24 V / connecteur moteur, cf
[[amr-left-wheel-faux-contact]]). L'**IMU est correctement en 3,3 V** (RAS).
Cf docs/hardware/encoders.md. Fait partie de l'audit câblage demandé ([[amr-session-suite-nav2-cyclone]] item F).
