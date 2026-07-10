---
name: amr-old-repo-merge
description: "Merge de l'ancien repo produit openAMRobot/openamr (CAD mécanique + BOM + images + datasheets) dans openamr-platform-hw. Décisions prises 2026-07-08. Bloqueur = git-lfs pas installé."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-08 — Merger l'ancien repo dans les repos release (demandé par l'utilisateur, Alex a signalé « énormément de données »).**

## L'ancien repo : `github.com/openAMRobot/openamr` (MIT © OpenAMRobot)
Repo **produit/mécanique** de l'org. **MÊME robot** que le build de Matthieu : le README HW dit
« utilise l'électronique **Linorobot**, moteur+contrôleur upgradés en **ZD BLDC + ZD driver** ». L'image
`HW_schema_article.jpg` confirme le MC_NODE = **ZBLD.C20-120L2 + AS5040 (0.087°=4096) + BLDC wheel L/R + Pi5 + Nav2**.
= exactement le build actuel. Roue = Blickle GEVN 200/30 (Ø0.2 m = mesure de Matthieu ✅).
C'est un **SUPERSET produit** : options lift/convoyeur/wireless-charging/QR-line-tracking/NVIDIA + **LiFePO4/BMS**
(→ ça VALIDE la généricisation batterie faite le 08-07 : produit = LiFePO4, pas plomb).

## Contenu à merger (docs/hardware/, ~180 Mo utiles)
- `CAD_files/` : assemblage complet STEP + **~90 fichiers production** (SolidWorks/STEP/DXF/PDF : panneaux, base,
  cover, wheel assembly, motor bracket, drive shaft, brackets, lidar support, camera body, magnetic encoder) +
  projet SW17 complet .zip (55 Mo). = **53 Mo STEP + 55 Mo zip + 12 Mo sldprt + 7.5 sldasm + 3.8 slddrw + 432 Ko dxf**
- `BOM/BOM_specs_MMP.xlsx` (40 Ko) + README (tôlerie K=0.47, visserie, roues/casters Blickle) = BOM **mécanique**
- `datasheets/` : **37 PDF** (25 Mo) ZD/ZLTech/TZBot — **copyright fabricant**
- `pictures/` : **32 images** (25 Mo) vues robot, wheel assembly 1-5, renders, ecosystem, HW schema
- `schematics/` = VIDE (l'électrique = repo de Matthieu)

## DÉCISIONS (toutes prises 2026-07-08)
- **Cible** = `openamr-platform-hw` (la structure `mechanical/{cad,chassis,drawings,renderings}/` +
  `manufacturing/{assembly,vendors}/` existe déjà en placeholders vides → le contenu s'y insère pile).
- **Branche** : `feature/mechanical-cad` depuis `feature/hardware-audit` (recommandé, à confirmer).
- **Git LFS** pour les binaires : `*.STEP *.SLDPRT *.SLDASM *.SLDDRW *.DXF *.pdf *.zip *.png *.jpg`.
- **Périmètre** = TOUT le hardware, **base testée vs options produit ÉTIQUETÉES** (ne pas prétendre que la base a un lift).
- **Datasheets** = **re-host + attribution** « Source: <manufacturer> » (choix d'Alex, comme l'ancien repo).
- **EXCLURE** : `CONTRIBUTING.md` (« sauf contribution »), section marketing/Stripe du README, submodules UI
  (`OpenAMR_UI_package`, `OpenAMR_UI_dev` — on ne touche pas à l'UI).

## Plan (phases, dès git-lfs installé)
1. Branche + `.gitattributes` LFS. 2. CAD → `mechanical/` + README index pièces MMP.xx. 3. Images → `renderings/`
+ intégration docs (hero README, wheel assembly). 4. BOM méca → réconcilier avec `components-bom.md`. 5. Doc
« architecture produit » (base vs options). 6. Datasheets re-host+attribués → `datasheets/`.

## ✅ FAIT (2026-07-08) — merge complet + poussé
Branche **`feature/mechanical-cad`** (depuis hardware-audit) poussée sur le fork SHuttooo. Contenu :
mechanical/cad (99 fichiers CAD + full assembly STEP + SW17 zip), renderings (21), assembly (5 wheel steps),
datasheets (31 + index+attribution + motor-sizing-calculations.md), BOM méca (xlsx+mechanical-bom.md),
product-architecture.md (base vs options), README illustré (hero+layout+ecosystem), CODE_OF_CONDUCT.
**Incohérences réconciliées** : gearbox **25:1** (pas 30:1 — 4GN 25K confirmé par les calculs ; suffixe -30S = code série, PAS le ratio),
courant 3.8A (plaque), DIP table « Was/Now » (pas Current/Target). Pins = les nôtres (inchangés).

## ⚠️ LFS ABANDONNÉ → git normal (leçon)
GitHub **refuse les objets LFS sur un fork public** (`can not upload new objects to public fork`) — même pour
juste pousser/visualiser. Donc **converti LFS→git normal** (`git lfs migrate export`) comme l'ancien repo (qui
portait 330 Mo sans LFS). Plus gros fichier = 50 Mo (SW17 zip) < limite 100 Mo GitHub. `.gitattributes` = marqueurs
`binary`. **Ne PAS retenter LFS sur ce fork.** Bonus : la PR upstream passera sans dépendance LFS.
