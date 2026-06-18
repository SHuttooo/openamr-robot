---
name: amr-wiring-dc-colors
description: "Convention couleurs alim CONTINU (DC) de CE robot AMR — marron = + (rouge), bleu = − (noir)"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

Sur **CE** robot AMR (OpenAMR), l'alimentation **continue (DC, 24 V batteries/secteur)** est câblée
avec des couleurs de type **secteur (AC)**, ce qui est contre-intuitif :

- **MARRON = positif (+)** ← équivaut au **rouge** en DC
- **BLEU = négatif (−)** ← équivaut au **noir** en DC

⚠️ Piège : marron/bleu est normalement la norme AC (phase/neutre), pas DC. Ici c'est du DC.
La couleur reste une **présomption** : sur du 24 V, **vérifier au multimètre** avant de brancher
(pointe rouge sur un fil, noire sur l'autre ; affichage positif = pointe rouge sur le +). Le **COM/−**
doit rester la masse commune (cf. [[amr-real-bringup]] et docs câblage : common ground obligatoire).

Confirmé par Matthieu le 2026-06-18 en branchant le robot sur batteries.
