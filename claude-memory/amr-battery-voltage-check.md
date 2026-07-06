---
name: amr-battery-voltage-check
description: "Seuils tension batterie 24V plomb : viser ≥25V au repos AVANT tout test nav/évitement (sinon couple mou → robot percute, on debugge Nav2 pour rien)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Toujours vérifier le 24 V (≥ 25 V au repos) AVANT tout test de navigation/évitement.** Système = 2× plomb
12 V en série. Au repos : **~25,5–26 V** = plein ✅ ; **~24 V** = ~50 % ⚠️ ; **≤ 23,5 V** = déchargé ❌.

**Why:** c'est la tension *au repos* ; **sous charge (moteurs) elle chute encore** (−1 à −2 V). Sous ~22 V
en charge → drivers en sous-tension → couple mou + la **roue gauche (faux-contact, [[amr-left-wheel-faux-contact]])
décroche** → le robot ne suit pas le plan → **percute des obstacles que la nav évitait**. Piège récurrent :
on debugge Nav2 alors que le vrai souci est le 24 V (déjà arrivé plusieurs fois).

**How to apply:** avant un test, multimètre sur le pack. Si < 25 V au repos → **recharger d'abord**, ne pas
conclure d'un test d'évitement. Relevé 2026-06-20 : **23,4 V → trop bas**, tests non concluants.
Détails : docs/hardware/power.md (table des seuils). Cf [[amr-nav2-bringup]], [[amr-next-session-plan]].
