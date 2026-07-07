# Session robot — 2026-07-07 : réécriture du correcteur de docking, saga du gate, et LE mot de la fin (batterie)

Longue session (plusieurs heures) centrée sur le **docking réel** : améliorer le correcteur
d'approche finale, puis une longue chasse à un scan qui ne trouvait plus les tags — qui s'est
finalement révélée être un **problème de batterie**, pas de code. Ce doc raconte **tout** : ce qui
a été corrigé, ce qui a été cassé puis annulé, les fausses pistes, les vraies causes, et toutes les
commandes utilisées.

Robot : Pi 5 (`botshare.local`), Teensy/micro-ROS, RPLIDAR A1, caméra IMX708, ROS 2 Jazzy, Nav2,
CycloneDDS domaine 0. Branche de travail : `fix/docking-near-servo-af` (repo `openamr-platform-sw`).

---

## 🟢 CE QUI A ÉTÉ VRAIMENT AMÉLIORÉ (le correcteur d'approche — solide, validé "c'est aligné")

Le régime final d'approche (`_final_visual_approach` dans `dock_trigger.py`) oscillait et arrivait
de travers. Plusieurs fixes empilés, tous gardés :

1. **Bug de dérivée (dt réel)** — le terme dérivé du correcteur divisait par un `period` **fixe**
   (0,05s) au lieu du temps réel écoulé. Quand le tag est perdu plusieurs cycles (mesuré : 25% des
   frames à 0 tag près du contact), ça gonflait la dérivée à chaque réapparition → à-coup. Fix :
   vrai `dt`, et si trou > ~125ms on réamorce sans dérivée.
2. **Compensation de profondeur** — le correcteur pilotait sur l'angle caméra brut `atan2(X,Z)`, qui
   **grossit mécaniquement** en approchant (même erreur physique → angle de plus en plus grand). Or
   c'est ce qui donnait "ça empire à la fin". Fix : piloter sur le **décalage latéral réel** avec un
   **lookahead fixe** (comme le fait FAR), pas la profondeur qui rétrécit.
3. **Report d'orientation par odométrie** — quand seul le tag centre est visible, il n'y avait
   **aucune contrainte d'orientation** (le robot gardait le tag centré mais pouvait arriver de
   travers). Fix : porter la dernière bonne normale connue et la recaler via le lacet odométrique
   (roues+IMU, indépendant du LIDAR). → **"c'est beaucoup mieux, c'est aligné"**.
4. **Simplification en paliers** — abandon du correcteur PD (kp/kd/deadband/PWM) : suivre l'axe tant
   qu'on a ≥2 tags, sinon la normale portée avec le tag centre, sinon **avancer aveugle**.
5. **Moyenne pondérée par stabilité** + **pondération inversée** (poids max **loin**, min **près** —
   la base large des 2 tags se dégrade de près, cf. leçon 28 de la doc simu).
6. **Gel de la normale** sous `freeze_axis_distance`, **recalé par odométrie** (bug corrigé : une
   valeur figée dans `base_link` devient fausse quand le robot tourne).

⚠️ **Point de sauvegarde retenu = commit `31fe8b1`** ("c'est aligné"). C'est l'état restauré et
déployé en fin de session (voir plus bas). Tous les fixes ci-dessus y sont.

---

## 📷 CAMÉRA — autofocus + le piège du nom `/camera`

- **Autofocus continu activé** (`AfMode: 2` dans `camera.launch.py`) — la caméra était en focus
  **manuel fixe à 1m**, floue en approche finale (0,25-0,70m). Confirmé actif (14 Hz, `FocusFoM`
  dans `/diagnostics`). L'utilisateur veut l'AF **toujours** actif (pas de gating).
- **PIÈGE MAJEUR — conflit de nom `/camera`** : le `web_video_server` du conteneur **Docker de l'UI**
  s'appelle aussi `"camera"`. Donc interroger `/camera` (ex. `ros2 param get /camera AfMode`) tombe
  **au hasard** sur l'un ou l'autre node → réponses incohérentes ("Parameter not set" un coup, `2`
  l'autre). **Fix : arrêter l'UI Docker pendant les tests docking** (`docker compose stop`). A fait
  perdre du temps à croire que l'AF ne marchait pas.

---

## 📡 LA SAGA DU GATE APRILTAG (le gros piège du soir — au final ANNULÉ)

**Le fond du problème** : le gate (`apriltag_gate.py`) est un script **Python** qui republie l'image
**brute** vers apriltag. À 1280×720 bgr8 = **2,7 Mo/frame** × 14 Hz, Python ne suit pas → il ne
republie que **~4 Hz saccadé** (trous de 0,9s). Conséquence : le scan de recherche exige les 3 tags
centrés 5 frames de suite — à 4 Hz saccadé, **ça ne marche que si le robot arrive déjà face au dock**
(sinon il balaie ~15° par trou de 0,9s et rate le centrage). **Cette fragilité est PRÉ-EXISTANTE**,
elle a juste été masquée par un positionnement favorable.

Tentatives d'optimisation, **toutes cassées et annulées** :
- **Gate dynamique** (`c077164`) — abonnement créé/détruit à la demande sous MultiThreadedExecutor.
  → apriltag recevait **0 image**. ❌ Annulé (`e7c722a`).
- **Gate compressé JPEG** (`477385d`) — subscribe au flux compressé (~30× plus léger), décode via
  cv_bridge seulement les frames transmises. → **10 Hz d'images, apriltag DÉTECTAIT les 3 tags** !
  MAIS le scan échouait quand même : l'image reconstruite par cv_bridge faisait qu'apriltag
  **arrêtait de publier le TF** `camera_optical_frame → charging_dock_tag_{0,1,2}`. Or le scan lit le
  **TF**, pas `/apriltag/detections`. Détection OK, scan aveugle. ❌ Annulé (`dece0b7`).

**Conclusion gate** : revenu à la version **brute** (4 Hz, TF correct). Le débit reste le vrai
chantier à traiter à froid (gate C++/intra-process, OU rendre le scan tolérant au feed pauvre — ex.
se contenter du tag centre, ou moins de frames consécutives).

---

## 🔍 LE SCAN — mes changements qui ont ajouté du bruit (annulés au retour à 31fe8b1)

- `staging_distance` 2.0→1.2→1.7, `predock_distance` 2.0→1.5 : le commentaire du yaml était calé sur
  le **tag de simu (0,40m)**, pas le vrai (0,131m). À 2m le vrai tag est petit → détection marginale.
- **Warmup** (attendre N échantillons avant de corriger) + **plancher moteur sur le scan** (`f8ca8a4`).
- ⚠️ **BUG que j'ai introduit** : le plancher moteur (`_floor_omega`) a une **zone morte** — appliqué
  au scan, dès qu'un tag est partiellement en vue la correction devient petite → mise à **zéro** → le
  robot **se fige** ("il tourne même plus pour chercher"). Le scan d'origine (31fe8b1, sans plancher)
  applique omega directement → tourne librement.

→ Retour à **31fe8b1** = enlève tout ce bruit scan, remet le scan d'origine qui tourne.

---

## 🔋 LA VRAIE CAUSE FINALE — LA BATTERIE (pas le code !)

Symptôme final : "**ça envoie 0,3 (puis 0,5) mais il ne bouge pas**", alors qu'en **navigation il
bougeait**. Fausses pistes écartées : conflit `/cmd_vel` (le collision_monitor **ne spamme PAS** de 0
au repos — `/cmd_vel` silencieux au repos). **Hypothèse de l'utilisateur = la bonne : batterie basse.**

**Pourquoi ça bouge en nav mais pas au scan** (la clé) :
- **Nav = avancer** : 2 roues **même sens**, **inertie** qui aide, **peu de couple**. Passe encore
  avec une batterie faible.
- **Scan = tourner sur place** : 2 roues **sens opposés**, **aucune inertie**, il faut vaincre la
  **friction statique des deux côtés à l'arrêt** = **le mouvement le plus gourmand en couple** du
  robot. Batterie basse → couple mou → les moteurs reçoivent 0,3/0,5 mais **calent**.

C'est un **mode de panne documenté** (cf. mémoire : viser **≥25V au repos** avant tout test nav,
sinon "on debugge Nav2 pour rien"). ⚠️ **La tension ne se lit PAS via ROS** sur ce robot
(`/diagnostics` ne contient que la caméra) → **multimètre obligatoire**.

**→ Recharger la batterie avant tout re-test.** Ce n'était ni le docking, ni le correcteur, ni le
gate. Juste le jus.

---

## 📋 TOUTES LES COMMANDES (recette, dans l'ordre)

### Bring-up complet (avec docking)
```bash
ssh botshare@botshare.local
```
```bash
pkill -9 -f "micro_ros_agent|rplidar|component_container|apriltag|dock_trigger|nav2|controller_server|planner_server|bt_navigator|behavior_server|smoother_server|amcl|map_server|lifecycle_manager|ekf_node|robot_state_publisher|static_transform|web_video_server|scan_body_filter|goal_relay|ros2 launch" 2>/dev/null
sleep 3
source /opt/ros/jazzy/setup.bash
source ~/linorobot2_ws/install/setup.bash
source ~/camera_ws/install/setup.bash
source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0
ros2 launch openamrobot_bringup bringup.launch.py map:=/home/botshare/maps/piece_actuelle.yaml use_docking:=true
```
⚠️ Le `pkill` en une ligne via `ssh hote "...ros2 launch..."` **coupe la connexion SSH** (le motif
matche la commande SSH elle-même). Le kill s'exécute quand même côté Pi ; vérifier avec `ssh hote "echo alive"`.

### Relancer UNIQUEMENT le docking (caméra/nav2/lidar déjà lancés)
```bash
pkill -9 -f "dock_trigger.py|apriltag_node|apriltag_gate.py|detected_dock_pose_publisher" 2>/dev/null; sleep 2
source /opt/ros/jazzy/setup.bash; source ~/openamr-platform-sw/ros2/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
ros2 launch openamrobot_docking docking_real.launch.py
```

### Calibration encodeur — PC, ⚠️ ROUES EN L'AIR (après chaque power-cycle Teensy)
```bash
cd ~/Documents/openamr
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
python3 scripts/align_enc_cal.py --arm 250   # attendre "table placed -> /debug/enc_cal"
```

### RViz + localisation
```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
rviz2 -d ~/Documents/openamr/scripts/openamr_nav.rviz
```
**2D Pose Estimate** à la position réelle. Si AMCL reste `inactive` (log `AMCL is not yet in the active state`) :
```bash
ros2 lifecycle get /amcl        # si inactive alors que map_server active :
ros2 lifecycle set /amcl activate
```

### Déclencher docking / undock
```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
ros2 topic pub --once /dock_trigger std_msgs/msg/Bool "{data: true}"
ros2 topic pub --once /undock_robot std_msgs/msg/Bool "{data: true}"
```

### Vérifs / diagnostic
```bash
source /opt/ros/jazzy/setup.bash; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; export ROS_DOMAIN_ID=0
# gyro (~0 au repos, sinon power-cycle Teensy robot immobile)
ros2 topic echo /imu/data --once --field angular_velocity.z
# ce que le contrôleur commande
ros2 topic echo /cmd_vel
# latence + détection AprilTag (activer le gate d'abord)
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: true}"
python3 /home/matthieu/Documents/openamr/scripts/apriltag_latency.py   # DET Hz, lat ms, id-Hz par tag
ros2 service call /apriltag/set_enabled std_srvs/srv/SetBool "{data: false}"
# débit gate (⚠️ /apriltag/image_in mesuré depuis le PC = plafonné par le WiFi, trompeur ;
#  fiable = le taux de /apriltag/detections, petits messages)
# CPU / thermique
uptime; vcgencmd measure_temp; vcgencmd get_throttled
# LIDAR (si /scan a 0 publisher malgré process actif -> débrancher/rebrancher USB)
ros2 topic info /scan
# ⚠️ tension batterie : PAS dans ROS -> MULTIMÈTRE (viser ≥25V au repos)
```

### UI Docker (⚠️ arrêter pendant les tests docking — conflit de nom /camera)
```bash
cd ~/Documents/openAMRobot/openamrobot-ui
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 docker compose up -d
docker compose stop     # pendant les tests docking
# rebuild si le code UI a changé (pull Raj) :
docker compose down && RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=0 docker compose up -d --build
```

---

## 📍 ÉTAT EN FIN DE SESSION
- **Code déployé sur le Pi** : `dock_trigger.py` + config restaurés à **31fe8b1** ("c'est aligné"),
  gate **brut** (4 Hz, TF correct), autofocus continu. Branche `fix/docking-near-servo-af`.
- **UI** : PR de Raj pullée + mergée dans `feat/real-robot-integration` (repo UI, non committé/poussé).
- **Robot** : **batterie à plat** → à recharger avant tout re-test.

## ⏭️ RESTE À FAIRE (à froid, robot chargé)
1. **Recharger la batterie** (≥25V) — prérequis absolu.
2. **Débit du gate** — le vrai déblocage durable du scan : gate C++/intra-process, OU assouplir le
   critère du scan (tag centre seul, moins de frames consécutives) pour tolérer 4 Hz.
3. Retester le docking bout-en-bout depuis la base 31fe8b1, robot chargé et posé face au dock.
4. Décider quoi faire de la branche `fix/docking-near-servo-af` (garder les fixes correcteur, jeter
   le bruit scan/gate déjà annulé) et préparer la PR.
