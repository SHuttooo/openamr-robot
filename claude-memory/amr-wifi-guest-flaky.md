---
name: amr-wifi-guest-flaky
description: "Le robot est sur le WiFi Motionlab-Guest (isolé/instable) — quand ça rame, mDNS+DDS lâchent et ça RESSEMBLE à une panne lidar/robot alors que non ; vérifier le réseau d'abord"
metadata:
  node_type: memory
  type: reference
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-06** : symptômes « le lidar ne marche plus », « le robot ne bouge plus »,
`ros2 topic echo` qui timeout depuis le PC, `botshare.local` qui ne résout plus
(`getent hosts` FAIL), `ping 172.17.17.64` 100 % packet loss — **tout ça = le WiFi
`Motionlab-Guest` qui rame**, PAS une panne robot. Ça buggait même sur le téléphone.
Une fois le réseau revenu : ping 16 ms, lidar `/scan` + `/scan_filtered` à ~6,8 Hz
(normal pour RPLIDAR A1, 5,5-10 Hz), tout remonte.

## Caméra = ce qui SATURE le lien au bring-up (2026-07-06)
Symptôme : **dès `ros2 launch ... bringup.launch.py` (avec caméra), la connexion PC↔Pi
s'écroule** (ping/SSH/DDS lâchent). Cause : le **flux caméra pleine résolution 1280×720
~15 fps** part sur le WiFi Guest faible dès qu'un abonné PC existe (RViz, ou le
`web_video_server` du conteneur UI sur `/camera/image_raw`) → **sature le lien**.
Fix vérifié : relancer **`use_camera:=false use_docking:=false`** → connexion stable
(0 % perte, ~14 ms), le PC revoit les 46 topics nav, découverte DDS OK.
- **Pour la démo « go to Station 4 » : PAS besoin de caméra ni docking** (nav+wait seulement).
  Le bring-up léger est le bon défaut sur ce réseau. Bonus : supprime aussi la charge
  `dock_trigger`/apriltag qui ralentissait la nav près des costmaps.
- NB : le node `/camera` qui reste listé en mode `use_camera:=false` = le `web_video_server`
  du conteneur UI (nommé `camera`), PAS le driver caméra du robot — ne pas confondre.
- Si la caméra est requise plus tard (panneau vidéo UI) : fix RÉSEAU (Ethernet filaire, ou
  baisser résolution/fps du flux), pas le soft.

## L'UI Docker SUR LE PC sature aussi le lien → nav bloquée (2026-07-06)
Même avec `use_camera:=false`, lancer l'**UI Docker sur le PC** (`docker compose up`)
a bloqué la nav : les goals RViz n'atteignaient plus le Pi (pas de chemin affiché,
`/cmd_vel_nav` silencieux). Cause : les nœuds du conteneur (rosbridge + relais +
web_video_server) **s'abonnent depuis le PC à des topics gros et RELIABLE**
(`/global_costmap/costmap`, `/map`, `/tf`, `/scan`) → tempête de retransmission DDS
sur le WiFi dégradé → saturation → le `/goal_pose` PC→Pi ne passe plus. **`docker compose
down` = la nav repart immédiatement** (confirmé).
- **Implication démo : ne PAS faire tourner l'UI Docker sur le PC en même temps que la nav
  sur ce WiFi.** Bon déploiement = **UI servie SUR LE PI** (Flask :5050 + rosbridge LOCAL au
  Pi, tout le DDS reste sur le Pi ; seul le navigateur se connecte en WiFi via UN websocket,
  léger). Le runbook le dit déjà (« UI served by Flask on the robot »). Alternative : PC en
  **Ethernet filaire**.

## À retenir
- **Le robot est sur `Motionlab-Guest`** (confirmé par l'utilisateur), PAS `Motionlab-Member`.
  Ne PAS basculer le PC sur Member pour « joindre le robot » — il faut être sur le MÊME
  réseau que le Pi = Guest.
- Réseau Guest = souvent isolation client + instable → mDNS et le pont DDS PC↔Pi tombent
  en premier quand ça sature.
- **Réflexe de diagnostic : réseau AVANT robot.** Avant d'accuser lidar/nav/DDS :
  `getent hosts botshare.local` puis `ping botshare.local`. Si ça échoue → c'est le WiFi,
  pas le soft. Vérifier aussi que le PC n'a pas roamé sur un autre SSID
  (`nmcli -t -f ACTIVE,SSID dev wifi | grep yes`).
- Vérifier le lidar **directement sur le Pi** par SSH (source ROS + `ros2 topic hz /scan`),
  pas depuis le PC à travers le WiFi bancal — sinon on confond latence réseau et panne capteur.
- Cf [[amr-pi5-power-brownout]] (autre faux coupable : brownout alim → ping d'abord),
  [[pi-ssh-access]], [[amr-pi-ros-commands]].
