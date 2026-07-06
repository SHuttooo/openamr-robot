---
name: amr-pi5-power-brownout
description: "BLOQUEUR alim : le Pi 5 brownout/freeze/coupe quand real_bringup démarre (moteurs+lidar+caméra = pic courant > alim 5A)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**Le Raspberry Pi 5 coupe sous charge (2026-06-25).** Au lancement de `real_bringup.launch.py`, les
moteurs + lidar + caméra démarrent **en même temps** → pic de courant → l'alim s'effondre → le Pi
**freeze (Ctrl+C ne répond plus) puis perd le réseau** (no ping). Au boot le Pi affiche
*« This power supply is not capable of supplying 5A; power to peripherals will be restricted »*.

**Symptômes typiques (toute la session du 2026-06-25 en a souffert) :** terminal figé pendant un launch ;
SSH qui tombe ; `No route to host` ; lidar qui ne tourne plus ; reboots involontaires ; impression de
« zombies » après coup (en fait des reboots/crash). → **Avant d'accuser le logiciel, vérifier que le Pi
est encore vivant (`ping`).**

**Cause = alimentation insuffisante** (Pi 5 demande 5V/5A ; sous batterie un peu basse le rail 5V
s'effondre au pic). **Aucun réglage ROS ne corrige ça.**

**À faire :** batterie **≥ 25 V** ([[amr-battery-voltage-check]]) ; **buck 5V capable de ≥5A en pic**, câble
court/épais ; ou alim secteur officielle 5V/5A pour tester. **Test de confirmation** : lancer le bringup
**sans la caméra** (charge plus légère) — si ça tient, c'est l'alim (la caméra ajoute le pic fatal).

⚠️ Piège d'analyse : `ps -ef | grep -c "[r]plidar"` via SSH **se compte lui-même** (la ligne de commande
contient le motif) → faux « 2 process ». Compter les vrais nœuds avec `ros2 node list`, pas un grep dont
la cmdline contient le motif cherché.

**Même cause côté MOTEURS (2026-06-26) :** les 2 drivers BLDC **ZBLD.C20-120L2R** passent en défaut
**LED rouge, code 10 = "Busbar Undervoltage"** (lecture LED : code = verts×5 + rouges ; 1 vert+5 rouges=10)
→ driver **stoppe le moteur** (le Teensy envoie pourtant le PWM, vérifiable sur `/debug/pwm`). Les DEUX en
même temps = cause commune = **24V partagé trop bas = batterie à plat** (ZBLD veut 24V ±20% = 19,2–28,8V).
Fix : recharger ≥25V → power-cycle 24V → LED rouge éteinte. Table complète des codes :
docs/hardware/motor-driver-fault-codes.md. ⇒ batterie faible = LE fil rouge de la journée (Pi brownout +
drivers code 10 + couple mou).

Voir [[amr-battery-voltage-check]], [[amr-nav2-bringup]].