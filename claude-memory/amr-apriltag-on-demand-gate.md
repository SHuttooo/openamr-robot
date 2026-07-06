---
name: amr-apriltag-on-demand-gate
description: "AprilTag à la demande : apriltag_node (166% CPU) ne tourne QUE pendant l'accostage, pas en nav. Gate dock_trigger active/désactive via service /apriltag/set_enabled. Résout la famine CPU qui retardait les goals Nav2 (load 8→4). QoS RELIABLE obligatoire."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Implémenté & vérifié sur le robot réel le 2026-06-30** (Day 2). Repo `openamr-platform-sw` →
`openamrobot_docking`. Doc complète : `docs/software/docking-apriltag-gate.md` ; journal §14
(`docs/history/diagnostics.md`).

## Pourquoi
`apriltag_node` traite chaque frame caméra → **~166 % CPU**. Lancé always-on dans le docking, il
**affamait le planner Nav2** (Pi à **load 8,3 / 4 cœurs**) → les goals mettaient des secondes à démarrer
(ce n'était PAS l'inflation, c'était le CPU). Tuer apriltag → load 8,3→4, délai disparu.

## Le design (gate on-demand)
- Nœud **`apriltag_gate.py`** entre caméra et apriltag : `/camera/image_raw → /apriltag/image_in`,
  **republie seulement si activé**. apriltag reste **vivant** (lit `/apriltag/image_in`), juste affamé
  quand désactivé → **~0 % CPU**. Toggle = un booléen → **instantané (<100 ms)**, pas de warm-up.
- Service **`/apriltag/set_enabled`** (`std_srvs/SetBool`). `dock_trigger` l'**active** à la zone de
  staging (pas pendant la nav vers le staging), le **désactive** en fin de séquence (`finally`).
- `dock_trigger` params : `use_apriltag_gate` (défaut **false** ; le launch réel met true ; en sim
  apriltag reste always-on et le service absent → no-op).

## ⚠️ Piège QoS (ne pas re-optimiser)
En **best_effort**, le sub caméra du gate se fait **affamer** dès qu'apriltag tourne (rx fige, apriltag
ne reçoit rien). La caméra publie **RELIABLE KEEP_LAST 1**. → le gate utilise **RELIABLE** des deux côtés.
Commenté dans le code « do not optimise back to best_effort ».

## Vérif (réel)
CPU apriltag : **1 % (off) → 102 % (on) → 1 % (off)** sur un cycle complet du service.

## Diff commandes opérateur (avant → après)
- Bring-up **inchangé** : `ros2 launch openamrobot_bringup bringup.launch.py map:=... use_docking:=true`.
- L'ancien contournement **`pkill -f "[a]priltag_node"`** (pour libérer le CPU en nav) → **supprimé**,
  apriltag est idle tout seul.
- Manuel (test détection / bouton UI) : `ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"`.

## NB
Caméra à débit **variable (~6–19 Hz)** observé — à surveiller pour l'asservissement visuel du docking
(sujet caméra séparé, n'affecte pas le gate). Cf [[amr-camera-imx708-libcamera]], [[amr-nav2-bringup]],
[[amr-pi5-power-brownout]]. Commits sans Claude [[amr-commit-no-claude]].
