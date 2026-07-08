# Topo de présentation — Intégration OpenAMRobot (réponse à la review de Raj)

> Tout ce qu'il faut savoir pour présenter. Mis à jour 27 juin 2026.

## 1. Le contexte en 30 secondes
- Robot mobile autonome (AMR), entraînement différentiel (2 roues).
- **Deux cerveaux** : un **Teensy 4.0** (firmware temps réel, asservit les moteurs en PID, parle en micro-ROS par USB) et un **Raspberry Pi 5** (ROS 2 Jazzy : perception lidar/caméra, navigation **Nav2**, accostage AprilTag).
- **Principe central** : la **même** pile Nav2 et le **même** `nav2_params.yaml` tournent en **simulation** (Gazebo) et sur le **robot réel**. Seuls la source de données et l'horloge changent → on développe en sim, ça marche pareil en réel.

## 2. Le message principal
On a transformé des launch/scripts épars en **une intégration propre** (`bringup.launch.py sim:=true|false` lance tout) **et** on a répondu à la review de Raj.

**Sur ses ~30 demandes : 17 complètes · 7 partielles · 6 restantes** — et **les 6 restantes sont surtout du matériel physique** (fusible, E-stop, source) ou des données terrain (rosbag). **Tout le P0 logiciel critique est fait, prouvé en sim et/ou flashé, et déployé sur le robot.**

## 3. Les grands changements (à savoir expliquer)

### A. 🛡️ La sécurité réactive restaurée — LE point fort (P0)
- **Problème** : le frein anti-collision (`collision_monitor`) + le lisseur (`velocity_smoother`) étaient **configurés mais jamais lancés** → le robot avait des yeux (lidar) mais **plus de réflexe pour freiner** → il percutait les obstacles. Exactement le P0 de Raj.
- **Fait** : chaîne rebranchée `controller → cmd_vel_nav → velocity_smoother → cmd_vel_smoothed → collision_monitor → /cmd_vel`.
- **Preuve sim** : les 2 nœuds `active`, robot navigue, **un seul writer final** sur `/cmd_vel`.

### B. 📡 Un seul `/scan_filtered` (invariant de Raj)
- **Fait** : filtre **sorti du launch de nav** → propriété de la source de données (sim : laser_filters ; réel : perception). **SLAM lit maintenant `/scan_filtered`** (avant : scan brut → reflets du robot dans la carte).
- **Preuve sim** : **1 publisher, 4 subscribers** (AMCL + 2 costmaps + collision_monitor).

### C. 🎯 Un seul transmetteur de but
- relay OU docking, jamais les deux (choisi par `use_docking`) + **alarme anti-double** testée.

### D. ⚙️ Bloc sécurité firmware (FLASHÉ sur le Teensy)
- **Watchdog = arrêt franc** : plus de `/cmd_vel` >200 ms → moteurs stop + **reset PID** (avant : vitesse 0 mais PID tournait).
- **PID durci** : init explicite, `reset()`, **anti-windup conscient de la saturation**.
- **PWM brut borné** : `/debug/openloop` rejette NaN/Inf + plafonne à 70 % du max.
- **Odométrie** : 1er échantillon de temps anormal rejeté (pas de saut).
- **Profil prod/diagnostic** : `#define` qui désactive le PWM brut en build production.

### E. 📈 RPM précis (firmware flashé)
- Vitesse roue : escalier grossier 0/3/6 → **mesure fine** (méthode période = temps entre tops). Améliore odométrie + tuning.

### F. 🛠️ Diagnostics sécurisés (P0/P1)
- `high_rate_capture` : **arrêt immédiat au jerk** (avant : roulait 0,4 s de plus).
- Outils alimentés : **`--arm` obligatoire + télémétrie fraîche requise** + bornes.
- `scripts/README.md` : outils **séparés** read-only / alimentés / launch.

### G. 🔧 Configs & doc (demandes précises de Raj)
- `trans_stopped_velocity` 0,25→0,02 · limites de vitesse alignées · `vy_samples:1` · `BaseObstacle.inflate_cost` retiré · typo RPLIDAR `angle_compensate` · empreinte réelle mesurée.
- **Carte obligatoire en réel** (échec clair sans `map:=`) · **caméra paramétrable** · **validation des entrées** du filtre.
- **QoS doc corrigée** (compatibilité endpoint, pas « Nav2 exige RELIABLE »).
- **Firmware reproductible** : upstream épinglé `@aaf9d59` + script d'overlay.

## 4. L'organisation (à savoir)
- **2 dépôts** : `openamr-platform-sw` (code ROS 2 générique) + `openamr` (instance : docs, scripts, configs/cartes de CE robot). + firmware `linorobot2_hardware`.
- **PC ↔ Pi synchronisés** : script `deploy_to_pi.sh`. **Tout est déployé sur le robot et rebuildé.**
- Doc : `ARCHITECTURE.md`, `CHANGELOG-FIXES.md` (chaque changement + pourquoi), `integration-review-response.html` (réponse à Raj, avant/après), ce brief.

## 5. La réponse à Raj (à dire)
« On valide ta direction. On a déjà traité le P0 le plus critique (sécurité réactive) **et** la majorité de tes P1/P2 — prouvés en simulation et/ou flashés, et déployés. Le reste est surtout **matériel physique** + de l'évidence terrain, et on suit ton ordre de merge. »

**Ses 2 critères transverses** :
- ✅ Un seul `/scan_filtered` par profil → **fait & validé**.
- 🔶 Un seul writer `/cmd_vel` → chaîne faite & validée, le **mux formel** (priorités) reste.

## 6. Ce qui reste (l'honnêteté = une force)
- **Physique (atelier) :** fusible, arrêt d'urgence, sélection source batterie/secteur, brownout Pi, câble roue gauche, tension encodeur à figer (3,3 V).
- **Données terrain :** analyse rosbag des timestamps (EKF), mesure de l'orientation IMU.
- **Logiciel restant (1 seul item non commencé) :** gating de l'activation Nav2 sur capteurs frais (#13).
- **Évidence :** preuve **sim** faite ; reste **rosbag + bench + test sol supervisé** (Raj les exige avant merge).

## 7. Tes 5 phrases-clés
1. « Une seule commande = sim ou réel, avec la **même pile Nav2**. »
2. « Le bug le plus dangereux — **sécurité anti-collision désactivée** — est **réparé et prouvé en sim**. »
3. « On garantit **un seul `/scan_filtered`** et un **seul transmetteur de but** par profil — tes invariants. »
4. « Firmware durci & **flashé** : watchdog arrêt-franc, PID anti-windup, PWM borné, profil prod/diag. »
5. « Sur ~30 demandes : **17 complètes, 7 partielles, 6 restantes** — le reste surtout **matériel physique**, dans ton ordre de merge. »

## 8. Questions probables de Raj (et tes réponses)
- *« Le mux cmd_vel ? »* → la chaîne existe et garantit 1 writer final ; le **mux formel** (priorité entre sources) est la prochaine étape.
- *« Preuves ? »* → sim end-to-end faite (nœuds actifs, robot navigue, 1 publisher scan, 1 writer cmd_vel, alarme double-transmetteur testée) ; rosbag/bench/sol planifiés.
- *« Offset EKF 0,2 s ? »* → reconnu comme contournement ; analyse rosbag des timestamps plutôt que justification à la main.
- *« Armement du PWM brut ? »* → bornes + validation **faites & flashées** ; l'armement exclusif complet (nouveau topic + handshake interface) est planifié.
- *« Gating d'activation Nav2 ? »* → planifié (nœud de readiness scan/odom/map→odom) ; aujourd'hui l'ancien `bringall.sh` attendait `map→odom`, on porte cette logique.
- *« Firmware reproductible ? »* → upstream épinglé `@aaf9d59` + `apply_overlay.sh` ; CI à câbler.
