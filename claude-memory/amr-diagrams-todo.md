---
name: amr-diagrams-todo
description: "Checklist des diagrammes release — TERMINÉE. HW = 11/11, FW = 4/4, SW = 3/3, tous générés/vérifiés/committés/poussés le 08-07. Plus aucun diagramme en attente."
metadata:
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-08 — Diagrammes à faire.** Des **placeholders** ont été posés dans les docs (repos FW/HW/SW),
chacun contenant **le prompt exact à coller à Claude** pour générer l'image, au bon endroit, le texte
autour rédigé comme si le diagramme existait déjà. Il reste à **générer les images** depuis ces prompts
et à remplacer le bloc placeholder par l'image. Chercher les blocs par `📐 Diagram:` dans les docs.

## HW — `openamr-platform-hw` (branche `feature/hardware-audit`)
- [x] `electrical/wiring/wiring-pinout.md` — **Wiring harness (system overview)** ✅ FAIT (diagrams/wiring-harness.svg, vérifié)
- [x] `electrical/wiring/wiring-pinout.md` — **Teensy 4.0 pin map** ✅ FAIT (diagrams/teensy-pinout.svg, vérifié)
- [x] `electrical/wiring/wiring-pinout.md` — **Driver signal + power connections** ✅ FAIT (v2, diagrams/driver-connections.svg, ordre bornes + anglais vérifiés). **wiring-pinout.md = 4/4 figures, 0 prompt résiduel**
- [x] `electrical/wiring/wiring-pinout.md` — **Driver DIP switch settings** ✅ FAIT (diagrams/driver-dip-switches.svg, vérifié)
- [x] `electrical/power_distribution/power.md` — **Power distribution** ✅ FAIT (diagrams/power-distribution.svg, vérifié)
- [x] `electrical/motor_control/motors-drivers.md` — **Motor control signal chain** ✅ FAIT (diagrams/signal-chain.svg, vérifié)
- [x] `electrical/sensors/encoders.md` — **AS5040 encoder wiring** ✅ FAIT (diagrams/encoder-wiring.svg, vérifié)
- [x] `README.md` — **System block diagram** ✅ FAIT (diagrams/system-block.svg, vérifié). **HW = 8/8 diagrammes, repo 100% propre**

- [x] `electrical/sensors/imu.md` — **IMU I²C wiring** ✅ FAIT (diagrams/imu-wiring.svg). Vérifié AVEC l'utilisateur : carte **marquée MPU-6050 mais silicium MPU6500** (WHO_AM_I 0x70, driver MPU9250) ; **3.3 V depuis le 3V3 Teensy** ; **AD0 non connecté** (addr 0x68 = défaut carte) ; XCL/XDA/INT/AD0 = n/c ; **pull-ups on-board** (aucune externe, valeur retirée)
- [x] `electrical/sensors/lidar.md` — **RPLIDAR A1 connection** ✅ FAIT (diagrams/lidar-connection.svg). Adaptateur physique = **Slamtec STC-A0317-R03** (pont CP2102, 10c4:ea60)
- [x] `electrical/sensors/camera.md` — **Camera Module 3 CSI connection** ✅ FAIT (diagrams/camera-connection.svg). Caméra **Pi-4 + adaptateur FPC 15→22 broches** pour Pi 5 ; connecteur **cam1** (doc corrigée cam0→cam1) ; « 4-lane » retiré. **HW = 11/11 diagrammes, 0 placeholder capteur restant**

## FW — `openamr-platform-fw` (branche `feature/teensy-4-0-linorobot2-overlay`)
- [x] `docs/architecture/control-loop.md` — **Motor control loop** ✅ FAIT (diagrams/motor-control-loop-per-wheel.svg, vérifié, committé a84c09e)
- [x] `docs/bringup/micro-ros-bringup.md` — **micro-ROS node topology** ✅ FAIT (diagrams/micro-ros-node-topology.svg, vérifié)
- [x] `docs/architecture/debug-telemetry.md` — **Debug/telemetry topic map** ✅ FAIT (diagrams/debug-telemetry-topic-map.svg, vérifié)
- [x] `docs/architecture/encoder-calibration.md` — **Encoder ripple calibration workflow** ✅ FAIT (diagrams/encoder-ripple-calibration-workflow.svg, vérifié, committé 21aa61c). **FW = 4/4 diagrammes, 0 placeholder restant**

## SW — `openamr-platform-sw` (branche `feature/real-robot-docs-pr`)
- [x] `docs/real_robot/02_networking_and_dds.md` — **Networking & DDS topology** ✅ FAIT (diagrams/networking-dds-topology.svg, vérifié, committé e2a2dd1)
- [x] `docs/safety/01_collision_monitor.md` — **Reactive-safety velocity chain** ✅ FAIT (diagrams/reactive-safety-velocity-chain.svg, vérifié)
- [x] `docs/real_robot/03_vision_pipeline_and_cpu.md` — **Vision pipeline 3-process vs intra-process** ✅ FAIT (diagrams/vision-pipeline-3-process-vs-intra-process-composition.svg, vérifié). **SW = 3/3. TOUS LES DIAGRAMMES FAITS : HW 11/11 · FW 4/4 · SW 3/3**

## Format placeholder ROBUSTE (2026-07-08) — les problèmes qu'on a eus + la solution
**Problèmes rencontrés (à ne plus refaire) :**
1. Commentaire HTML mal formé → le prompt restait VISIBLE en blockquote sur GitHub (2×).
2. Regex de placement non-greedy `(?:>.*\n)*?> ```` `` → s'arrêtait à la fence OUVRANTE → prompt orphelin.
3. SVG à fond transparent → rendu incohérent (fond blanc à injecter).
**Solution en place pour les 7 placeholders FW/SW restants :** chaque diagramme non généré =
  (a) une **ligne stub VISIBLE sans prompt** : `> 📐 **[Diagram: <titre>]** — placeholder...`
  (b) le **prompt + l'instruction de remplacement dans un commentaire HTML** (invisible sur GitHub).
  → Pour placer : remplacer la ligne stub + le commentaire par la SEULE ligne image `![...](diagrams/<slug>.svg)`
    que le commentaire dicte. Le prompt ne peut PLUS jamais fuiter (il est dans le commentaire).
  → Après placement, GREP de contrôle : `^> \`\`\`` et `^> (Draw|Create|Highlight)` = 0 (hors exemples de code légitimes).

## Style uniforme des diagrammes (2026-07-08)
- **Fond BLANC obligatoire** : les SVG transparents cassent le rendu → injecter un `<rect>` pleine
  toile `fill="#ffffff"` juste après `<svg>`. (3 SVG HW re-fondus le 08-07.)
- **Palette partagée** (hex explicites, PAS de `var(--...)`) : 24 V/power=rouge #c0392b, 5 V=orange
  #e67e22, 3.3 V logique=bleu #2c6fbb, data=gris #888, warning/danger=rouge, wired/OK=vert #2e8b57.
- Les **7 prompts restants (FW/SW) contiennent déjà ce bloc STYLE** → les prochaines générations
  seront cohérentes. Après placement d'un SVG, vérifier qu'il a bien un fond blanc.
- Astuce `var(--...)` : si un SVG en a, ce n'est cassé QUE si pas de `style="fill:rgb(...)"` inline
  (le style inline l'emporte → couleurs OK). teensy-pinout était dans ce cas = OK.

## Méthode / convention
- Format placeholder = blockquote `> ### 📐 Diagram: <titre>` + caption + un bloc ``` avec le prompt Claude.
- Chaque doc référence déjà le diagramme dans le texte (« shown below », « the diagram above »).
- **NE PAS** générer 36 diagrammes partout — seulement les points à vraie valeur (câblage, puissance,
  boucle de contrôle, topologie). C'est la consigne utilisateur : « pas des diagrams qui servent à rien ».
- ⚠️ **BUG DE PLACEMENT à éviter** : pour retirer le bloc placeholder, NE PAS utiliser un regex non-greedy
  `(?:>.*\n)*?> ```` `` qui s'arrête à la fence OUVRANTE → laisse le prompt en blockquote VISIBLE après l'image
  (arrivé 2× le 08-07). Retirer le bloc ENTIER (title→fence fermante), puis GREPER les orphelins :
  `grep -rn '^> ```' ` et `^> (Draw|Create|Highlight|pos [0-9])` doivent renvoyer 0.
- Une fois l'image faite : la mettre dans un `diagrams/` du repo, `![...](...)`, **et RETIRER complètement
  le bloc prompt** (image seule). ⚠️ NE PAS le garder en commentaire HTML : un commentaire mal formé a
  laissé le prompt VISIBLE en blockquote sur GitHub (bug 08-07). Les prompts restent dans l'historique git.
- SW a déjà des diagrammes ASCII dans `openamrobot_docking/docs/` — ne pas doublonner.
