---
name: amr-wheel-geometry
description: "Géométrie roues = le FIRMWARE fait foi (mesuré physiquement par l'utilisateur) : Ø roue 0.2 m (rayon 0.10), voie 0.46 m. Le 0.046533/0.4075 de l'URDF/SDF/BOM sont FAUX (artefacts CAD). Mon audit HW disait 'measured 0.046533' = erreur, corrigée."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-08 — Vérité terrain géométrie (confirmée : l'utilisateur a MESURÉ).**

## Valeurs correctes = le FIRMWARE (`lino_base_config.h`)
- **`WHEEL_DIAMETER 0.2`** → rayon 0.10 m → **roue Ø 20 cm**. ✅ mesuré.
- **`LR_WHEELS_DISTANCE 0.46`** → **voie 46 cm** (distance entre les 2 roues). ✅ **RE-MESURÉE au mètre
  ruban centre-à-centre le 08-07 = 0.46 m confirmé** → la question des « 5 cm » (0.46 vs CAD 0.4075) est
  CLOSE, le 0.4075 est définitivement rejeté (artefact CAD). BOM mis à jour (« confirmed by tape-measure »).

## Ce qui est FAUX (ne pas s'y fier)
Trois autres sources portent des valeurs erronées, toutes cohérentes entre elles mais fausses :
- URDF `robo_urdf.urdf.xacro` : hauteur d'axe de roue Z = **0.046533** (Y = ±0.20375 → voie 0.4075).
- `robot.sdf` plugin diff-drive : `wheel_radius 0.046533`, `wheel_separation 0.4075`.
- **Mon audit HW `components-bom.md`** disait « **Measured on the real robot** : wheel radius 0.046533,
  track 0.4075 » → **c'était FAUX**, j'avais recopié le `wheel_radius` du SDF (lui-même = le Z d'axe,
  artefact d'export CAD) en croyant que c'était une mesure. **Corrigé** au Ø 0.2 / voie 0.46.
- Piège visuel : `0.046533` (rayon, 4,6 cm) ≠ `0.46` (voie, 46 cm) — facteur 10, pas « proche ».

## Incohérence interne du repo SW (vrai bug sim, à signaler séparément)
Dans le même URDF, le **cylindre visuel/collision de roue = `radius 0.11`** (Ø 22 cm, ≈ le vrai) et
`gazebo_control.xacro` = `wheel_radius 0.11` — MAIS le **plugin diff-drive `robot.sdf` = 0.046533**.
Donc en **simulation l'odométrie/cinématique est scalée ~×2 faux** vs le modèle visible. Latent
(la nav sim est self-consistante) mais réel. Fix propre = mettre `robot.sdf` wheel_radius 0.10 /
wheel_separation 0.46 (package `openamrobot_description`, hors des 3 PR actuelles).

## Conséquence odométrie réelle
Comme le FW est correct, l'odométrie déployée est bonne. Le doute « ×2,15 » qu'on a exploré ce soir
est levé. Cf [[amr-pid-tuning]], [[amr-min-velocity-floors]] (planchers mesurés via cette odométrie =
valides). BOM : `manufacturing/bom/components-bom.md`, branche `feature/hardware-audit`.
