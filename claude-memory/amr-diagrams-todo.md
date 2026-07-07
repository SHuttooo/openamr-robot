---
name: amr-diagrams-todo
description: "Checklist des 15 diagrammes à générer : placeholders déjà posés dans les docs FW/HW/SW (chacun avec son prompt Claude intégré). Liste ici pour ne rien oublier avant la release."
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

## FW — `openamr-platform-fw` (branche `feature/teensy-4-0-linorobot2-overlay`)
- [ ] `docs/architecture/control-loop.md` — **Motor control loop** (PID + feedforward + anti-windup, 50 Hz)
- [ ] `docs/bringup/micro-ros-bringup.md` — **micro-ROS node topology** (Teensy client ↔ agent Pi ↔ ROS graph)
- [ ] `docs/architecture/debug-telemetry.md` — **Debug/telemetry topic map** (commandes vs télémétrie)
- [ ] `docs/architecture/encoder-calibration.md` — **Encoder ripple calibration workflow** (calib par boot)

## SW — `openamr-platform-sw` (branche `feature/real-robot-docs-pr`)
- [ ] `docs/real_robot/02_networking_and_dds.md` — **Networking & DDS topology** (PC/Pi/Teensy + pièges FastDDS/domain)
- [ ] `docs/safety/01_collision_monitor.md` — **Reactive-safety velocity chain** (controller→smoother→collision_monitor→/cmd_vel)
- [ ] `docs/real_robot/03_vision_pipeline_and_cpu.md` — **Vision pipeline 3-process vs intra-process** (avant/après)

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
