---
name: amr-user-drives-real-robot-launches
description: "Sur le robot réel, laisser l'utilisateur lancer/relancer lui-même le bring-up (SSH) plutôt que l'automatiser à sa place — donner la commande, ne pas l'exécuter"
metadata:
  type: feedback
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

**2026-07-07** : après une session où j'ai automatisé pas mal de commandes SSH (kill/relaunch du
bring-up, scp de fichiers, rebuild) pour aller vite pendant un test de docking, l'utilisateur a
coupé un `ssh ... ros2 node list/param get` de vérification avec *« je veux lancer de mon côté »*.

## Règle
Sur le robot réel, pour les étapes de **lancement/relancement du bring-up** (et les vérifications
qui suivent juste après), **donner la commande complète à copier-coller** plutôt que l'exécuter
moi-même via SSH — même si je viens de déployer des fichiers modifiés (scp/rebuild) qui nécessitent
un relaunch pour être pris en compte.

## Pourquoi
Cohérent avec un signal déjà vu dans la même session (*« on ne part pas sur la bonne façon de
faire. je veux pouvoir voir les logs »*) : l'utilisateur veut garder la main sur ce qui tourne sur
le robot physique — voir lui-même les logs de démarrage, décider quand relancer, ne pas découvrir
après coup qu'un process a été tué/relancé à sa place.

## Ce qui reste OK de faire moi-même
- Lire/analyser des logs déjà écrits, des topics déjà enregistrés.
- Modifier du code, scp/déployer des fichiers, rebuild.
- Des commandes SSH **read-only** de diagnostic ponctuel quand explicitement demandé (ex. « regarde
  si… »), mais pas de vérif automatique enchaînée après un déploiement sans qu'il l'ait demandée.
- Voir aussi [[amr-commands-always-complete]] (commandes toujours complètes, copiables).

## Comment appliquer
Après avoir déployé un changement (scp + colcon build), **s'arrêter et donner la commande de
relaunch** à l'utilisateur au lieu de la lancer via SSH. Ne reprendre la main (SSH) que s'il le
redemande explicitement.
