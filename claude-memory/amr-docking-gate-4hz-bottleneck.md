---
name: amr-docking-gate-4hz-bottleneck
description: "Le gate apriltag Python (image brute 2,7Mo) plafonne à ~4Hz saccadé → le scan de docking rate les tags s'il doit tourner ; compressé/dynamique cassent le TF ; + piège nom /camera avec l'UI Docker"
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-07 — LE chantier durable du docking : le débit d'images vers apriltag.**

## Le goulot
`apriltag_gate.py` est un script **Python** qui republie l'image **brute** (`/camera/image_raw`,
1280×720 bgr8 = **2,7 Mo/frame**) vers apriltag, gaté à la demande (service `/apriltag/set_enabled`).
Python ne suit pas à 14 Hz → il ne republie que **~4 Hz saccadé (trous de 0,9s)**. Mesure fiable = le
taux de `/apriltag/detections` (petits msgs) ; ⚠️ mesurer `/apriltag/image_in` **depuis le PC** est
trompeur (le WiFi plafonne le transport des images brutes de 2,7 Mo → faux 3-4 Hz même si le Pi va bien).

## Conséquence : le scan de recherche est fragile
`_search_for_tag` exige les **3 tags centrés 5 frames de suite**. À 4 Hz saccadé, ça ne réussit **que
si le robot arrive déjà face au dock** ; s'il doit **tourner pour chercher**, il balaie ~15° par trou
de 0,9s et rate le centrage → « tags not detected during scan ». **Fragilité PRÉ-EXISTANTE**, masquée
par un positionnement favorable. Ça a l'air de "marcher un jour, pas l'autre" selon où le robot arrive.

## Ce qui a été ESSAYÉ pour le débit et qui CASSE (ne pas refaire tel quel)
- **Gate dynamique** (subscribe/unsubscribe à la demande, MultiThreadedExecutor) → apriltag reçoit
  **0 image**. Cassé.
- **Gate compressé JPEG** (subscribe au flux compressé ~30× plus léger, décode via cv_bridge seulement
  les frames transmises) → **10 Hz d'images, apriltag DÉTECTE bien les 3 tags** MAIS l'image
  reconstruite par cv_bridge fait qu'apriltag **arrête de publier le TF** `camera_optical_frame →
  charging_dock_tag_{0,1,2}`. Or le **scan lit le TF, pas `/apriltag/detections`** → détection OK mais
  scan aveugle. Cassé (cause exacte du TF-cassé non isolée). **Les deux annulés → retour au gate brut.**

## Pistes propres (à froid)
1. Gate en **C++ / composable node intra-process** (zéro-copie, dans le container caméra+apriltag).
2. OU rendre le **scan tolérant au feed pauvre** : se contenter du **tag centre** (id1, le plus
   fiablement vu) au lieu d'exiger les 3, et/ou moins de frames consécutives.

## ⚠️ Piège annexe : conflit de nom `/camera`
Le `web_video_server` du **conteneur Docker de l'UI** s'appelle aussi `"camera"` → interroger `/camera`
(ex. `ros2 param get /camera AfMode`) tombe **au hasard** sur le vrai driver OU le web_video_server →
réponses incohérentes. **Arrêter l'UI Docker pendant les tests docking** (`docker compose stop`).

Cf `docs/2026-07-07-session-docking-corrector-rewrite.md`, [[amr-apriltag-on-demand-gate]],
[[amr-vision-latency-cpu]], [[amr-battery-voltage-check]] (le scan qui "cale" peut aussi = batterie).