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

- [ ] `electrical/sensors/imu.md` — **MPU6500 IMU I²C wiring** (SDA18/SCL19, 3.3V, 0x68) — placeholder posé
- [ ] `electrical/sensors/lidar.md` — **RPLIDAR A1 connection** (CP2102 USB→Pi) — placeholder posé
- [ ] `electrical/sensors/camera.md` — **Camera Module 3 CSI connection** — placeholder posé

## FW — `openamr-platform-fw` (branche `feature/teensy-4-0-linorobot2-overlay`)
- [ ] `docs/architecture/control-loop.md` — **Motor control loop** (PID + feedforward + anti-windup, 50 Hz)
- [ ] `docs/bringup/micro-ros-bringup.md` — **micro-ROS node topology** (Teensy client ↔ agent Pi ↔ ROS graph)
- [ ] `docs/architecture/debug-telemetry.md` — **Debug/telemetry topic map** (commandes vs télémétrie)
- [ ] `docs/architecture/encoder-calibration.md` — **Encoder ripple calibration workflow** (calib par boot)

## SW — `openamr-platform-sw` (branche `feature/real-robot-docs-pr`)
- [ ] `docs/real_robot/02_networking_and_dds.md` — **Networking & DDS topology** (PC/Pi/Teensy + pièges FastDDS/domain)
- [ ] `docs/safety/01_collision_monitor.md` — **Reactive-safety velocity chain** (controller→smoother→collision_monitor→/cmd_vel)
- [ ] `docs/real_robot/03_vision_pipeline_and_cpu.md` — **Vision pipeline 3-process vs intra-process** (avant/après)

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
