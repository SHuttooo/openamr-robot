# 2026-07-10 — Docking finalisé, diagnostic CPU/caméra (composé = défaut), audit doc complet (59), test sim & prépa des 4 PR

Grosse journée : on termine les derniers réglages du docking, on trouve enfin **le** bloqueur de fond (CPU/caméra, mauvais profil de lancement), on fait un **audit multi-agents de toute la doc** (59 docs), on remet le **sim** en route sur le PC, et on **pousse + prépare les 4 PR**. Les PR seront ouvertes demain.

## Docking — les derniers réglages

Sur la lancée de la veille (ligne d'approche unifiée en odom), plusieurs bugs restants réglés :

- **`dock_pose` hors carte → planner « Goal … outside bounds »** : `dock_pose_x` valait `4.899` (d'une autre carte) alors que `piece_actuelle.yaml` s'arrête à x=1.97. Mesuré le vrai tag (`ros2 run tf2_ros tf2_echo map charging_dock_tag_1` → (1.362, 0.222), +z ≈ −x ⇒ yaw 0) et corrigé → le staging retombe dans la carte.
- **Le robot calait à ~15 cm du dock (à-coups)** : `/cmd_vel` a **7 publishers** ; `dock_trigger` publie direct dessus, mais le **`collision_monitor` de Nav2 publie AUSSI** et envoie des `0` en voyant le dock → la base reçoit avance/stop/avance → judder puis blocage. Fix : **désactiver le collision_monitor pendant la manœuvre** (comme la pause AMCL), mais **seulement APRÈS la Phase 1** — la Phase 1 est du Nav2 dont les commandes passent `controller→smoother→collision_monitor→/cmd_vel` ; le couper avant cassait la Phase 1 (le robot n'atteignait plus son 1er objectif).
- **Garde-fou obstacle** : `obstacle_check_enabled` mis à **false par défaut** (le dock EST l'« obstacle » qu'on approche exprès ; le garde-fou à 0,6 m abortait l'approche). Rendu réglable à chaud.
- **Arrêt final** : `stop_lidar_distance` **0.13 m** (lidar avant = capteur d'arrêt fiable), `docking_distance 0.13` = failsafe caméra. `drive_speed 0.05→0.10` (avance trop lente) ; nouveau `final_push_speed` = plancher du taper, à monter pour l'élan sur la marche à batterie basse.
- **Recherche des tags qui se figeait** : quand un seul tag est vu près du centre, la correction proportionnelle passait sous le plancher de stiction → le robot **se figeait face à un tag** sans révéler les autres. Floored → il **continue à tourner** tant que les 3 tags ne sont pas vus.
- **`log_splitter`** : nouvel outil — découpe `/rosout` en topics `/logs/<node>` (ex. `ros2 topic echo /logs/dock_trigger`) pour ne plus se noyer dans la console du bring-up.

## Le vrai bloqueur de fond : CPU / caméra (mauvais profil)

Le docking restait fragile (recherche qui n'aboutit pas, approche en aveugle, oscillation lente). Diagnostic au `top` pendant un dock :
- On tournait sur **`bringup.launch.py` (NON-composé)** → la caméra passe par **`apriltag_gate.py` (Python)** qui recopie chaque image pleine rés → **~20 % CPU + plafonne à 0,4–4 img/s** (goulot historique). D'où les tags perdus → aveugle → oscillation lente (le correcteur agit sur du périmé).
- Le **Pi5 est saturé** (load 8+ sur 4 cœurs) : vision composée + Nav2 complet + docking ensemble = 2× la capacité.
- **Fix = le profil COMPOSÉ** (`bringup_composed.launch.py`) : caméra+AprilTag intra-process zéro-copie → ~15 img/s, ~½ CPU vision, **pas de gate**. Documenté comme **LE défaut** pour tout ce qui touche caméra/docking. (Non-composé = debug nav-only sans caméra.)

## Audit doc complet — 59 docs, multi-agents

Deux vagues de **workflow multi-agents** (1 agent par doc, confronté à l'état réel du code) :
- **Vague 1** (20 docs opérationnelles/docking) : 31 corrections.
- **Vague 2** (39 docs restantes) : 14 corrections.
- **Total : 59 docs audités, 45 corrections** ; 37 déjà justes.

Corrections types : composé = défaut partout (fini `bringup.launch.py` en tête), carte `piece_actuelle.yaml`, dock-pose via `tf2_echo`, **DWB `param set` ne prend pas à chaud** (getter ment → yaml+relance), valeurs docking à jour (stop 0.13, drive_speed 0.10, gains, undock 0.7, obstacle off, turn_deadband 0.09), ligne toujours en odom, arrêt lidar, collision_monitor coupé pendant le dock, `base_footprint` racine + slam_toolbox, réfs croisées cassées.

## Test du sim (sur le PC)

- **Fragmentation des branches** découverte : `feature/docking` n'a le `package.xml` complet QUE pour docking ; `openamrobot_bringup`/`perception`/… sont des stubs → **pas buildable seule**. La branche **complète et buildable = `feature/real-robot-bringup`**.
- **« ça lag énormément » (5 fps)** : pas un bug du robot. Le laptop (RTX 3060) tournait sur l'**iGPU Intel** — au `top`, **RViz à 281 % + Gazebo à 172 %** rament faute de GPU. Le driver NVIDIA était bien installé mais les apps partaient sur l'Intel (**GPU hybride / PRIME**). Fix : lancer avec **`__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia`** → le rendu passe sur la RTX → fluide. (Piège annexe : `QT_QPA_PLATFORM=xcb` sur Wayland force XWayland → à NE PAS mettre.)
- Commandes sim de la doc : `ros2 launch openamrobot_docking bringup_sim.launch.py` (build depuis `ros2/` d'abord). Bug latent connu : géométrie de roue sim (`robot.sdf` 0.046533 vs 0.11) → branche `fix/sim-wheel-geometry`.

## Git & préparation des 4 PR

- **Tout poussé** sur le fork `SHuttooo/openamr-platform-sw`. **4 branches = 4 PR** (empilées, à merger dans l'ordre) : `feature/real-robot-bringup` (1er) → `feature/real-robot-docs-pr` (2e) → `feature/docking` (dernier) ; `fix/sim-wheel-geometry` indépendante.
- **Descriptions de PR** (anglais) + **texte d'explication pour Alex** rédigés (comment lire : commit par commit, pas le diff global de ~500 fichiers dû à la divergence fork↔upstream).
- **Placement des docs corrigé** : les docs internes au paquet docking (auditées) rapatriées sur `feature/docking` pour éviter les conflits au merge (`15_legacy` préservé). ⚠️ Erreur en cours de route (écrasé le bon README bringup détaillé par une version courte) → **détectée et revertée**. La réconciliation doc complète entre branches reste à faire proprement (divergence plus large que l'audit).
- Repo `openamr` : journal + mémoire de session poussés.

## Demain
**Ouvrir les 4 PR** upstream (bring-up → docs → docking + sim-fix), envoyer le lien + le texte à Alex, et faire la réconciliation doc propre entre branches si besoin.
