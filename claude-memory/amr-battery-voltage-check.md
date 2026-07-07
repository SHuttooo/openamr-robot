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

## ⚠️ SIGNATURE-CLÉ (2026-07-07) : « il bouge en NAV mais CALE en rotation sur place » = batterie basse
Symptôme diagnostic vécu tout un soir avant de trouver : le robot **avançait** en navigation mais le
**scan de docking (rotation sur place) ne démarrait pas** — « ça envoie 0,3 puis 0,5 rad/s mais il ne
bouge pas ». **Ce n'est PAS le code, c'est le couple / la batterie.** Pourquoi ce split :
- **Avancer** = 2 roues même sens + **inertie** + peu de couple → passe encore batterie faible.
- **Tourner sur place** = 2 roues sens opposés, **aucune inertie**, vaincre la friction statique des
  deux côtés à l'arrêt = **le mouvement le plus gourmand en couple** → cale en premier quand le jus baisse.
Donc **« nav OK mais rotation-sur-place qui cale » = drapeau rouge batterie**, à vérifier AVANT de
debugger le docking/scan. ⚠️ **La tension n'est PAS publiée dans ROS** (`/diagnostics` = caméra
seulement) → **multimètre obligatoire**. Une longue session (heures) décharge assez pour déclencher ça.
